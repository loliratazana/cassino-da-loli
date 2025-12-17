# app.py — Kawaii Casino Ultimate (single-file final)
# Coloque na pasta do site. Crie pasta `static/` ao lado e adicione "minecraft.woff".
# Rodar local: pip install flask ; python app.py
# Deploy PythonAnywhere: faça upload, ajuste WSGI: from app import app as application

from flask import Flask, request, session, redirect, url_for, jsonify, render_template_string
import sqlite3, json, random, os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "kawaii-super-secret-2025"
DB = "kawaii_full.db"
ADMIN_PW = "420691618"

# -------------------- DB helpers --------------------
def get_conn():
    conn = sqlite3.connect(DB, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    c = get_conn().cursor()
    # users
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ip TEXT UNIQUE,
        name TEXT,
        points INTEGER DEFAULT 100,
        items TEXT DEFAULT '',
        plays INTEGER DEFAULT 0,
        created TEXT
    )
    """)
    # logs
    c.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        ip TEXT,
        ua TEXT,
        time TEXT,
        data TEXT
    )
    """)
    # shop items
    c.execute("""
    CREATE TABLE IF NOT EXISTS shop_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        price INTEGER
    )
    """)
    # seed shop if empty
    cnt = c.execute("SELECT COUNT(*) AS cnt FROM shop_items").fetchone()["cnt"]
    if cnt == 0:
        seed = [
            ("🎀 Badge Kawaii",50),
            ("🧁 Cupcake Charm",80),
            ("💎 Diamond Aura",150),
            ("👑 Crown Pixie",300)
        ]
        c.executemany("INSERT INTO shop_items(name,price) VALUES(?,?)", seed)
    c.connection.commit()
    c.connection.close()

init_db()

# -------------------- business helpers --------------------
def get_or_create_user(ip, name=None):
    conn = get_conn(); c = conn.cursor()
    u = c.execute("SELECT * FROM users WHERE ip=?", (ip,)).fetchone()
    if not u:
        created = datetime.utcnow().isoformat()
        c.execute("INSERT INTO users(ip,name,points,items,plays,created) VALUES(?,?,?,?,?,?)",
                  (ip, name or "Player", 100, "", 0, created))
        conn.commit()
        u = c.execute("SELECT * FROM users WHERE ip=?", (ip,)).fetchone()
    c.connection.close()
    return u

def update_user_name(uid, name):
    conn = get_conn(); c = conn.cursor()
    c.execute("UPDATE users SET name=? WHERE id=?", (name, uid))
    conn.commit(); c.connection.close()

def add_points(uid, amount):
    conn = get_conn(); c = conn.cursor()
    c.execute("UPDATE users SET points=points+? WHERE id=?", (amount, uid))
    conn.commit(); c.connection.close()

def spend_points(uid, amount):
    conn = get_conn(); c = conn.cursor()
    cur = c.execute("SELECT points FROM users WHERE id=?", (uid,)).fetchone()
    if not cur:
        c.connection.close(); return False
    if cur["points"] < amount:
        c.connection.close(); return False
    c.execute("UPDATE users SET points=points-? WHERE id=?", (amount, uid))
    conn.commit(); c.connection.close(); return True

def add_item(uid, item_name):
    conn = get_conn(); c = conn.cursor()
    cur = c.execute("SELECT items FROM users WHERE id=?", (uid,)).fetchone()
    items = (cur["items"] or "") + item_name + " "
    c.execute("UPDATE users SET items=? WHERE id=?", (items, uid))
    conn.commit(); c.connection.close()

def inc_play(uid):
    conn = get_conn(); c = conn.cursor()
    c.execute("UPDATE users SET plays=plays+1 WHERE id=?", (uid,))
    conn.commit(); c.connection.close()

def record_log(user_id, data):
    conn = get_conn(); c = conn.cursor()
    c.execute("INSERT INTO logs(user_id, ip, ua, time, data) VALUES(?,?,?,?,?)",
              (user_id, request.remote_addr, request.headers.get("User-Agent"), datetime.utcnow().isoformat(), json.dumps(data)))
    conn.commit(); c.connection.close()

def get_rank(limit=10):
    conn = get_conn(); c = conn.cursor()
    rows = c.execute("SELECT name, points FROM users ORDER BY points DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return rows

def get_shop():
    conn = get_conn(); c = conn.cursor()
    rows = c.execute("SELECT * FROM shop_items ORDER BY price").fetchall()
    conn.close()
    return rows

# -------------------- game logic --------------------
def run_jackpot():
    icons = ["🍓","🍒","⭐","💎","🍭"]
    roll = [random.choice(icons) for _ in range(3)]
    win = roll[0] == roll[1] == roll[2]
    return roll, win

# -------------------- CSS --------------------
BASE_CSS = """
<link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap" rel="stylesheet">
<style>
@font-face{ font-family: MinecraftLocal; src: url('/static/minecraft.woff') format('woff'); }
body{
  margin:0;
  font-family:'Press Start 2P', MinecraftLocal, monospace;
  background:linear-gradient(135deg,#ffd6e8,#ffc0e8);
  display:flex;
  justify-content:center;
  align-items:center;
  min-height:100vh;
}
.loader{
  display:flex;
  justify-content:center;
  align-items:center;
  gap:6px;
}
.loader span{
  width:12px;
  height:12px;
  background:#ff69b4;
  border-radius:50%;
  animation: bounce 0.6s infinite alternate;
}
.loader span:nth-child(2){animation-delay:0.2s;}
.loader span:nth-child(3){animation-delay:0.4s;}
@keyframes bounce{
  to{transform:translateY(-12px);}
}
.container{
  width:95%;
  max-width:1100px;
  background:white;
  border-radius:18px;
  padding:18px;
  box-shadow:0 20px 40px rgba(0,0,0,.12);
  animation: fadein 0.8s ease forwards;
}
@keyframes fadein{ from{opacity:0;transform:translateY(20px);} to{opacity:1;transform:translateY(0);} }
.header{display:flex;justify-content:space-between;align-items:center}
.h1{color:#ff2f92;font-size:22px}
.grid{display:grid;grid-template-columns:2fr 1fr;gap:14px;margin-top:12px}
.card{background:linear-gradient(180deg,#fff,#fff6fb);padding:14px;border-radius:12px;box-shadow:0 6px 14px rgba(0,0,0,.06);transition:0.3s}
.card:hover{transform:scale(1.02)}
.button{background:#ff69b4;color:white;border:none;padding:10px 14px;border-radius:999px;cursor:pointer;transition:0.3s}
.button:hover{transform:scale(1.05)}
.slot{font-size:52px;text-align:center;margin:10px 0}
.mem-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:10px}
.mem-cell{background:#fff0f7;border-radius:10px;padding:12px;text-align:center;cursor:pointer;font-size:26px}
.confetti{position:fixed;left:0;top:0;width:100%;height:100%;pointer-events:none}
.small{font-size:11px;color:#666}
.table{width:100%;border-collapse:collapse}
.table th,.table td{border:1px solid #fde6f1;padding:8px;font-size:12px}
.right-panel{display:flex;flex-direction:column;gap:10px}
.item{display:flex;justify-content:space-between;align-items:center;padding:8px;background:#fff8fb;border-radius:8px}
.score{font-size:13px;color:#ff2f92}
.menu-dots{position:absolute;top:18px;right:18px;cursor:pointer;font-size:28px;color:#ff69b4;}
.menu-dots:hover{color:#ff2fda;}
.avatar{display:flex;flex-wrap:wrap;gap:4px;margin-top:8px;}
.avatar .part{width:48px;height:48px;background:#ffe0f0;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:28px;cursor:pointer;transition:0.2s}
.avatar .part.selected{border:2px solid #ff2f92}
</style>
"""

# -------------------- HOME HTML --------------------
HOME_HTML = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Kawaii Casino</title>
{{ css }}
</head>
<body>
<div class="loader" id="loader">
  <span></span><span></span><span></span>
</div>

<div class="container" id="mainContent" style="display:none;">
  <div class="header">
    <div class="h1">🌸 Kawaii Casino</div>
    <div><a href="{{ url_for('terms') }}" class="small">Termos</a> • <a href="{{ url_for('admin') }}" class="small">Admin</a></div>
  </div>

  <div class="card" style="margin-top:12px">
    <form method="post">
      <label>Apelido: <input name="nickname" required style="font-family:inherit;padding:8px;margin-left:8px;font-size:16px"></label><br><br>
      <input type="hidden" name="screen" id="screen">
      <input type="hidden" name="viewport" id="viewport">
      <input type="hidden" name="language" id="language">
      <input type="hidden" name="platform" id="platform">
      <input type="hidden" name="cores" id="cores">
      <input type="hidden" name="memory" id="memory">
      <input type="hidden" name="touch" id="touch">
      <label style="display:block;margin-top:10px">
        <input type="checkbox" name="accept" value="yes" required> Aceito os termos e autorizo coleta técnica (apenas para estatísticas)
      </label>
      <div style="margin-top:12px"><button class="button">Entrar ✨</button></div>
      <div class="small" style="margin-top:8px">• Você receberá 100 pts ao entrar pela primeira vez.</div>
    </form>
  </div>
</div>

<script>
setTimeout(()=>{
  document.getElementById('loader').style.display='none';
  document.getElementById('mainContent').style.display='block';
}, 1200);

document.getElementById('screen').value = screen.width + 'x' + screen.height;
document.getElementById('viewport').value = innerWidth + 'x' + innerHeight;
document.getElementById('language').value = navigator.language || '';
document.getElementById('platform').value = navigator.platform || '';
document.getElementById('cores').value = navigator.hardwareConcurrency || '';
document.getElementById('memory').value = navigator.deviceMemory || '';
document.getElementById('touch').value = ('ontouchstart' in window) ? 'yes' : 'no';
</script>
</body>
</html>
"""

# -------------------- ROUTES --------------------
@app.route("/", methods=["GET","POST"])
def home():
    if request.method=="POST":
        if request.form.get("accept")!="yes":
            return "Consentimento necessário.", 400
        nickname = request.form.get("nickname") or "Player"
        ip = request.remote_addr
        u = get_or_create_user(ip, nickname)
        update_user_name(u["id"], nickname)
        extra = {k: request.form.get(k) for k in ("screen","viewport","language","platform","cores","memory","touch")}
        record_log(u["id"], extra)
        session["uid"] = u["id"]
        return redirect(url_for('casino'))
    return render_template_string(HOME_HTML, css=BASE_CSS)

# -------------------- TERMS --------------------
TERMS_HTML = """
<!doctype html>
<html>
<head><meta charset="utf-8"><title>Termos</title>{{ css }}</head>
<body>
<div class="container">
<div class="card">
<h2>📜 Termos de Uso</h2>
<p>• Coletamos APENAS dados técnicos após consentimento.</p>
<p>• Dados coletados: IP, User-Agent, idioma, resolução, plataforma, número de pontos, compras e ações de jogo.</p>
<p>• Uso apenas para estatísticas e segurança. Cassino fictício, sem dinheiro real.</p>
</div>
</div>
</body>
</html>
"""
@app.route("/terms")
def terms():
    return render_template_string(TERMS_HTML, css=BASE_CSS)

# -------------------- CASINO --------------------
CASINO_HTML = """
<!doctype html>
<html>
<head><meta charset="utf-8"><title>Casino</title>{{ css }}</head>
<body>
<div class="container">
  <div class="header">
    <div class="h1">🎰 Kawaii Casino</div>
    <div style="text-align:right">
      <div class="score">✨ {{ user['name'] }} • {{ user['points'] }} pts</div>
      <small><a href="{{ url_for('home') }}">Home</a> • <a href="{{ url_for('admin') }}">Admin</a></small>
    </div>
    <div class="menu-dots" onclick="toggleMenu()">⋮</div>
  </div>

  <div id="menuPanel" style="display:none;margin-top:12px">
    <button class="button" onclick="showTab('jackpot')">🎰 Jackpot</button>
    <button class="button" onclick="showTab('memory')">🧠 Memória</button>
    <button class="button" onclick="showTab('avatar')">👤 Avatar</button>
    <button class="button" onclick="showTab('shop')">🛍 Loja</button>
  </div>

  <div id="jackpotTab" class="card tab" style="margin-top:12px;">
    <h3>🎰 Jackpot</h3>
    <div class="slot" id="slot">{{ roll_display }}</div>
    <div style="text-align:center">
      <input type="number" id="jackBet" placeholder="Aposta pts" style="width:80px;font-family:inherit;margin-bottom:6px">
      <button class="button" onclick="playJackpot()">GIRAR</button>
    </div>
    <div id="jack-msg" class="small"></div>
  </div>

  <div id="memoryTab" class="card tab" style="margin-top:12px; display:none;">
    <h3>🧠 Memória</h3>
    <div id="mem" class="mem-grid"></div>
    <div id="mem-msg" class="small"></div>
  </div>

  <div id="avatarTab" class="card tab" style="margin-top:12px; display:none;">
    <h3>👤 Avatar</h3>
    <div class="avatar" id="avatarDisplay"></div>
    <div class="small">Clique nas partes para adicionar/remover itens da loja.</div>
  </div>

  <div id="shopTab" class="card tab" style="margin-top:12px; display:none;">
    <h3>🛍 Loja</h3>
    {% for it in shop %}
      <div class="item">
        <div>{{ it['name'] }} <small class="small">({{ it['price'] }} pts)</small></div>
        <form method="post" action="{{ url_for('buy') }}" style="margin:0">
          <input type="hidden" name="item_id" value="{{ it['id'] }}">
          <button class="button">Comprar</button>
        </form>
      </div>
    {% endfor %}
  </div>

  <div class="card" style="margin-top:12px;">
    <h3>🏆 Ranking</h3>
    {% for r in rank %}
      <div style="display:flex;justify-content:space-between">
        <div>{{ loop.index }}. {{ r['name']|e }}</div>
        <div>{{ r['points'] }} pts</div>
      </div>
    {% endfor %}
  </div>

</div>

<canvas id="confetti" class="confetti"></canvas>

<!-- sounds -->
<audio id="snd-spin" src="https://assets.mixkit.co/sfx/preview/mixkit-arcade-retro-game-over-213.wav"></audio>
<audio id="snd-win" src="https://assets.mixkit.co/sfx/preview/mixkit-game-bonus-reached-2065.mp3"></audio>

<script>
function toggleMenu(){
  let panel = document.getElementById('menuPanel');
  panel.style.display = panel.style.display==='none'?'block':'none';
}
function showTab(name){
  document.querySelectorAll('.tab').forEach(t=>t.style.display='none');
  document.getElementById(name+'Tab').style.display='block';
}

// ---------------- Jackpot ----------------
function playJackpot(){
  let bet = parseInt(document.getElementById('jackBet').value)||1;
  fetch("{{ url_for('api_jackpot') }}", {method:'POST'}).then(r=>r.json()).then(d=>{
    document.getElementById('slot').textContent = d.roll
