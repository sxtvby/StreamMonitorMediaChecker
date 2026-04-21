from flask import Flask, render_template, request, jsonify, send_file
import requests, time
from db import get_db, init_db

app = Flask(__name__)
init_db()

# ===== FORMATO FINAL =====
def format_output(c):
    return f"""├● 👑 ᴜꜱᴇʀ : {c['user']}
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

# ===== VERIFICACIÓN ESTABLE =====
def verificar(url):
    try:
        if "username=" not in url:
            return None

        base = url.split("/get.php")[0]
        user = url.split("username=")[1].split("&")[0]
        password = url.split("password=")[1].split("&")[0]

        api = f"{base}/player_api.php?username={user}&password={password}"

        t1 = time.time()
        r = requests.get(api, timeout=8)

        latency = int((time.time() - t1) * 1000)

        if r.status_code != 200:
            return None

        try:
            data = r.json()
        except:
            return None

        info = data.get("user_info", {})
        server = data.get("server_info", {})

        if info.get("auth") != 1:
            return None

        # ===== CANALES =====
        canales = 0
        try:
            m3u = requests.get(url, timeout=8).text
            canales = m3u.count("#EXTINF")
        except:
            canales = 0

        return {
            "user": user,
            "pass": password,
            "active": info.get("active_cons", "N/A"),
            "max": info.get("max_connections", "N/A"),
            "created": info.get("created_at", "N/A"),
            "exp": info.get("exp_date", "N/A"),
            "server": base,
            "pais": server.get("country", "N/A"),
            "isp": server.get("url", "N/A"),
            "timezone": server.get("timezone", "N/A"),
            "latency": latency,
            "canales": canales,
            "url": url
        }

    except:
        return None

# ===== HOME =====
@app.route("/")
def home():
    return render_template("index.html")

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

# ===== SCAN =====
@app.route("/scan")
def scan():
    db = get_db()
    listas = db.execute("SELECT * FROM listas").fetchall()

    for l in listas:
        db.execute("UPDATE listas SET estado='RUN' WHERE id=?", (l[0],))
        db.commit()

        result = verificar(l[1])

        if result:
            texto = format_output(result)
            db.execute("UPDATE listas SET estado='OK', resultado=? WHERE id=?",
                       (texto, l[0]))
        else:
            db.execute("UPDATE listas SET estado='BAD', resultado='❌ INVALID' WHERE id=?",
                       (l[0],))

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

# ===== EXPORT =====
@app.route("/export")
def export():
    db = get_db()
    listas = db.execute("SELECT * FROM listas WHERE estado='OK'").fetchall()

    with open("validas.txt","w",encoding="utf-8") as f:
        for l in listas:
            f.write(l[3] + "\n\n")

    return send_file("validas.txt", as_attachment=True)

if __name__ == "__main__":
    app.run()
