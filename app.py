from flask import Flask, request, redirect, session, url_for, render_template_string
import sqlite3, os

app = Flask(__name__)
app.secret_key = os.urandom(24)

# --- HTML Templates ---
login_html = '''<!DOCTYPE html>
<html><head><title>Bem-vindo - Kawaii Game</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
body { display: flex; justify-content: center; align-items: center; background: pink; height: 100vh; margin:0; font-family: Arial, sans-serif; }
.loader { border: 10px solid #f3f3f3; border-top: 10px solid deeppink; border-radius: 50%; width: 100px; height: 100px; animation: spin 2s linear infinite; }
@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
#login-form { display: none; flex-direction: column; align-items: center; text-align: center; }
input, button { padding: 10px; margin: 5px; border: 1px solid deeppink; border-radius: 5px; }
button { background: deeppink; color: white; cursor: pointer; }
</style>
</head>
<body>
  <div id="loader" class="loader"></div>
  <div id="login-form">
    <h2>Bem-vindo ao Kawaii Game!</h2>
    <form method="post">
      <input type="text" name="name" placeholder="Seu nome" required><br>
      <button type="submit">Entrar</button>
    </form>
  </div>
<script>
window.addEventListener('load', () => {
  setTimeout(() => {
    document.getElementById('loader').style.display = 'none';
    document.getElementById('login-form').style.display = 'flex';
  }, 2000);
});
</script>
</body></html>'''
main_html = '''<!DOCTYPE html>
<html><head><title>Kawaii Game</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
body { background: pink; color: #333; font-family: 'Comic Sans MS', cursive, sans-serif; margin: 0; padding: 0; }
header { text-align: center; padding: 10px; background: deeppink; color: white; }
header h1 { margin: 0; font-size: 24px; }
nav { display: flex; justify-content: center; margin: 10px; }
nav div { width: 20px; height: 20px; border-radius: 50%; background: deeppink; margin: 0 5px; cursor: pointer; }
nav div.active { background: mediumvioletred; }
.section { display: none; padding: 20px; text-align: center; }
.section.active { display: block; }
button { padding: 10px 20px; background: mediumvioletred; color: white; border: none; border-radius: 5px; cursor: pointer; margin: 5px;}
input[type=number] { padding: 5px; width: 60px; }
#points { position: fixed; top: 10px; right: 10px; background: #ffefff; padding: 10px; border: 2px solid deeppink; border-radius: 5px; }
.rankings { margin-top: 20px; }
#avatar-display { font-size: 80px; }
.confetti {
  position: fixed; width: 10px; height: 10px; background: gold; z-index: 1000;
  animation: fall 2s linear forwards;
}
@keyframes fall { 100% { transform: translateY(100vh); opacity: 0; } }
</style>
</head>
<body>
<header><h1>Bem-vindo, {{ user }}!</h1></header>
<div id="points">Pontos: <span id="points-value">{{ points }}</span></div>
<nav>
  <div id="tab-games" class="active" title="Jogos"></div>
  <div id="tab-store" title="Loja"></div>
  <div id="tab-avatar" title="Avatar"></div>
</nav>
<div id="games-section" class="section active">
  <h2>Jogos</h2>
  <div>
    <h3>Jackpot</h3>
    <p>Faça sua aposta:</p>
    <input type="number" id="bet-jackpot" min="1" placeholder="0"><button onclick="playJackpot()">Jogar</button>
    <p id="jackpot-result"></p>
  </div>
  <hr>
  <div>
    <h3>Memória</h3>
    <p>Faça sua aposta:</p>
    <input type="number" id="bet-memory" min="1" placeholder="0"><button onclick="playMemory()">Jogar</button>
    <p id="memory-result"></p>
  </div>
  <hr>
  <div>
    <h3>Carta da Sorte</h3>
    <p>Faça sua aposta:</p>
    <input type="number" id="bet-luck" min="1" placeholder="0"><button onclick="playLuck()">Jogar</button>
    <p id="luck-result"></p>
  </div>
  <div class="rankings">
    <h3>Ranking</h3>
    <ol>
      {% for name, pts in ranking %}
      <li>{{ name }} - {{ pts }} pts</li>
      {% endfor %}
    </ol>
  </div>
</div>
<div id="store-section" class="section">
  <h2>Loja</h2>
  <div>
    {% for aid, name, cost in accessories %}
      <div>
        <span>{{ name }} - {{ cost }} pts</span>
        {% if aid in owned %}
          <button disabled>Comprado</button>
        {% else %}
          <button onclick="buyItem({{ aid }})">Comprar</button>
        {% endif %}
      </div>
    {% endfor %}
  </div>
</div>
<div id="avatar-section" class="section">
  <h2>Avatar</h2>
  <div id="avatar-display">
    {% if owned.get(3) and owned[3] %}👑{% endif %}
    {% if owned.get(1) and owned[1] %}🏅{% endif %}
    😊
    {% if owned.get(2) and owned[2] %}✨{% endif %}
  </div>
  <p>Você possui:
    {% for aid, name, cost in accessories if aid in owned %}
      {{ name }}{% if owned[aid] %} (equipado){% endif %};
    {% endfor %}
  </p>
  <p>Para equipar, compre na loja e recarregue a página.</p>
</div>

<!-- Sons de vitória/derrota (base64) -->
<audio id="winSound" src="data:audio/wav;base64,''' + '' + '''" preload="auto"></audio>
<audio id="loseSound" src="data:audio/wav;base64,''' + '' + '''" preload="auto"></audio>

<script>
// Navegação por abas
document.getElementById('tab-games').onclick = () => showSection('games');
document.getElementById('tab-store').onclick = () => showSection('store');
document.getElementById('tab-avatar').onclick = () => showSection('avatar');
function showSection(section) {
    ['games','store','avatar'].forEach(s => {
        document.getElementById('tab-'+s).classList.remove('active');
        document.getElementById(s+'-section').classList.remove('active');
    });
    document.getElementById('tab-'+section).classList.add('active');
    document.getElementById(section+'-section').classList.add('active');
}
// Atualiza pontos na tela
function updatePoints(pts) {
    document.getElementById('points-value').innerText = pts;
}
// Jogos
function playJackpot() {
    let bet = parseInt(document.getElementById('bet-jackpot').value);
    let resultP = document.getElementById('jackpot-result');
    resultP.innerText = '';
    if (!bet || bet < 1) { resultP.innerText = 'Aposta inválida.'; return; }
    fetch('/play_jackpot', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({bet: bet})
    })
    .then(res => res.json())
    .then(data => {
        if (data.win) {
            resultP.innerText = 'Você ganhou ' + data.earn + ' pontos!';
            triggerWinEffects();
        } else {
            resultP.innerText = 'Você perdeu ' + data.loss + ' pontos.';
            triggerLoseEffects();
        }
        updatePoints(data.points);
    });
}
function playMemory() {
    let bet = parseInt(document.getElementById('bet-memory').value);
    let resultP = document.getElementById('memory-result');
    resultP.innerText = '';
    if (!bet || bet < 1) { resultP.innerText = 'Aposta inválida.'; return; }
    fetch('/play_memory', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({bet: bet})
    })
    .then(res => res.json())
    .then(data => {
        if (data.win) {
            resultP.innerText = 'Você ganhou ' + data.earn + ' pontos!';
            triggerWinEffects();
        } else {
            resultP.innerText = 'Você perdeu ' + data.loss + ' pontos.';
            triggerLoseEffects();
        }
        updatePoints(data.points);
    });
}
function playLuck() {
    let bet = parseInt(document.getElementById('bet-luck').value);
    let resultP = document.getElementById('luck-result');
    resultP.innerText = '';
    if (!bet || bet < 1) { resultP.innerText = 'Aposta inválida.'; return; }
    fetch('/play_luck', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({bet: bet})
    })
    .then(res => res.json())
    .then(data => {
        if (data.win) {
            resultP.innerText = 'Você ganhou ' + data.earn + ' pontos!';
            triggerWinEffects();
        } else {
            resultP.innerText = 'Você perdeu ' + data.loss + ' pontos.';
            triggerLoseEffects();
        }
        updatePoints(data.points);
    });
}
// Comprar item na loja
function buyItem(id) {
    fetch('/buy', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({item_id: id})
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            alert('Compra bem-sucedida!');
            location.reload();
        } else {
            alert(data.message);
        }
    });
}
// Efeitos de vitória
function triggerWinEffects() {
    document.getElementById('winSound').play();
    for (let i = 0; i < 30; i++) {
        let conf = document.createElement('div');
        conf.classList.add('confetti');
        conf.style.left = Math.random() * 100 + 'vw';
        conf.style.background = '#' + Math.floor(Math.random()*16777215).toString(16);
        document.body.appendChild(conf);
        setTimeout(() => conf.remove(), 2000);
    }
}
function triggerLoseEffects() {
    document.getElementById('loseSound').play();
}
</script>
</body></html>'''
