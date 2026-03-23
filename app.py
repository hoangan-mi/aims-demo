from flask import Flask, render_template, request, redirect, session
import csv
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "123456"

# =========================
# ROLE CHECK
# =========================
def require_role(roles):
    def wrapper(func):
        def decorated(*args, **kwargs):
            if "username" not in session:
                return redirect("/login")

            if session.get("role") not in roles:
                return "❌ Bạn không có quyền truy cập"

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
                if "ATS" not in row or row["ATS"] == "":
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
                "user","asset_id","expected_room","scanned_room",
                "type_alert","description","time"
            ])

        writer.writerow([
            user, asset_id, expected_room, scanned_room,
            alert_type, description,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ])


# =========================
# LOGIN / LOGOUT
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

        return render_template("login.html", error="Sai tài khoản hoặc mật khẩu")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# =========================
# HOME
# =========================
@app.route("/")
@require_role(["admin","manager","user"])
def home():
    return render_template("index.html")


# =========================
# SCAN PAGE
# =========================
@app.route("/scan")
@require_role(["admin","manager","user"])
def scan_qr():
    return render_template("scan.html")


# =========================
# 🔥 SCAN ROOM
# =========================
@app.route("/scan-room/<room_id>")
@require_role(["admin","manager"])
def scan_room(room_id):

    session["current_room"] = room_id
    session["scan_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return f"✅ Đã quét phòng {room_id} (hiệu lực 60 phút)"


# =========================
# 🔥 END SCAN ROOM
# =========================
@app.route("/end-scan-room")
@require_role(["admin","manager"])
def end_scan_room():
    session.pop("current_room", None)
    session.pop("scan_time", None)
    return redirect("/")


# =========================
# ASSETS LIST
# =========================
@app.route("/assets")
@require_role(["admin","manager"])
def assets():

    assets = load_assets()

    room = request.args.get("room")
    asset_type = request.args.get("type")

    result = {}

    for id, asset in assets.items():

        if room and room.lower() not in asset.get("Room", "").lower():
            continue

        if asset_type and asset_type.lower() not in asset.get("Type_asset", "").lower():
            continue

        result[id] = asset

    return render_template("assets.html", assets=result)


# =========================
# 🔥 ASSET DETAIL (CORE)
# =========================
@app.route("/asset/<asset_id>")
@require_role(["admin","manager","user"])
def asset_detail(asset_id):

    assets = load_assets()
    asset = assets.get(asset_id)

    if not asset:
        return "Không tìm thấy tài sản"

    room = asset.get("Room", "").strip()

    # ===== ADMIN / MANAGER =====
    if session.get("role") in ["admin","manager"]:

        current_room = session.get("current_room")
        scan_time = session.get("scan_time")

        # chưa quét phòng
        if not current_room:
            return "❌ Chưa quét QR phòng!"

        # timeout 60 phút
        if scan_time:
            scan_time_dt = datetime.strptime(scan_time, "%Y-%m-%d %H:%M:%S")
            if datetime.now() - scan_time_dt > timedelta(minutes=60):
                session.pop("current_room", None)
                return "⏰ Hết thời gian! Quét lại QR phòng."

        # sai phòng
        if current_room != room:
            save_alert(
                session["username"],
                asset_id,
                room,
                current_room,
                "wrong_room"
            )
            update_ats(asset_id, 15)

    # ===== SAVE HISTORY =====
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    file_exists = os.path.exists("scan_history.csv")

    with open("scan_history.csv", "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow(["user","asset_id","room","time"])

        writer.writerow([
            session["username"],
            asset_id,
            room,
            now
        ])

    return render_template("asset.html", asset=asset)


# =========================
# REPORT DAMAGE
# =========================
@app.route("/report/<asset_id>", methods=["GET","POST"])
@require_role(["admin","manager","user"])
def report(asset_id):

    assets = load_assets()
    asset = assets.get(asset_id)

    if not asset:
        return redirect("/scan")

    if request.method == "POST":

        description = request.form.get("description")

        save_alert(
            session["username"],
            asset_id,
            asset.get("Room"),
            asset.get("Room"),
            "damage",
            description
        )

        update_ats(asset_id, 25)

        return render_template("report_success.html", asset=asset)

    return render_template("report_form.html", asset=asset)


# =========================
# HISTORY
# =========================
@app.route("/history")
@require_role(["admin","manager"])
def history():

    history = []

    if os.path.exists("scan_history.csv"):
        with open("scan_history.csv", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                history.append(row)

    return render_template("history.html", history=history)


# =========================
# ABNORMAL
# =========================
@app.route("/abnormal")
@require_role(["admin"])
def abnormal():

    abnormal_assets = []

    if os.path.exists("alerts.csv"):
        with open("alerts.csv", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                abnormal_assets.append(row)

    return render_template("abnormal.html", abnormal_assets=abnormal_assets)


# =========================
# RUN
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
