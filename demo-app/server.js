const http = require('http'), fs = require('fs'), path = require('path');
const root = path.resolve(__dirname, '..', 'output');
http.createServer((req,res)=>{
  const url = new URL(req.url,'http://localhost');
  if(url.pathname === '/api/runs') {
    let names=[]; try { names=fs.readdirSync(root,{withFileTypes:true}).filter(d=>d.isDirectory() && d.name!=='latest' && fs.existsSync(path.join(root,d.name,'decision_log.json'))).map(d=>d.name).sort().reverse(); if(fs.existsSync(path.join(root,'latest','decision_log.json'))) names.unshift('latest'); } catch {}
    res.setHeader('Content-Type','application/json'); return res.end(JSON.stringify(names));
  }
  if(url.pathname === '/api/run') {
    const id=url.searchParams.get('id'); if(!id || !/^[\w.-]+$/.test(id) || id==='.' || id==='..') {res.statusCode=400; return res.end();}
    try { const read=n=>JSON.parse(fs.readFileSync(path.join(root,id,n+'.json'),'utf8').replace(/^\uFEFF/,'')); res.setHeader('Content-Type','application/json'); return res.end(JSON.stringify({log:read('decision_log'),story:read('story_bible')})); } catch {res.statusCode=404; return res.end('Run unavailable');}
  }
  const file=url.pathname==='/decision-log'?'decision-log.html':url.pathname==='/'?'index.html':null;
  if(!file){res.statusCode=404;return res.end('Not found');} res.setHeader('Content-Type','text/html; charset=utf-8'); fs.createReadStream(path.join(__dirname,file)).pipe(res);
}).listen(3000,'127.0.0.1',()=>console.log('Demo: http://localhost:3000'));
