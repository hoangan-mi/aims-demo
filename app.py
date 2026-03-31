from flask import Flask, render_template, request, redirect, session, jsonify
import csv
import os
import time
from datetime import datetime

app = Flask(__name__)
app.secret_key = "123456"


# =========================
# CHECK ROLE
# =========================
def require_role(roles):
    def wrapper(func):
        def decorated(*args, **kwargs):

            if "username" not in session:
                return redirect("/login")

            if session.get("role") not in roles:
                return "❌ Không có quyền"

            return func(*args, **kwargs)

        decorated.__name__ = func.__name__
        return decorated
    return wrapper


# =========================
# LOAD USERS
# =========================
def load_users():
    users = {}

    if not os.path.exists("users.csv"):
        return users

    with open("users.csv", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            users[row["username"].strip()] = row

    return users


# =========================
# LOAD ASSETS
# =========================
def load_assets():
    assets = {}

    if not os.path.exists("aims.csv"):
        return assets

    with open("aims.csv", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        for row in reader:
            asset_id = row.get("ID_assets", "").strip()

            if asset_id:
                if not row.get("ATS"):
                    row["ATS"] = "100"

                assets[asset_id] = row

    return assets


# =========================
# UPDATE ATS
# =========================
def update_ats(asset_id, minus):
    rows = []

    with open("aims.csv", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        for row in reader:
            if row.get("ID_assets", "").strip() == asset_id.strip():
                ats = int(row.get("ATS", 100))
                ats = max(0, ats - minus)
                row["ATS"] = str(ats)

            rows.append(row)

    if not rows:
        return

    with open("aims.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


# =========================
# SAVE ALERT
# =========================
def save_alert(user, asset_id, expected_room, scanned_room, alert_type, description=""):
    file_exists = os.path.exists("alerts.csv")

    with open("alerts.csv", "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow([
                "user", "asset_id", "expected_room",
                "scanned_room", "type", "description", "time"
            ])

        writer.writerow([
            user, asset_id, expected_room,
            scanned_room, alert_type, description,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ])


# =========================
# LOGIN
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        users = load_users()
        user = users.get(username)

        if user and user["password"] == password:
            session["username"] = username
            session["role"] = user.get("role")

            return redirect("/")

        return render_template("login.html", error="Sai tài khoản")

    return render_template("login.html")


# =========================
# LOGOUT
# =========================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# =========================
# HOME
# =========================
@app.route("/")
@require_role(["admin", "manager", "user"])
def home():

    # auto reset phòng sau 30p
    if "room_time" in session:
        if time.time() - session["room_time"] > 1800:
            session.pop("current_room", None)
            session.pop("room_time", None)

    return render_template("index.html")


# =========================
# SCAN PAGE
# =========================
@app.route("/scan")
@require_role(["admin", "manager", "user"])
def scan():
    return render_template("scan.html")


# =========================
# SCAN ROOM
# =========================
@app.route("/scan-room/<room>")
def scan_room(room):
    session["current_room"] = room
    session["room_time"] = time.time()
    return jsonify({"status": "ok"})


# =========================
# API SCAN ASSET
# =========================
@app.route("/api/asset/<asset_id>")
def api_asset(asset_id):

    if "username" not in session:
        return {"status": "error"}

    assets = load_assets()
    asset = assets.get(asset_id.strip())

    if not asset:
        return {"status": "error", "message": "not found"}

    # log scan
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    file_exists = os.path.exists("scan_history.csv")

    with open("scan_history.csv", "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow(["user", "asset_id", "room", "time"])

        writer.writerow([
            session["username"],
            asset_id,
            asset.get("Room"),
            now
        ])

    # check sai phòng
    scanned_room = session.get("current_room")
    wrong = False

    if scanned_room and scanned_room != asset.get("Room"):
        wrong = True

        save_alert(
            session["username"],
            asset_id,
            asset.get("Room"),
            scanned_room,
            "wrong_room"
        )

        update_ats(asset_id, 15)

    return {
        "status": "ok",
        "data": asset,
        "wrong_room": wrong
    }


# =========================
# ASSETS LIST
# =========================
@app.route("/assets")
@require_role(["admin", "manager"])
def assets():

    assets = load_assets()
    result = {}

    room = request.args.get("room")
    t = request.args.get("type")

    for id, a in assets.items():

        if room and room.lower() not in a.get("Room", "").lower():
            continue

        if t and t.lower() not in a.get("Type_asset", "").lower():
            continue

        result[id] = a

    return render_template("assets.html", assets=result)


# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(debug=True)
