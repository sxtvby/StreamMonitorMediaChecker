from flask import Flask, render_template, request, jsonify, redirect, session, send_file
import requests, time
from db import get_db, init_db
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "secret123"

init_db()

# ===== ADMIN =====
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

def auth():
    return "user" in session

# ===== FORMATO =====
def format_output(c):
    return f"""╭───✦ HIT HUNTER
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

🌐 ᴍ3ᴜ : {c['url']}
"""

# ===== VERIFICACIÓN SEGURA =====
def verificar(url):
    try:
        if "username=" not in url:
            return None

        base = url.split("/get.php")[0]
        user = url.split("username=")[1].split("&")[0]
        password = url.split("password=")[1].split("&")[0]

        api = f"{base}/player_api.php?username={user}&password={password}"

        t1 = time.time()
        r = requests.get(api, timeout=6)

        if r.status_code != 200:
            return None

        try:
            data = r.json()
        except:
            return None

        latency = int((time.time() - t1)*1000)

        info = data.get("user_info", {})
        server = data.get("server_info", {})

        if info.get("auth") != 1:
            return None

        # ===== CONTAR CANALES =====
        canales = 0
        try:
            m3u = requests.get(url, timeout=6).text
            canales = m3u.count("#EXTINF")
        except:
            pass

        return {
            "user": user,
            "pass": password,
            "active": info.get("active_cons", 0),
            "max": info.get("max_connections", 0),
            "created": info.get("created_at","N/A"),
            "exp": info.get("exp_date","N/A"),
            "server": base,
            "timezone": server.get("timezone","N/A"),
            "pais": server.get("country","N/A"),
            "isp": server.get("url","N/A"),
            "latency": latency,
            "canales": canales,
            "url": url
        }

    except:
        return None

# ===== HOME =====
@app.route("/")
def home():
    if not auth():
        return redirect("/login")

    db = get_db()
    listas = db.execute("SELECT * FROM listas").fetchall()
    return render_template("index.html", listas=listas)

# ===== ADD =====
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

# ===== SCAN NO BLOQUEANTE =====
@app.route("/scan")
def scan():
    db = get_db()
    listas = db.execute("SELECT * FROM listas").fetchall()

    for l in listas:
        try:
            result = verificar(l[1])

            if result:
                texto = format_output(result)
                db.execute("UPDATE listas SET estado=?, resultado=? WHERE id=?",
                           ("OK", texto, l[0]))
            else:
                db.execute("UPDATE listas SET estado=?, resultado=? WHERE id=?",
                           ("INVALID", "❌ No válida", l[0]))

            db.commit()
            time.sleep(1)  # 🔥 evita bloqueo

        except Exception as e:
            db.execute("UPDATE listas SET estado=?, resultado=? WHERE id=?",
                       ("ERROR", str(e), l[0]))
            db.commit()

    return jsonify({"ok":True})

# ===== EXPORT =====
@app.route("/export")
def export():
    db = get_db()
    listas = db.execute("SELECT resultado FROM listas WHERE estado='OK'").fetchall()

    with open("hits.txt","w",encoding="utf-8") as f:
        for l in listas:
            f.write(l[0] + "\n\n")

    return send_file("hits.txt", as_attachment=True)

if __name__ == "__main__":
    app.run()
