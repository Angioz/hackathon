import json, pathlib, subprocess, time, sys
root=pathlib.Path(__file__).resolve().parents[1]
latest=root/'output'/'latest'
if not (latest/'decision_log.json').exists():
    latest.mkdir(parents=True,exist_ok=True)
    (latest/'decision_log.json').write_text(json.dumps({'fixture':True,'decisions':[{'round':2,'agent_id':'Critic','action_type':'challenge','decision_summary':'Test the reading experience.','reasoning_why':'Readers need a clear way back.','plot_twist_flag':True}]}),encoding='utf-8')
    (latest/'story_bible.json').write_text(json.dumps({'fixture':True,'title':'FIXTURE: Smart Scroll'}),encoding='utf-8')
p=subprocess.Popen(['node','server.js'],cwd=root/'demo-app')
try:
    time.sleep(2)
    for url in ['http://localhost:3000/','http://localhost:3000/decision-log','http://localhost:3000/api/run?id=latest']:
        r=subprocess.run(['curl.exe','-s','-o','NUL','-w','%{http_code}',url],capture_output=True,text=True); print(url, r.stdout, flush=True)
finally:
    p.terminate(); p.wait()
