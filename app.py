from flask import Flask, render_template, request, jsonify, redirect, session, send_file
import requests
from datetime import datetime
from db import get_db, init_db
from werkzeug.security import generate_password_hash, check_password_hash
import time
import random
import json

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

# ===== VERIFICACIÓN MEJORADA (SOLO TUS URLS) =====
def verificar(url):
    try:
        time.sleep(random.uniform(1, 2))  # comportamiento humano

        if "get.php" in url:
            base = url.split("/get.php")[0]
            user = url.split("username=")[1].split("&")[0]
            password = url.split("password=")[1].split("&")[0]

            api = f"{base}/player_api.php?username={user}&password={password}"

            r = requests.get(api, timeout=10)
            data = r.json()

            info = data.get("user_info", {})
            server = data.get("server_info", {})

            if info.get("auth") == 1:

                resultado = {
                    "user": user,
                    "pass": password,
                    "active": info.get("active_cons", 0),
                    "max": info.get("max_connections", 0),
                    "created": format_fecha(info.get("created_at")),
                    "exp": format_fecha(info.get("exp_date")),
                    "server": base,
                    "timezone": server.get("timezone", "N/A"),
                    "canales": 0,
                    "status": "OK"
                }

                return resultado

            else:
                return {"status": "INVALID"}

        else:
            r = requests.get(url, timeout=10)

            if "#EXTM3U" in r.text:
                canales = r.text.count("#EXTINF")
                return {
                    "user": "N/A",
                    "pass": "N/A",
                    "active": "-",
                    "max": "-",
                    "created": "-",
                    "exp": "-",
                    "server": url,
                    "timezone": "-",
                    "canales": canales,
                    "status": "OK"
                }

        return {"status": "INVALID"}

    except:
        return {"status": "ERROR"}

# ===== HOME =====
@app.route("/")
def home():
    if not auth():
        return redirect("/login")

    db = get_db()
    listas = db.execute("SELECT * FROM listas").fetchall()

    return render_template("index.html", listas=listas)

# ===== AÑADIR =====
@app.route("/add", methods=["POST"])
def add():
    urls = request.json["urls"].split("\n")
    db = get_db()

    for url in urls:
        url = url.strip()
        if url:
            try:
                db.execute("INSERT INTO listas (url,estado) VALUES (?,?)",(url,"NEW"))
            except:
                pass

    db.commit()
    return jsonify({"ok":True})

# ===== SCAN =====
@app.route("/scan")
def scan():
    db = get_db()
    listas = db.execute("SELECT * FROM listas").fetchall()

    for l in listas:
        resultado = verificar(l[1])

        db.execute("""
        UPDATE listas 
        SET estado=?, data=?, ultima_revision=? 
        WHERE id=?
        """,
        (
            resultado.get("status"),
            json.dumps(resultado),
            datetime.now().strftime("%d/%m/%Y %H:%M"),
            l[0]
        ))

    db.commit()
    return jsonify({"ok":True})

# ===== EXPORT FORMATO PRO =====
@app.route("/export")
def export():
    db = get_db()
    listas = db.execute("SELECT data FROM listas WHERE estado='OK'").fetchall()

    with open("validas.txt","w",encoding="utf-8") as f:
        for l in listas:
            c = json.loads(l[0])

            f.write(f"""╭───✦ HIT HUNTER
├● 👑 ᴜꜱᴇʀ : {c['user']}
├● 🔐 ᴩᴀꜱꜱ : {c['pass']}
├● ✅ ꜱᴛᴀᴛᴜꜱ : Active
├● 📶 ᴀᴄᴛɪᴠᴇ : {c['active']}
├● 📡 ᴍᴀx : {c['max']}
├● ⏰ ᴄʀᴇᴀᴛᴇᴅ : {c['created']}
├● 📅 ᴇxᴘɪʀᴀᴛɪᴏɴ : {c['exp']}
├● 🌐 ꜱᴇʀᴠᴇʀ : {c['server']}
├● 🕰️ ᴛɪᴍᴇᴢᴏɴᴇ : {c['timezone']}
├● 📺 ᴄᴀɴᴀʟᴇꜱ : {c['canales']}
├● 👤 нιт вʏ : PANEL PRO
╰───✦ 🚀

🌐 ᴍ3ᴜ : {c['server']}/get.php?username={c['user']}&password={c['pass']}&type=m3u_plus

""")

    return send_file("validas.txt", as_attachment=True)

# ===== RUN =====
if __name__ == "__main__":
    app.run()
