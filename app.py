from flask import Flask, render_template, request, redirect, url_for
import csv
import os

app = Flask(__name__)

# =========================
# Load dữ liệu từ CSV
# =========================
def load_data():
    data = {}

    if not os.path.exists("aims.csv"):
        print("⚠ Không tìm thấy aims.csv")
        return data

    with open("aims.csv", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        for row in reader:
            # Chuẩn hóa ID (rất quan trọng)
            asset_id = row["ID_assets"].strip()
            data[asset_id] = row

    print(f"✔ Đã load {len(data)} tài sản")
    return data


# =========================
# Trang chủ
# =========================
@app.route("/")
def home():
    return render_template("index.html")


# =========================
# Trang scan QR
# =========================
@app.route("/scan")
def scan_qr():
    return render_template("scan.html")


# =========================
# Trang danh sách tất cả tài sản
# =========================
@app.route("/assets")
def show_assets():
    assets_data = load_data()   # reload mỗi lần mở
    return render_template("assets.html", assets=assets_data)


# =========================
# Trang chi tiết tài sản
# =========================
@app.route("/asset/<asset_id>")
def asset_detail(asset_id):

    assets_data = load_data()   # reload dữ liệu mới nhất

    asset_id = asset_id.strip()  # loại bỏ khoảng trắng
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
# Trang báo cáo hư hỏng
# =========================
@app.route("/report/<asset_id>", methods=["GET", "POST"])
def report_damage(asset_id):

    assets_data = load_data()
    asset_id = asset_id.strip()
    asset = assets_data.get(asset_id)

    if not asset:
        return redirect(url_for("scan_qr"))

    if request.method == "POST":

        description = request.form.get("description", "").strip()

        with open("damage_reports.csv", "a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)

            writer.writerow([
                asset["ID_assets"],
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
