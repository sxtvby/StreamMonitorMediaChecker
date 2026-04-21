from flask import Flask, render_template, request, jsonify, redirect, session, send_file
import requests, time, socket
from datetime import datetime
from db import get_db, init_db
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "supersecret"

init_db()

# ===== CREAR ADMIN =====
db = get_db()
try:
    db.execute("INSERT INTO users (username,password) VALUES (?,?)",
               ("admin", generate_password_hash("admin123")))
    db.commit()
except:
    pass

# ===== LOGIN =====
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        user = request.form["user"]
        password = request.form["password"]

        db = get_db()
        u = db.execute("SELECT * FROM users WHERE username=?", (user,)).fetchone()

        if u and check_password_hash(u[2], password):
            session["user"] = user
            return redirect("/")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

def auth():
    return "user" in session

# ===== FORMATO FECHA =====
def format_fecha(ts):
    try:
        return datetime.fromtimestamp(int(ts)).strftime('%d/%m/%Y')
    except:
        return "N/A"

# ===== DETECCIÓN AVANZADA =====
def detectar_servidor(base):
    try:
        host = base.replace("http://","").replace("https://","").split(":")[0]

        ip = socket.gethostbyname(host)

        geo = requests.get(f"http://ip-api.com/json/{ip}", timeout=5).json()

        return {
            "ip": ip,
            "pais": geo.get("country", "N/A"),
            "isp": geo.get("isp", "N/A"),
            "timezone_geo": geo.get("timezone", "N/A")
        }
    except:
        return {
            "ip": "N/A",
            "pais": "N/A",
            "isp": "N/A",
            "timezone_geo": "N/A"
        }

# ===== VERIFICACIÓN PRO =====
def verificar(url):
    try:
        if "username=" in url and "password=" in url:

            base = url.split("/get.php")[0]
            user = url.split("username=")[1].split("&")[0]
            password = url.split("password=")[1].split("&")[0]

            # ⏱️ LATENCIA
            start = time.time()
            api = f"{base}/player_api.php?username={user}&password={password}"
            r = requests.get(api, timeout=8)
            latency = round((time.time() - start) * 1000)

            if r.status_code != 200:
                return None

            data = r.json()
            info = data.get("user_info", {})
            server = data.get("server_info", {})

            if info.get("auth") != 1:
                return None

            # 📡 CANALES
            try:
                m3u = requests.get(url, timeout=8).text
                canales = m3u.count("#EXTINF")
                if canales < 5:
                    return None
            except:
                return None

            # 🌍 GEO INFO
            geo = detectar_servidor(base)

            # 🕰️ TIMEZONE FINAL
            timezone = (
                server.get("timezone")
                or info.get("timezone")
                or geo.get("timezone_geo")
                or "Desconocido"
            )

            return {
                "user": user,
                "pass": password,
                "exp": format_fecha(info.get("exp_date")),
                "created": format_fecha(info.get("created_at")),
                "active": info.get("active_cons", 0),
                "max": info.get("max_connections", 0),
                "timezone": timezone,
                "server": base,
                "m3u": url,
                "pais": geo["pais"],
                "isp": geo["isp"],
                "ip": geo["ip"],
                "latency": latency,
                "canales": canales
            }

        return None

    except:
        return None

# ===== HOME =====
@app.route("/")
def home():
    if not auth():
        return redirect("/login")
    return render_template("index.html")

# ===== SCAN =====
@app.route("/scan", methods=["POST"])
def scan():
    urls = request.json["urls"].split("\n")
    resultados = []

    for url in urls:
        url = url.strip()
        if not url:
            continue

        data = verificar(url)

        if data:
            resultados.append(data)

        time.sleep(1.5)

    return jsonify(resultados)

# ===== EXPORT =====
@app.route("/export", methods=["POST"])
def export():
    data = request.json

    with open("hits.txt","w",encoding="utf-8") as f:
        for c in data:
            f.write(f"""╭───✦ HIT HUNTER
├● 👑 ᴜꜱᴇʀ : {c['user']}
├● 🔐 ᴩᴀꜱꜱ : {c['pass']}
├● ✅ ꜱᴛᴀᴛᴜꜱ : Active
├● 📶 ᴀᴄᴛɪᴠᴇ : {c['active']}
├● 📡 ᴍᴀx : {c['max']}
├● ⏰ ᴄʀᴇᴀᴛᴇᴅ : {c['created']}
├● 📅 ᴇxᴘɪʀᴀᴛɪᴏɴ : {c['exp']}
├● 🌐 ꜱᴇʀᴠᴇʀ : {c['server']}
├● 🌍 ᴘᴀɪꜱ : {c['pais']}
├● 📡 ɪꜱᴘ : {c['isp']}
├● ⚡ ʟᴀᴛᴇɴᴄʏ : {c['latency']} ms
├● 🕰️ ᴛɪᴍᴇᴢᴏɴᴇ : {c['timezone']}
├● 📺 ᴄᴀɴᴀʟᴇꜱ : {c['canales']}
├● 👤 нιт вʏ : PANEL PRO
╰───✦ 🚀

🌐 ᴍ3ᴜ : {c['m3u']}


""")

    return send_file("hits.txt", as_attachment=True)

if __name__ == "__main__":
    app.run()
