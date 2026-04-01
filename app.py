from flask import Flask, render_template, request, redirect, session
import csv
import os
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = "123456"

# =========================
# SAFE GET
# =========================
def safe_get(value):
    return (value or "").strip()

# =========================
# KIỂM TRA ROLE (FIX)
# =========================
def require_role(roles):
    def wrapper(func):
        @wraps(func)
        def decorated(*args, **kwargs):
            if "username" not in session:
                return redirect("/login")

            if session.get("role") not in roles:
                return "❌ Bạn không có quyền truy cập"

            return func(*args, **kwargs)
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
            users[safe_get(row.get("username"))] = row

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
            asset_id = safe_get(row.get("ID_assets"))

            if asset_id:
                try:
                    int(row.get("ATS", 100))
                except:
                    row["ATS"] = "100"

                assets[asset_id] = row

    return assets

# =========================
# UPDATE ATS (FIX)
# =========================
def update_ats(asset_id, minus):

    if not os.path.exists("aims.csv"):
        return

    rows = []

    with open("aims.csv", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        for row in reader:
            if safe_get(row.get("ID_assets")) == safe_get(asset_id):

                try:
                    ats = int(row.get("ATS", 100))
                except:
                    ats = 100

                ats = max(0, ats - minus)
                row["ATS"] = str(ats)

            rows.append(row)

    if not rows:
        return

    with open("aims.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

# =========================
# SAVE ALERT
# =========================
def save_alert(user, asset_id, expected_room, scanned_room, alert_type, description=""):

    file_exists = os.path.exists("alerts.csv")

    with open("alerts.csv", "a", newline="", encoding="utf-8-sig") as f:
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
# LOGIN
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":

        username = safe_get(request.form.get("username"))
        password = safe_get(request.form.get("password"))

        users = load_users()
        user = users.get(username)

        if user and user.get("password") == password:
            session["username"] = username
            session["role"] = user.get("role")
            return redirect("/")

        return render_template("login.html", error="Sai tài khoản hoặc mật khẩu")

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
@require_role(["admin","manager","user"])
def home():
    return render_template("index.html")

# =========================
# SCAN
# =========================
@app.route("/scan")
@require_role(["admin","manager","user"])
def scan_qr():
    return render_template("scan.html")

# =========================
# ASSETS LIST
# =========================
@app.route("/assets")
@require_role(["admin","manager"])
def assets():
    assets = load_assets()
    room = safe_get(request.args.get("room")).lower()
    asset_type = safe_get(request.args.get("type")).lower()

    result = {}

    for id, asset in assets.items():
        if room and room not in safe_get(asset.get("Room")).lower():
            continue

        if asset_type and asset_type not in safe_get(asset.get("Type_asset")).lower():
            continue

        result[id] = asset

    return render_template("assets.html", assets=result)

# =========================
# ASSET DETAIL (FIX)
# =========================
@app.route("/asset/<asset_id>")
@require_role(["admin","manager","user"])
def asset_detail(asset_id):

    assets = load_assets()
    asset = assets.get(asset_id)

    if not asset:
        return "Không tìm thấy tài sản"

    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        file_exists = os.path.exists("scan_history.csv")

        with open("scan_history.csv", "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)

            if not file_exists:
                writer.writerow(["user","asset_id","room","type","time"])

            writer.writerow([
                session.get("username"),
                asset_id,
                asset.get("Room"),
                asset.get("Type_asset"),
                now
            ])
    except Exception as e:
        print("Lỗi history:", e)

    scanned_room = request.args.get("scan_room")

    if scanned_room and scanned_room != asset.get("Room"):
        save_alert(session.get("username"), asset_id,
                   asset.get("Room"), scanned_room, "wrong_room")
        update_ats(asset_id, 15)

    return render_template("asset.html", asset=asset)

# =========================
# UPDATE LOCATION (FIX)
# =========================
@app.route("/update-location", methods=["POST"])
@require_role(["admin","manager"])
def update_location():

    asset_id = safe_get(request.form.get("asset_id"))
    auditorium = safe_get(request.form.get("auditorium"))
    room = safe_get(request.form.get("room"))

    if not os.path.exists("aims.csv"):
        return "Không có dữ liệu"

    rows = []

    with open("aims.csv", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        for row in reader:
            if safe_get(row.get("ID_assets")) == asset_id:
                old_room = row.get("Room")

                row["Auditorium"] = auditorium
                row["Room"] = room

                save_location_history(asset_id, old_room, room)

            rows.append(row)

    if rows:
        with open("aims.csv", "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

    return redirect("/asset/" + asset_id)

# =========================
# SAVE LOCATION HISTORY
# =========================
def save_location_history(asset_id, old_room, new_room):

    file_exists = os.path.exists("location_history.csv")

    with open("location_history.csv", "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow(["asset_id","old_room","new_room","time"])

        writer.writerow([
            asset_id, old_room, new_room,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ])

# =========================
# RUN
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
