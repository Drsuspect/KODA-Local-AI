from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn

from grammar_engine import analyze_record as grammar_analyze
from pedagogy_engine import analyze_record as pedagogy_analyze

ROOT = Path(__file__).resolve().parents[2]
DATA_FILE = Path(os.getenv(
    "KODAAI_REASONING_FILE",
    ROOT / "training_data" / "wrong_answer_reasoning_v0_1" / "ekpss_100_draft.jsonl",
))
BACKUP_DIR = ROOT / "training_data" / "wrong_answer_reasoning_v0_1" / "review_backups"

app = FastAPI(title="KODAAI Reasoning Review", version="0.1")


class SavePayload(BaseModel):
    record: dict[str, Any]
    reviewer: str | None = None
    target_status: str = "draft"


def load_rows() -> list[dict[str, Any]]:
    rows = []
    for line in DATA_FILE.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def write_rows(rows: list[dict[str, Any]]) -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup = BACKUP_DIR / f"{DATA_FILE.stem}_{stamp}.jsonl"
    backup.write_text(DATA_FILE.read_text(encoding="utf-8"), encoding="utf-8")
    tmp = DATA_FILE.with_suffix(".tmp")
    tmp.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    tmp.replace(DATA_FILE)


@app.get("/api/records")
def records(offset: int = 0, limit: int = Query(20, ge=1, le=100), status: str | None = None):
    rows = load_rows()
    if status:
        rows = [r for r in rows if (r.get("validation") or {}).get("status") == status]
    return {"count": len(rows), "records": rows[offset:offset+limit]}


@app.get("/api/record/{record_id}")
def record(record_id: str):
    for row in load_rows():
        if row.get("id") == record_id:
            return {
                "record": row,
                "grammar": grammar_analyze(row),
                "pedagogy": pedagogy_analyze(row),
            }
    raise HTTPException(404, "record not found")


@app.post("/api/record/{record_id}")
def save_record(record_id: str, payload: SavePayload):
    rows = load_rows()
    idx = next((i for i, r in enumerate(rows) if r.get("id") == record_id), None)
    if idx is None:
        raise HTTPException(404, "record not found")
    if payload.record.get("id") != record_id:
        raise HTTPException(400, "record id cannot change")

    grammar = grammar_analyze(payload.record)
    pedagogy = pedagogy_analyze(payload.record)
    target = payload.target_status
    if target not in {"draft", "reviewed", "verified"}:
        raise HTTPException(400, "invalid target_status")
    if target in {"reviewed", "verified"} and not (payload.reviewer or "").strip():
        raise HTTPException(400, "reviewer is required")
    if target == "verified" and (grammar["status"] == "fail" or pedagogy["readiness"] == "blocked"):
        raise HTTPException(409, "record has blocking grammar/pedagogy findings")

    rec = payload.record
    rec.setdefault("validation", {})
    rec["validation"]["status"] = target
    rec["validation"]["reviewer"] = (payload.reviewer or None)
    rec["validation"]["notes"] = (
        f"Grammar={grammar['status']}; pedagogy={pedagogy['readiness']}; "
        f"reviewed_at={datetime.now().isoformat(timespec='seconds')}"
    )
    rows[idx] = rec
    write_rows(rows)
    return {"ok": True, "record": rec, "grammar": grammar, "pedagogy": pedagogy}


@app.get("/", response_class=HTMLResponse)
def index():
    return HTML


HTML = r"""<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>KODAAI Reasoning Review</title>
<style>
:root{font-family:Arial,sans-serif;color-scheme:dark}body{margin:0;background:#0d1117;color:#f0f6fc}header{padding:16px 20px;border-bottom:1px solid #30363d}
main{display:grid;grid-template-columns:320px 1fr;min-height:calc(100vh - 70px)}aside{border-right:1px solid #30363d;padding:14px;overflow:auto}
section{padding:18px;overflow:auto}.card{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:14px;margin-bottom:12px}
button,select,input,textarea{font:inherit}button{padding:8px 11px;border-radius:8px;border:1px solid #58a6ff;background:#1f6feb;color:white;cursor:pointer}
input,select,textarea{background:#0d1117;color:#f0f6fc;border:1px solid #30363d;border-radius:8px;padding:8px}textarea{width:100%;box-sizing:border-box;min-height:85px}
.item{display:block;width:100%;text-align:left;margin:6px 0;background:#21262d;border-color:#484f58}.ok{color:#3fb950}.warn{color:#d29922}.fail{color:#f85149}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.option{border-left:4px solid #30363d}.correct{border-left-color:#3fb950}
pre{white-space:pre-wrap;word-break:break-word}.sources a{color:#58a6ff;display:block;margin:5px 0}.toolbar{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
@media(max-width:900px){main{grid-template-columns:1fr}aside{border-right:0;border-bottom:1px solid #30363d;max-height:260px}.grid{grid-template-columns:1fr}}
</style></head><body>
<header><strong>KODAAI · Neden Yanlış? İnceleme + Dilbilgisi + Pedagoji v0.1</strong></header>
<main><aside><div class="toolbar"><button onclick="loadList()">Yenile</button><select id="status" onchange="loadList()"><option value="">Tümü</option><option>draft</option><option>reviewed</option><option>verified</option></select></div><div id="list"></div></aside>
<section><div id="empty" class="card">Soldan bir kayıt seçin.</div><div id="editor" hidden>
<div class="card"><div class="toolbar"><input id="reviewer" placeholder="İnceleyen kişi"><button onclick="save('draft')">Taslak Kaydet</button><button onclick="save('reviewed')">Reviewed</button><button onclick="save('verified')">Verified</button></div><p id="saveMsg"></p></div>
<div class="card"><h2 id="rid"></h2><textarea id="question" style="min-height:180px"></textarea></div>
<div id="options" class="grid"></div>
<div class="card"><h3>Pedagoji</h3><label>İpucu</label><textarea id="hint"></textarea><label>Açıklama</label><textarea id="explain"></textarea><label>Basitleştir</label><textarea id="simplify"></textarea><label>Örnek</label><textarea id="example"></textarea><label>Anlama Kontrolü</label><textarea id="check"></textarea></div>
<div class="grid"><div class="card"><h3>Dilbilgisi Motoru</h3><div id="grammar"></div></div><div class="card"><h3>Pedagojik Kontrol</h3><div id="pedagogy"></div></div></div>
<div class="card sources"><h3>Doğrulama Kaynakları</h3><div id="sources"></div></div>
</div></section></main>
<script>
let current=null;
async function j(url,opt){const r=await fetch(url,opt);if(!r.ok)throw new Error(await r.text());return r.json()}
async function loadList(){const s=document.getElementById('status').value;const d=await j('/api/records?limit=100'+(s?'&status='+s:''));const el=document.getElementById('list');el.innerHTML='';for(const r of d.records){const b=document.createElement('button');b.className='item';b.textContent=r.id+' · '+r.validation.status;b.onclick=()=>openRec(r.id);el.appendChild(b)}}
function esc(x){return (x??'').toString()}
async function openRec(id){const d=await j('/api/record/'+encodeURIComponent(id));current=d.record;document.getElementById('empty').hidden=true;document.getElementById('editor').hidden=false;document.getElementById('rid').textContent=current.id+' · doğru: '+current.correct_answer;document.getElementById('question').value=current.question;
const opts=document.getElementById('options');opts.innerHTML='';for(const k of ['A','B','C','D','E']){const o=current.options[k];const div=document.createElement('div');div.className='card option '+(o.is_correct?'correct':'');div.innerHTML='<h3>'+k+' · '+esc(o.text)+'</h3><textarea id="reason_'+k+'"></textarea>';opts.appendChild(div);document.getElementById('reason_'+k).value=o.reason}
const p=current.pedagogy||{};for(const [id,key] of [['hint','hint'],['explain','explain'],['simplify','simplify'],['example','example'],['check','check_understanding']])document.getElementById(id).value=p[key]||'';
renderReport('grammar',d.grammar);renderReport('pedagogy',d.pedagogy);const src=document.getElementById('sources');src.innerHTML='';for(const s of d.grammar.sources){const a=document.createElement('a');a.href=s.url;a.target='_blank';a.rel='noreferrer';a.textContent=s.label+' ['+s.authority+']';src.appendChild(a)}}
function renderReport(id,r){const el=document.getElementById(id);const state=r.status||r.readiness;el.innerHTML='<p class="'+(state==='pass'||state==='ready'?'ok':state==='fail'||state==='blocked'?'fail':'warn')+'"><strong>'+state+'</strong></p>';for(const f of (r.findings||[])){const p=document.createElement('p');p.className=f.severity;p.textContent=f.severity.toUpperCase()+' · '+f.code+' · '+f.message;el.appendChild(p)}if(r.evidence?.length){const pre=document.createElement('pre');pre.textContent=JSON.stringify(r.evidence,null,2);el.appendChild(pre)}}
function collect(){current.question=document.getElementById('question').value;for(const k of ['A','B','C','D','E'])current.options[k].reason=document.getElementById('reason_'+k).value;current.pedagogy={...current.pedagogy,hint:document.getElementById('hint').value,explain:document.getElementById('explain').value,simplify:document.getElementById('simplify').value,example:document.getElementById('example').value,check_understanding:document.getElementById('check').value};return current}
async function save(target){try{const d=await j('/api/record/'+encodeURIComponent(current.id),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({record:collect(),reviewer:document.getElementById('reviewer').value,target_status:target})});current=d.record;document.getElementById('saveMsg').className='ok';document.getElementById('saveMsg').textContent='Kaydedildi: '+target;renderReport('grammar',d.grammar);renderReport('pedagogy',d.pedagogy);loadList()}catch(e){document.getElementById('saveMsg').className='fail';document.getElementById('saveMsg').textContent=e.message}}
loadList();
</script></body></html>"""


if __name__ == "__main__":
    uvicorn.run(app, host=os.getenv("KODAAI_REVIEW_HOST", "127.0.0.1"), port=int(os.getenv("KODAAI_REVIEW_PORT", "8091")))
