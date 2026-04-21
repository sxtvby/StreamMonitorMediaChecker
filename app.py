from flask import Flask, render_template, request, jsonify, redirect, session, send_file
import requests, time, threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from db import get_db, init_db

app = Flask(__name__)
app.secret_key = "secret123"

init_db()

# ===== USER =====
db = get_db()
try:
    db.execute("INSERT INTO users (user,pass) VALUES (?,?)", ("admin","admin"))
    db.commit()
except:
    pass

# ===== LOGIN =====
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        user = request.form["user"]
        password = request.form["pass"]

        db = get_db()
        u = db.execute("SELECT * FROM users WHERE user=? AND pass=?",(user,password)).fetchone()

        if u:
            session["user"] = user
            return redirect("/")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

def auth():
    return "user" in session

# ===== FECHA =====
def fmt_fecha(ts):
    try:
        return datetime.fromtimestamp(int(ts)).strftime('%d/%m/%Y')
    except:
        return "N/A"

# ===== CANALES =====
def check_canales(url):
    try:
        r = requests.get(url, timeout=5)
        if "#EXTM3U" in r.text:
            return r.text.count("#EXTINF")
    except:
        pass
    return 0

# ===== FORMATO =====
def format_ok(c):
    return f"""╭───✦ HIT HUNTER
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
├● ⚡ ꜱᴄᴀɴᴛʏᴩᴇ : combo scanner
├● 👤 нιт вʏ : PANEL PRO
╰───✦ 🚀

🌐 ᴍ3ᴜ : {c['url']}
"""

# ===== VERIFICAR UNO =====
def verificar_one(row):
    id, url = row[0], row[1]
    db = get_db()

    try:
        base = url.split("/get.php")[0]
        user = url.split("username=")[1].split("&")[0]
        password = url.split("password=")[1].split("&")[0]

        api = f"{base}/player_api.php?username={user}&password={password}"
        r = requests.get(api, timeout=6)

        if r.status_code != 200:
            db.execute("UPDATE listas SET estado='ERROR', resultado='❌ SIN RESPUESTA' WHERE id=?", (id,))
            db.commit()
            return

        data = r.json()
        info = data.get("user_info", {})
        server = data.get("server_info", {})

        if info.get("auth") != 1:
            db.execute("UPDATE listas SET estado='BAD', resultado='❌ INVALIDA' WHERE id=?", (id,))
            db.commit()
            return

        canales = check_canales(url)

        c = {
            "user": user,
            "pass": password,
            "active": info.get("active_cons", "0"),
            "max": info.get("max_connections", "0"),
            "created": fmt_fecha(info.get("created_at")),
            "exp": fmt_fecha(info.get("exp_date")),
            "server": base,
            "timezone": server.get("timezone","N/A"),
            "canales": canales,
            "url": url
        }

        db.execute("UPDATE listas SET estado='OK', resultado=? WHERE id=?",
                   (format_ok(c), id))
        db.commit()

    except:
        db.execute("UPDATE listas SET estado='ERROR', resultado='❌ ERROR' WHERE id=?", (id,))
        db.commit()

# ===== BACKGROUND SCAN =====
def scan_background():
    db = get_db()
    listas = db.execute("SELECT * FROM listas").fetchall()

    with ThreadPoolExecutor(max_workers=3) as executor:
        executor.map(verificar_one, listas)

# ===== START SCAN =====
@app.route("/verificar")
def scan():
    threading.Thread(target=scan_background).start()
    return jsonify({"ok":True})

# ===== RESULTS =====
@app.route("/results")
def results():
    db = get_db()
    listas = db.execute("SELECT * FROM listas").fetchall()

    return jsonify([
        {"estado": l[2], "resultado": l[3]}
        for l in listas
    ])

# ===== ADD =====
@app.route("/add", methods=["POST"])
def add():
    urls = request.json["urls"].split("\n")
    db = get_db()

    for url in urls:
        url = url.strip()
        if url:
            db.execute("INSERT OR IGNORE INTO listas (url,estado) VALUES (?,?)",(url,"NEW"))

    db.commit()
    return jsonify({"ok":True})

# ===== EXPORT =====
@app.route("/export")
def export():
    db = get_db()
    listas = db.execute("SELECT resultado FROM listas WHERE estado='OK'").fetchall()

    with open("validas.txt","w",encoding="utf-8") as f:
        for l in listas:
            f.write(l[0] + "\n\n")

    return send_file("validas.txt", as_attachment=True)

# ===== HOME =====
@app.route("/")
def home():
    if not auth():
        return redirect("/login")
    return render_template("index.html")

if __name__ == "__main__":
    app.run()
