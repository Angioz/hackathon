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
  if(url.pathname === '/api/live') {
    // Live: output/live/events.jsonl (from ?since=N). Replay: output/<run>/events.jsonl (?run=id).
    const run=url.searchParams.get('run'); if(run && (!/^[\w.-]+$/.test(run) || run==='.' || run==='..')) {res.statusCode=400; return res.end();}
    // Replays fall back to committed recordings in docs/evidence/<run>/ (e.g. ?run=golden works on any laptop).
    const evidence=path.resolve(__dirname,'..','docs','evidence');
    const file=[path.join(root, run||'live','events.jsonl')].concat(run?[path.join(evidence,run,'events.jsonl')]:[]).find(f=>fs.existsSync(f));
    let events=[]; try { events=fs.readFileSync(file,'utf8').split(/\r?\n/).filter(Boolean).map(l=>{try{return JSON.parse(l)}catch{return null}}).filter(Boolean); } catch {}
    const since=Math.max(0, parseInt(url.searchParams.get('since')||'0',10)||0);
    res.setHeader('Content-Type','application/json'); res.setHeader('Cache-Control','no-store');
    return res.end(JSON.stringify({total:events.length, events: run?events:events.slice(since)}));
  }
  const file=url.pathname==='/decision-log'?'decision-log.html':url.pathname==='/live'?'live.html':url.pathname==='/'?'index.html':null;
  if(!file){res.statusCode=404;return res.end('Not found');} res.setHeader('Content-Type','text/html; charset=utf-8'); fs.createReadStream(path.join(__dirname,file)).pipe(res);
}).listen(3000,'127.0.0.1',()=>console.log('Demo: http://localhost:3000'));
