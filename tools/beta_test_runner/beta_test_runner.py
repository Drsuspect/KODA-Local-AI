from __future__ import annotations
import json, os, re, statistics, threading, time, webbrowser
from datetime import datetime
from difflib import SequenceMatcher
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib import request, error

APP_HOST="127.0.0.1"; APP_PORT=8765; HERE=Path(__file__).resolve().parent
def detect_root():
    cand=[HERE,HERE.parent,Path.cwd(),Path(r"F:\\Yazilimlar\\app\\KODA_AI_LAB\\04_KODA_Local_AI"),Path(r"C:\\KODA_AI_LAB\\04_KODA_Local_AI")]
    if os.environ.get("KODAAI_ROOT"): cand.insert(0,Path(os.environ["KODAAI_ROOT"]))
    for p in cand:
        try:
            if (p/"api_server.py").exists() and (p/"logs").exists(): return p
        except: pass
    return HERE
ROOT=detect_root()
QF=HERE/"questions.json"
QUESTIONS=json.loads(QF.read_text(encoding="utf-8"))
STATE={"session_id":None,"session_started":None,"session_finished":None,"marks":{},"root":str(ROOT),"backend_url":"http://127.0.0.1:8080","last_auto":None,"auto_started":False,"auto_running":False,"auto_progress":0,"auto_total":len(QUESTIONS),"auto_current":None,"auto_last":None,"auto_error":None}
def now_iso(): return datetime.now().astimezone().isoformat(timespec="seconds")
def norm(s):
    s=(s or "").translate(str.maketrans("çğıöşüÇĞİÖŞÜ","cgiosuCGIOSU")).casefold()
    return " ".join(re.findall(r"[a-z0-9]+",s))
def read_jsonl(p):
    if not p.exists(): return []
    out=[]
    for line in p.read_text(encoding="utf-8-sig",errors="replace").splitlines():
        try:
            if line.strip(): out.append(json.loads(line))
        except: pass
    return out
def pdt(s):
    try: return datetime.fromisoformat(str(s).replace("Z","+00:00"))
    except: return None
def inwin(r,start,end):
    t=pdt(r.get("timestamp"))
    if not t:return True
    if t.tzinfo is None:t=t.astimezone()
    return (not start or t>=start) and (not end or t<=end)
def api_key():
    f=ROOT/".env"
    if f.exists():
        for line in f.read_text(encoding="utf-8-sig",errors="ignore").splitlines():
            if line.startswith("KODAAI_API_KEY="):
                return line.split("=",1)[1].strip().strip('"').strip("'")
    return ""
def ask(q,qid,sid,base):
    payload=json.dumps({"question":q,"session_id":sid,"client_request_id":qid},ensure_ascii=False).encode("utf-8")
    h={"Content-Type":"application/json; charset=utf-8","Accept":"application/json"}
    if api_key(): h["X-KODAAI-API-Key"]=api_key()
    req=request.Request(base.rstrip("/")+"/ask",data=payload,headers=h,method="POST"); st=time.perf_counter()
    try:
        with request.urlopen(req,timeout=120) as r:
            return {"ok":True,"http":r.status,"elapsed_ms":round((time.perf_counter()-st)*1000,2),"response":json.loads(r.read().decode("utf-8",errors="replace"))}
    except error.HTTPError as e:
        return {"ok":False,"http":e.code,"elapsed_ms":round((time.perf_counter()-st)*1000,2),"error":e.read().decode("utf-8",errors="replace")}
    except Exception as e:return {"ok":False,"http":None,"elapsed_ms":round((time.perf_counter()-st)*1000,2),"error":f"{type(e).__name__}: {e}"}
def latest_telemetry(qid,sid):
    rows=read_jsonl(ROOT/"logs"/"telemetry.jsonl")
    for r in reversed(rows):
        if r.get("request_id")==qid and (not sid or r.get("session_id")==sid):
            return r
    return {}

def best(q,rows,used):
    nq=norm(q); c=[]
    for i,r in enumerate(rows):
        if i in used:continue
        rq=norm(r.get("question") or "")
        if not rq:continue
        sc=1.0 if rq==nq else SequenceMatcher(None,nq,rq).ratio()
        if sc>=0.68:c.append((sc,i,r))
    if not c:return None
    return sorted(c,key=lambda x:x[0],reverse=True)[0]
def analyze():
    ld=ROOT/"logs"; tel=read_jsonl(ld/"telemetry.jsonl"); gaps=read_jsonl(ld/"content_gap.jsonl"); audit=read_jsonl(ld/"audit_log.jsonl")
    st=pdt(STATE.get("session_started")); en=pdt(STATE.get("session_finished")) or datetime.now().astimezone()
    tel=[r for r in tel if inwin(r,st,en)]; gaps=[r for r in gaps if inwin(r,st,en)]; audit=[r for r in audit if inwin(r,st,en)]
    used=set(); results=[]
    for q in QUESTIONS:
        m=best(q["question"],tel,used)
        if m:
            sc,i,r=m;used.add(i);results.append({"id":q["id"],"question":q["question"],"matched":True,"match_score":round(sc,3),"telemetry_question":r.get("question"),"route":r.get("route"),"subject":r.get("subject"),"duration_ms":r.get("duration_ms"),"source_count":r.get("source_count"),"used_context":r.get("used_context"),"success":r.get("success"),"blocked":r.get("blocked"),"error":r.get("error"),"request_id":r.get("request_id")})
        else:results.append({"id":q["id"],"question":q["question"],"matched":False})
    dur=[r.get("duration_ms") for r in tel if isinstance(r.get("duration_ms"),(int,float))]
    routes={}; subs={}
    for r in tel:
        routes[r.get("route") or "UNKNOWN"]=routes.get(r.get("route") or "UNKNOWN",0)+1
        subs[r.get("subject") or "UNKNOWN"]=subs.get(r.get("subject") or "UNKNOWN",0)+1
    susp=[]
    for r in results:
        if not r["matched"]:susp.append({"id":r["id"],"reason":"TELEMETRY_MISSING","question":r["question"]})
        elif r.get("success") is False:susp.append({"id":r["id"],"reason":"REQUEST_FAILED","question":r["question"],"route":r.get("route")})
        elif r.get("blocked"):susp.append({"id":r["id"],"reason":"BLOCKED","question":r["question"],"route":r.get("route")})
        elif r.get("route")=="ERROR":susp.append({"id":r["id"],"reason":"ERROR_ROUTE","question":r["question"]})
    gaplist=[{k:g.get(k) for k in ("timestamp","question","subject","topic_guess","retrieval_score","matched_sources","status","request_id")} for g in gaps]
    summary={"session_id":STATE.get("session_id"),"session_started":STATE.get("session_started"),"session_finished":STATE.get("session_finished") or now_iso(),"root":str(ROOT),"questions_total":len(QUESTIONS),"telemetry_events_in_window":len(tel),"questions_matched":sum(x["matched"] for x in results),"questions_missing":sum(not x["matched"] for x in results),"content_gaps":len(gaplist),"audit_events_in_window":len(audit),"route_counts":routes,"subject_counts":subs,"duration":{"avg_ms":round(statistics.mean(dur),2) if dur else None,"median_ms":round(statistics.median(dur),2) if dur else None,"max_ms":round(max(dur),2) if dur else None},"suspicious_count":len(susp)}
    rep={"summary":summary,"results":results,"content_gaps":gaplist,"suspicious":susp}
    od=ld/"beta_test_reports";od.mkdir(parents=True,exist_ok=True);f=od/f"beta_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json";f.write_text(json.dumps(rep,ensure_ascii=False,indent=2),encoding="utf-8");rep["report_file"]=str(f);return rep

HTML="""<!doctype html><html lang='tr'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>KODAAI Beta Test Runner</title><style>
:root{--bg:#071525;--panel:#0b1e32;--text:#f4f8ff;--muted:#a9b9cc;--cyan:#20dfff;--green:#2cefb4;--border:#244f76}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font-family:Segoe UI,Arial}.shell{max-width:1180px;margin:auto;padding:22px}.top{display:flex;justify-content:space-between;align-items:center}h1{margin:0}.badge{color:var(--cyan);font-weight:700}.card{background:var(--panel);border:1px solid var(--border);border-radius:16px;padding:18px;margin-top:16px}.progress{height:8px;background:#0a1727;border-radius:999px;overflow:hidden}.bar{height:100%;background:linear-gradient(90deg,#2586ff,#20dfff);width:1%}.meta{display:flex;justify-content:space-between;color:var(--muted);font-size:13px;margin:10px 0 16px}.question{font-size:30px;line-height:1.35;min-height:145px;display:flex;align-items:center}.actions{display:flex;gap:10px;flex-wrap:wrap}button{background:#0c2740;color:var(--text);border:1px solid #23547a;border-radius:10px;padding:11px 15px;font-weight:700;cursor:pointer}button.primary{color:var(--cyan)}button.danger{color:#ffd7dc;border-color:#70404a}button:disabled{opacity:.38;cursor:not-allowed}.run-progress{height:12px;background:#06111e;border-radius:999px;overflow:hidden;margin-top:12px}.run-bar{height:100%;background:linear-gradient(90deg,#2586ff,#20dfff);width:0%;transition:width .25s ease}.run-big{font-size:22px;font-weight:800;color:var(--cyan);margin-top:10px}.run-done{color:var(--green)}.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}.small{color:var(--muted);font-size:13px}.status{padding:10px;border-radius:10px;background:#081a2c;margin-top:10px;white-space:pre-wrap}input{background:#071525;color:white;border:1px solid var(--border);padding:9px;border-radius:8px;width:100%}table{width:100%;border-collapse:collapse;font-size:13px}th,td{padding:8px;border-bottom:1px solid #17344e;text-align:left;vertical-align:top}th{color:var(--cyan)}pre{white-space:pre-wrap;max-height:280px;overflow:auto;background:#06111e;padding:12px;border-radius:10px}.hidden{display:none}</style></head><body><div class='shell'>
<div class='top'><div><h1>KODAAI Beta Test Runner</h1><div class='small'>100 soruluk sesli / otomatik production testi</div></div><div class='badge' id='voiceState'>Mikrofon kapalı</div></div>
<div class='card'><div class='progress'><div class='bar' id='bar'></div></div><div class='meta'><span id='qid'></span><span id='counter'></span></div><div class='question' id='question'></div><div class='actions'><button onclick='prev()'>← Önceki</button><button class='primary' onclick='next()'>Sonraki →</button><button onclick='speak()'>Soruyu seslendir</button><button onclick='toggleVoice()' id='voiceBtn'>Sesli komutu aç</button><button onclick="mark('ok')">✓ Başarılı</button><button onclick="mark('problem')">! Problem</button></div><div class='small' style='margin-top:12px'>Sesli komutlar: sonraki, önceki, tekrar, final analiz. Klavye: → / ←.</div></div>
<div class='grid'><div class='card'><h3>Test oturumu</h3><div class='small'>KODAAI kökü</div><div class='status' id='root'></div><div class='small' style='margin-top:10px'>Backend</div><input id='backend' value='http://127.0.0.1:8080'><div class='actions' style='margin-top:12px'><button class='primary' onclick='startSession()'>Oturumu Başlat</button><button class='danger' id='autoBtn' onclick='autoRun()'>100 Soruyu Otomatik Çalıştır</button></div><div class='run-progress'><div class='run-bar' id='runBar'></div></div><div class='run-big' id='runCount'>0 / 100</div><div class='status' id='runStatus'>Hazır.</div><div class='small' id='runLast' style='margin-top:8px'>Son sonuç: -</div></div>
<div class='card'><h3>Final</h3><p class='small'>Telemetry, content_gap ve audit kayıtlarını oturum aralığında karşılaştırır.</p><button class='primary' id='finalBtn' onclick='finalAnalyze()' disabled>Final Analiz ve İçerik Açıkları</button><div class='status' id='finalStatus'>Test tamamlandığında aktifleşir.</div></div></div>
<div class='card hidden' id='reportCard'><h3>Özet</h3><div id='summary'></div><h3>İçerik Açıkları</h3><div id='gaps'></div><h3>Şüpheli / Eksik</h3><div id='suspicious'></div><h3>Ham rapor</h3><pre id='raw'></pre></div></div>
<script>
let qs=[],idx=0,recognition=null,listening=false,progressTimer=null;async function init(){let s=await fetch('/api/state').then(r=>r.json());qs=s.questions;root.textContent=s.root;render();applyProgress(s.state)}function render(){let q=qs[idx];question.textContent=q.question;qid.textContent=q.id;counter.textContent=(idx+1)+' / '+qs.length;bar.style.width=((idx+1)/qs.length*100)+'%'}function next(){if(idx<qs.length-1){idx++;render()}}function prev(){if(idx>0){idx--;render()}}function speak(){speechSynthesis.cancel();let u=new SpeechSynthesisUtterance(qs[idx].question);u.lang='tr-TR';speechSynthesis.speak(u)}async function mark(v){await fetch('/api/mark',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:qs[idx].id,value:v})})}async function startSession(){let res=await fetch('/api/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({backend_url:backend.value})});let r=await res.json();if(!res.ok||!r.ok){runStatus.textContent=r.error||'Oturum açılamadı.';return}runStatus.textContent='Oturum başladı: '+r.session_id;runCount.textContent='0 / '+qs.length;runBar.style.width='0%';runLast.textContent='Son sonuç: -';finalBtn.disabled=true;finalStatus.textContent='Test tamamlandığında aktifleşir.'}function applyProgress(p){let total=p.auto_total||qs.length||100,done=p.auto_progress||0,pct=total?Math.round(done/total*100):0;runCount.textContent=done+' / '+total;runBar.style.width=pct+'%';autoBtn.disabled=!!p.auto_running;if(p.auto_running){runCount.classList.remove('run-done');runStatus.textContent='TEST DEVAM EDİYOR\nŞu an: '+(p.auto_current||'-')+'\nSession: '+(p.session_id||'-');finalBtn.disabled=true;finalStatus.textContent='Test devam ediyor. Final analiz kilitli.'}else if(p.auto_started&&done>=total&&total>0){runCount.classList.add('run-done');runStatus.textContent='TEST TAMAMLANDI\nSession: '+(p.session_id||'-');finalBtn.disabled=false;finalStatus.textContent='Test tamamlandı. Final Analiz hazır.';if(progressTimer){clearInterval(progressTimer);progressTimer=null}}else{finalBtn.disabled=true}if(p.auto_last){let x=p.auto_last;runLast.textContent='Son sonuç: '+(x.id||'-')+' · '+(x.route||'route ?')+' · '+(x.subject||'subject ?')+' · '+(x.duration_ms??x.elapsed_ms??'-')+' ms'}if(p.auto_error){runStatus.textContent+='\nHATA: '+p.auto_error}}async function pollProgress(){try{let p=await fetch('/api/progress?ts='+Date.now()).then(r=>r.json());applyProgress(p)}catch(e){runStatus.textContent='İlerleme okunamadı: '+e}}async function autoRun(){if(!confirm('100 soru /ask endpointine gönderilecek. Başlatılsın mı?'))return;finalBtn.disabled=true;finalStatus.textContent='Test devam ediyor. Final analiz kilitli.';let res=await fetch('/api/auto-run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({backend_url:backend.value})});let r=await res.json();if(!res.ok||!r.ok){runStatus.textContent=r.error||'Test başlatılamadı.';return}runStatus.textContent=r.message;if(progressTimer)clearInterval(progressTimer);progressTimer=setInterval(pollProgress,1000);pollProgress()}async function finalAnalyze(){let p=await fetch('/api/progress?ts='+Date.now()).then(r=>r.json());if(p.auto_running||!p.auto_started||p.auto_progress<p.auto_total){finalStatus.textContent='Final analiz için 100 / 100 tamamlanmalı.';return}finalStatus.textContent='Analiz ediliyor...';let res=await fetch('/api/analyze',{method:'POST'});let r=await res.json();if(!res.ok||r.ok===false){finalStatus.textContent=r.error||'Analiz yapılamadı.';return}finalStatus.textContent='Tamam. Rapor: '+r.report_file;showReport(r)}function table(rows,cols){if(!rows.length)return '<div class=small>Kayıt yok.</div>';let h='<table><tr>'+cols.map(c=>'<th>'+c[1]+'</th>').join('')+'</tr>';for(let r of rows)h+='<tr>'+cols.map(c=>'<td>'+String(r[c[0]]??'')+'</td>').join('')+'</tr>';return h+'</table>'}function showReport(r){reportCard.classList.remove('hidden');let s=r.summary;summary.innerHTML='<div class=status>Toplam: '+s.questions_total+' | Eşleşen: '+s.questions_matched+' | Eksik: '+s.questions_missing+' | İçerik açığı: '+s.content_gaps+' | Ortalama: '+(s.duration.avg_ms??'-')+' ms | Medyan: '+(s.duration.median_ms??'-')+' ms | Maks: '+(s.duration.max_ms??'-')+' ms<br>Routes: '+JSON.stringify(s.route_counts)+'<br>Subjects: '+JSON.stringify(s.subject_counts)+'</div>';gaps.innerHTML=table(r.content_gaps,[['question','Soru'],['subject','Ders'],['topic_guess','Konu'],['retrieval_score','Score'],['matched_sources','Kaynak'],['status','Durum']]);suspicious.innerHTML=table(r.suspicious,[['id','ID'],['reason','Neden'],['question','Soru'],['route','Route']]);raw.textContent=JSON.stringify(r,null,2)}function toggleVoice(){if(listening){listening=false;recognition.stop();return}let SR=window.SpeechRecognition||window.webkitSpeechRecognition;if(!SR){alert('Chrome/Edge SpeechRecognition yok. Butonlar çalışır.');return}recognition=new SR();recognition.lang='tr-TR';recognition.continuous=true;recognition.onresult=e=>{let t=e.results[e.results.length-1][0].transcript.toLowerCase();if(t.includes('sonraki'))next();else if(t.includes('önceki'))prev();else if(t.includes('tekrar'))speak();else if(t.includes('final'))finalAnalyze()};recognition.onstart=()=>{listening=true;voiceState.textContent='Mikrofon dinliyor';voiceBtn.textContent='Sesli komutu kapat'};recognition.onend=()=>{if(listening){try{recognition.start()}catch(e){}}};recognition.start()}document.addEventListener('keydown',e=>{if(e.key==='ArrowRight')next();if(e.key==='ArrowLeft')prev()});init();
</script></body></html>"""

class H(BaseHTTPRequestHandler):
    def log_message(self,*a):pass
    def sendj(self,o,s=200):
        d=json.dumps(o,ensure_ascii=False).encode("utf-8");self.send_response(s);self.send_header("Content-Type","application/json; charset=utf-8");self.send_header("Content-Length",str(len(d)));self.end_headers();self.wfile.write(d)
    def body(self):
        n=int(self.headers.get("Content-Length","0") or 0);return json.loads(self.rfile.read(n).decode("utf-8")) if n else {}
    def do_GET(self):
        if self.path=="/":
            d=HTML.encode("utf-8");self.send_response(200);self.send_header("Content-Type","text/html; charset=utf-8");self.send_header("Content-Length",str(len(d)));self.end_headers();self.wfile.write(d)
        elif self.path=="/api/state":self.sendj({"root":str(ROOT),"questions":QUESTIONS,"state":STATE})
        elif self.path.startswith("/api/progress"):
            self.sendj({k:STATE.get(k) for k in ("session_id","session_started","session_finished","auto_started","auto_running","auto_progress","auto_total","auto_current","auto_last","auto_error")})
        else:self.send_error(404)
    def do_POST(self):
        try:
            if self.path=="/api/start":
                b=self.body()
                if STATE.get("auto_running"):
                    self.sendj({"ok":False,"error":"Otomatik test devam ederken yeni oturum başlatılamaz."},409);return
                STATE["backend_url"]=b.get("backend_url") or STATE["backend_url"];STATE["session_id"]="beta-"+datetime.now().strftime("%Y%m%d-%H%M%S");STATE["session_started"]=now_iso();STATE["session_finished"]=None;STATE["marks"]={};STATE["last_auto"]=None;STATE["auto_started"]=False;STATE["auto_running"]=False;STATE["auto_progress"]=0;STATE["auto_total"]=len(QUESTIONS);STATE["auto_current"]=None;STATE["auto_last"]=None;STATE["auto_error"]=None;self.sendj({"ok":True,"session_id":STATE["session_id"]})
            elif self.path=="/api/mark":
                b=self.body();STATE["marks"][b["id"]]=b.get("value");self.sendj({"ok":True})
            elif self.path=="/api/auto-run":
                b=self.body();STATE["backend_url"]=b.get("backend_url") or STATE["backend_url"]
                if STATE.get("auto_running"):
                    self.sendj({"ok":False,"error":"Otomatik test zaten devam ediyor."},409);return
                if not STATE["session_id"]:
                    STATE["session_id"]="beta-"+datetime.now().strftime("%Y%m%d-%H%M%S")
                STATE["session_started"]=now_iso();STATE["session_finished"]=None
                STATE["last_auto"]=None;STATE["auto_started"]=True;STATE["auto_running"]=True;STATE["auto_progress"]=0;STATE["auto_total"]=len(QUESTIONS);STATE["auto_current"]=None;STATE["auto_last"]=None;STATE["auto_error"]=None
                sid=STATE["session_id"]
                def w():
                    out=[]
                    try:
                        for i,q in enumerate(QUESTIONS,1):
                            STATE["auto_current"]=q["id"]
                            result=ask(q["question"],q["id"],sid,STATE["backend_url"])
                            out.append({"id":q["id"],**result})
                            time.sleep(.05)
                            tel=latest_telemetry(q["id"],sid)
                            STATE["auto_progress"]=i
                            STATE["auto_last"]={"id":q["id"],"route":tel.get("route"),"subject":tel.get("subject"),"duration_ms":tel.get("duration_ms"),"elapsed_ms":result.get("elapsed_ms"),"ok":result.get("ok")}
                            time.sleep(.08)
                    except Exception as e:
                        STATE["auto_error"]=f"{type(e).__name__}: {e}"
                    finally:
                        STATE["last_auto"]=out;STATE["auto_current"]=None;STATE["auto_running"]=False;STATE["session_finished"]=now_iso()
                threading.Thread(target=w,daemon=True).start();self.sendj({"ok":True,"message":f"Otomatik test başladı. Session: {sid}. İlerleme ekranda canlı gösterilecek."})
            elif self.path=="/api/analyze":
                if STATE.get("auto_running") or not STATE.get("auto_started") or STATE.get("auto_progress",0)<STATE.get("auto_total",len(QUESTIONS)):
                    self.sendj({"ok":False,"error":"Final analiz kilitli: otomatik test 100 / 100 tamamlanmalı."},409);return
                self.sendj(analyze())
            else:self.send_error(404)
        except Exception as e:self.sendj({"ok":False,"error":f"{type(e).__name__}: {e}"},500)
def main():
    print("KODAAI Beta Test Runner");print("ROOT:",ROOT);print(f"UI: http://{APP_HOST}:{APP_PORT}")
    s=ThreadingHTTPServer((APP_HOST,APP_PORT),H);threading.Timer(.8,lambda:webbrowser.open(f"http://{APP_HOST}:{APP_PORT}")).start()
    try:s.serve_forever()
    except KeyboardInterrupt:pass
if __name__=="__main__":main()

