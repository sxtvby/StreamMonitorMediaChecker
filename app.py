from flask import Flask, render_template, request, jsonify, redirect, session
import requests, time
from db import get_db, init_db

app = Flask(__name__)
app.secret_key = "secret123"

init_db()

# ===== CREAR USER =====
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

# ===== FORMATO SIMPLE =====
def format_ok(user, password, base, exp):
    return f"""╭───✦ HIT HUNTER
├● 👑 ᴜꜱᴇʀ : {user}
├● 🔐 ᴩᴀꜱꜱ : {password}
├● ✅ ꜱᴛᴀᴛᴜꜱ : Active
├● 📅 ᴇxᴘɪʀᴀᴛɪᴏɴ : {exp}
├● 🌐 ꜱᴇʀᴠᴇʀ : {base}
├● ⚡ ꜱᴄᴀɴᴛʏᴩᴇ : panel
├● 👤 нιт вʏ : PANEL PRO
╰───✦ 🚀

🌐 ᴍ3ᴜ : {base}/get.php?username={user}&password={password}&type=m3u
"""

# ===== VERIFICAR =====
def verificar(url):
    try:
        if "username=" not in url:
            return ("ERROR","❌ URL inválida")

        base = url.split("/get.php")[0]
        user = url.split("username=")[1].split("&")[0]
        password = url.split("password=")[1].split("&")[0]

        api = f"{base}/player_api.php?username={user}&password={password}"

        r = requests.get(api, timeout=8)

        if r.status_code != 200:
            return ("ERROR","❌ Sin respuesta")

        data = r.json()
        info = data.get("user_info", {})

        if info.get("auth") != 1:
            return ("BAD","❌ Cuenta inválida")

        exp = info.get("exp_date","N/A")

        return ("OK", format_ok(user,password,base,exp))

    except:
        return ("ERROR","❌ Error de conexión")

# ===== HOME =====
@app.route("/")
def home():
    if not auth():
        return redirect("/login")
    return render_template("index.html")

# ===== ADD =====
@app.route("/add", methods=["POST"])
def add():
    urls = request.json["urls"].split("\n")
    db = get_db()

    for url in urls:
        url = url.strip()
        if url:
            db.execute("INSERT INTO listas (url,estado) VALUES (?,?)",(url,"NEW"))

    db.commit()
    return jsonify({"ok":True})

# ===== VERIFICAR =====
@app.route("/verificar")
def scan():
    db = get_db()
    listas = db.execute("SELECT * FROM listas").fetchall()

    for l in listas:
        db.execute("UPDATE listas SET estado='RUN' WHERE id=?", (l[0],))
        db.commit()

        estado, resultado = verificar(l[1])

        db.execute("UPDATE listas SET estado=?, resultado=? WHERE id=?",
                   (estado, resultado, l[0]))
        db.commit()

        time.sleep(1)

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

if __name__ == "__main__":
    app.run()
