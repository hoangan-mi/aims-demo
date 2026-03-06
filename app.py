from flask import Flask, render_template, request, redirect, url_for, session
import csv
import os

app = Flask(__name__)
app.secret_key = "123456"


# =========================
# Load tài khoản
# =========================
def load_users():

    users = {}

    if not os.path.exists("users.csv"):
        print("⚠ Không tìm thấy users.csv")
        return users

    with open("users.csv", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        for row in reader:
            username = row.get("username")
            if username:
                users[username] = row

    return users


# =========================
# Load dữ liệu tài sản
# =========================
def load_data():

    data = {}

    if not os.path.exists("aims.csv"):
        print("⚠ Không tìm thấy aims.csv")
        return data

    with open("aims.csv", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")

        for row in reader:
            asset_id = row.get("ID_assets")

            if asset_id:
                asset_id = asset_id.strip()
                data[asset_id] = row

    print(f"✔ Đã load {len(data)} tài sản")

    return data


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

        if user and user.get("password") == password:

            session["username"] = username
            session["role"] = user.get("role", "user")

            return redirect(url_for("home"))

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
# Trang chủ
# =========================
@app.route("/")
def home():

    if "username" not in session:
        return redirect("/login")

    return render_template("index.html", role=session.get("role"))


# =========================
# Trang scan QR
# =========================
@app.route("/scan")
def scan_qr():

    if "username" not in session:
        return redirect("/login")

    return render_template("scan.html")


# =========================
# Trang danh sách tài sản
# =========================
@app.route("/assets")
def show_assets():

    if "username" not in session:
        return redirect("/login")

    if session.get("role") == "user":
        return """
        <h2 style='text-align:center;margin-top:50px;color:red'>
        ❌ Bạn không có quyền xem danh sách tài sản
        </h2>
        """

    assets_data = load_data()

    return render_template("assets.html", assets=assets_data)


# =========================
# Trang chi tiết tài sản
# =========================
@app.route("/asset/<asset_id>")
def asset_detail(asset_id):

    if "username" not in session:
        return redirect("/login")

    assets_data = load_data()

    asset_id = asset_id.strip()

    asset = assets_data.get(asset_id)

    if not asset:

        return f"""
        <h2 style='color:red;text-align:center;margin-top:50px;'>
        ❌ Không tìm thấy tài sản: {asset_id}
        </h2>

        <div style='text-align:center;'>
        <a href='/scan'>Quét lại QR</a>
        </div>
        """

    return render_template("asset.html", asset=asset)

# =========================
# API lấy thông tin tài sản (dùng cho scan QR realtime)
# =========================
@app.route("/api/asset/<asset_id>")
def api_asset(asset_id):

    if "username" not in session:
        return {"status": "error", "message": "not login"}

    assets_data = load_data()

    asset_id = asset_id.strip()

    asset = assets_data.get(asset_id)

    if not asset:
        return {"status": "error", "message": "not found"}

    return {
        "status": "ok",
        "data": asset
    }
# =========================
# Trang báo cáo hư hỏng
# =========================
@app.route("/report/<asset_id>", methods=["GET", "POST"])
def report_damage(asset_id):

    if "username" not in session:
        return redirect("/login")

    assets_data = load_data()

    asset_id = asset_id.strip()

    asset = assets_data.get(asset_id)

    if not asset:
        return redirect(url_for("scan_qr"))

    if request.method == "POST":

        description = request.form.get("description", "").strip()

        file_exists = os.path.exists("damage_reports.csv")

        with open("damage_reports.csv", "a", newline="", encoding="utf-8") as f:

            writer = csv.writer(f)

            if not file_exists:
                writer.writerow([
                    "ID_assets",
                    "Type_asset",
                    "Auditorium",
                    "Floor",
                    "Room",
                    "Description"
                ])

            writer.writerow([
                asset.get("ID_assets", ""),
                asset.get("Type_asset", ""),
                asset.get("Auditorium", ""),
                asset.get("Floor", ""),
                asset.get("Room", ""),
                description
            ])

        return render_template("report_success.html", asset=asset)

    return render_template("report_form.html", asset=asset)


# =========================
# Run app
# =========================
if __name__ == "__main__":

    port = int(os.environ.get("PORT", 5000))

    app.run(host="0.0.0.0", port=port, debug=True)

