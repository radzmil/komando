"""Shared incident memory. No third-party dependencies or infrastructure privileges."""

import json
import os
import sqlite3
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
import hmac
from diagnostics import diagnose

DB_PATH = Path(os.environ.get("KOMANDO_DB", str(Path(__file__).with_name("memory.sqlite3"))))
MAX_BODY = 8192


def connect():
    if os.environ.get("DATABASE_URL"):
        import psycopg2
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        with conn.cursor() as cursor:
            cursor.execute("""CREATE TABLE IF NOT EXISTS komando_memories (
                id BIGSERIAL PRIMARY KEY, client_id TEXT NOT NULL, source TEXT NOT NULL,
                content TEXT NOT NULL, created_at TEXT NOT NULL)""")
        conn.commit()
        return conn
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("""CREATE TABLE IF NOT EXISTS memories (
        id INTEGER PRIMARY KEY, client_id TEXT NOT NULL, source TEXT NOT NULL,
        content TEXT NOT NULL, created_at TEXT NOT NULL)""")
    return conn


def query(conn, sql, params=()):
    if os.environ.get("DATABASE_URL"):
        cursor = conn.cursor()
        cursor.execute(sql.replace("?", "%s").replace("memories", "komando_memories"), params)
        return cursor
    return conn.execute(sql, params)


PAGE = """<!doctype html><html lang="ms"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>KOMANDO</title><style>body{font:16px system-ui;max-width:700px;margin:2em auto;padding:0 1em;background:#101827;color:#f2f5fa}input,textarea,button{font:inherit;padding:.7em;margin:.4em 0;width:100%;box-sizing:border-box}article{background:#202d40;padding:1em;margin:1em 0;border-radius:8px;white-space:pre-wrap}small{color:#b8c6d8}</style>
<h1>KOMANDO</h1><p>Memori insiden bersama. Jangan masukkan token atau kata laluan.</p>
<label>Client ID<input id="client" value="CLI-1001" maxlength="80"></label>
<button onclick="load()">Muat memori</button><form id="form"><textarea id="content" maxlength="4000" required placeholder="Ringkasan insiden"></textarea><button>Simpan catatan</button></form><p id="notice"></p><div id="list"></div>
<script>
let key=sessionStorage.getItem('komando_key')||prompt('Kunci akses KOMANDO');
if(key)sessionStorage.setItem('komando_key',key);
const headers=()=>({'Authorization':'Bearer '+key});
const notice=document.getElementById('notice');
async function load(){let client=document.getElementById('client').value.trim();
try{let r=await fetch('/memories?client_id='+encodeURIComponent(client),{headers:headers()});if(!r.ok)throw Error('HTTP '+r.status);
let data=await r.json(),list=document.getElementById('list');list.replaceChildren();
for(let m of data.memories){let a=document.createElement('article'),s=document.createElement('small');s.textContent=m.source+' · '+m.created_at;a.append(s,document.createElement('br'),document.createTextNode(m.content));list.append(a)}notice.textContent='';}
catch(e){notice.textContent='Tidak berjaya: '+e.message}}
document.getElementById('form').onsubmit=async e=>{e.preventDefault();try{let r=await fetch('/memories',{method:'POST',headers:{...headers(),'Content-Type':'application/json'},body:JSON.stringify({client_id:document.getElementById('client').value.trim(),source:'phone',content:document.getElementById('content').value})});if(!r.ok)throw Error('HTTP '+r.status);document.getElementById('content').value='';await load()}catch(err){notice.textContent='Tidak berjaya: '+err.message}};
if(key)load();</script></html>"""


class Handler(BaseHTTPRequestHandler):
    def respond(self, code, data):
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def authorized(self):
        secret = os.environ.get("KOMANDO_API_KEY", "")
        supplied = self.headers.get("Authorization", "")
        return len(secret) >= 32 and hmac.compare_digest(supplied, "Bearer " + secret)

    def page(self):
        payload = PAGE.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path == "/":
            return self.page()
        if not self.authorized():
            return self.respond(401, {"error": "unauthorized"})
        parsed = urlsplit(self.path)
        if parsed.path != "/memories":
            return self.respond(404, {"error": "not found"})
        client = parse_qs(parsed.query).get("client_id", [""])[0]
        if not client or len(client) > 80:
            return self.respond(400, {"error": "client_id required"})
        with connect() as conn:
            rows = query(conn, "SELECT id, source, content, created_at FROM memories "
                         "WHERE client_id=? ORDER BY id DESC LIMIT 30", (client,)).fetchall()
        self.respond(200, {"client_id": client, "memories": [dict(zip(
            ("id", "source", "content", "created_at"), row)) for row in rows]})

    def do_POST(self):
        if not self.authorized():
            return self.respond(401, {"error": "unauthorized"})
        if self.path == "/diagnose":
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 256:
                    return self.respond(400, {"error": "invalid size"})
                client = json.loads(self.rfile.read(size)).get("client_id")
                if client != "CLI-1001":
                    return self.respond(400, {"error": "client not configured"})
            except (ValueError, TypeError, AttributeError):
                return self.respond(400, {"error": "invalid JSON"})
            result = diagnose(client)
            with connect() as conn:
                query(conn, "INSERT INTO memories (client_id, source, content, created_at) VALUES (?, ?, ?, ?)",
                      (client, "diagnostic", result["status"] + ": " + result["detail"],
                       datetime.now(timezone.utc).isoformat()))
            return self.respond(200, result)
        if self.path != "/memories":
            return self.respond(404, {"error": "not found"})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= MAX_BODY:
                return self.respond(413, {"error": "invalid size"})
            data = json.loads(self.rfile.read(size))
            client, source, content = (data.get(key) for key in ("client_id", "source", "content"))
            if (not all(isinstance(value, str) and value.strip() for value in (client, source, content))
                    or len(client) > 80 or source not in ("cline", "whatsapp", "phone") or len(content) > 4000):
                return self.respond(400, {"error": "invalid memory"})
        except (ValueError, TypeError, AttributeError, json.JSONDecodeError):
            return self.respond(400, {"error": "invalid JSON"})
        with connect() as conn:
            timestamp = datetime.now(timezone.utc).isoformat()
            if os.environ.get("DATABASE_URL"):
                cursor = query(conn, "INSERT INTO memories (client_id, source, content, created_at) "
                               "VALUES (?, ?, ?, ?) RETURNING id", (client, source, content, timestamp))
                memory_id = cursor.fetchone()[0]
            else:
                cursor = query(conn, "INSERT INTO memories (client_id, source, content, created_at) "
                               "VALUES (?, ?, ?, ?)", (client, source, content, timestamp))
                memory_id = cursor.lastrowid
        self.respond(201, {"id": memory_id})


if __name__ == "__main__":
    if len(os.environ.get("KOMANDO_API_KEY", "")) < 32:
        raise SystemExit("Set KOMANDO_API_KEY (at least 32 characters)")
    ThreadingHTTPServer((os.environ.get("KOMANDO_HOST", "127.0.0.1"),
                         int(os.environ.get("PORT", os.environ.get("KOMANDO_PORT", "8765")))), Handler).serve_forever()