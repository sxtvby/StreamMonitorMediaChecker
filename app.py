from flask import Flask, render_template, request, jsonify, redirect, session, send_file
import requests
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

# ===== LOGOUT =====
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

# ===== VERIFICACIÓN PRO =====
def verificar(url):
    try:
        # ===== IPTV USER/PASS =====
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
                return {
                    "estado": "OK",
                    "exp": format_fecha(info.get("exp_date")),
                    "canales": 0
                }
            else:
                return {"estado": "INVALID", "exp": "N/A", "canales": 0}

        # ===== LISTA PUBLICA =====
        else:
            r = requests.get(url, timeout=10)

            if r.status_code == 200 and "#EXTM3U" in r.text:
                canales = r.text.count("#EXTINF")
                return {
                    "estado": "OK",
                    "exp": "N/A",
                    "canales": canales
                }

            return {"estado": "INVALID", "exp": "N/A", "canales": 0}

    except:
        return {"estado": "ERROR", "exp": "N/A", "canales": 0}

# ===== HOME =====
@app.route("/")
def home():
    if not auth():
        return redirect("/login")

    db = get_db()
    listas = db.execute("SELECT * FROM listas").fetchall()

    total = len(listas)
    ok = len([l for l in listas if l[2] == "OK"])
    bad = len([l for l in listas if l[2] == "INVALID"])

    return render_template("index.html", listas=listas, total=total, ok=ok, bad=bad)

# ===== AÑADIR =====
@app.route("/add", methods=["POST"])
def add():
    if not auth():
        return jsonify({"error":"login"})

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
    if not auth():
        return jsonify({"error":"login"})

    db = get_db()
    listas = db.execute("SELECT * FROM listas").fetchall()

    for l in listas:
        resultado = verificar(l[1])

        db.execute("""
        UPDATE listas 
        SET estado=?, exp=?, canales=?, ultima_revision=? 
        WHERE id=?
        """,
        (
            resultado["estado"],
            resultado["exp"],
            resultado["canales"],
            datetime.now().strftime("%d/%m/%Y %H:%M"),
            l[0]
        ))

    db.commit()
    return jsonify({"ok":True})

# ===== EXPORT =====
@app.route("/export")
def export():
    db = get_db()
    listas = db.execute("SELECT * FROM listas WHERE estado='OK'").fetchall()

    with open("validas.txt","w",encoding="utf-8") as f:
        for l in listas:
            f.write(f"""URL: {l[1]}
EXP: {l[3]}
CANALES: {l[4]}

""")

    return send_file("validas.txt", as_attachment=True)

# ===== RUN =====
if __name__ == "__main__":
    app.run()
