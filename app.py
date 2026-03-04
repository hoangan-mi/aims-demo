from flask import Flask, render_template, request
import csv
import os

app = Flask(__name__)

# Load dữ liệu từ CSV
def load_data():
    data = {}
    with open("aims.csv", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        for row in reader:
            data[row["ID_assets"]] = row
    return data

assets_data = load_data()

# =========================
# Trang chủ
# =========================
@app.route("/")
def home():
    return render_template("index.html")


# =========================
# Trang chi tiết tài sản
# =========================
@app.route("/asset/<asset_id>")
def asset_detail(asset_id):
    asset = assets_data.get(asset_id)
    return render_template("asset.html", asset=asset)

# =========================
# Trang báo cáo hư hỏng
# =========================
@app.route("/report/<asset_id>", methods=["GET", "POST"])
def report_damage(asset_id):
    asset = assets_data.get(asset_id)

    # Nếu không tìm thấy tài sản
    if not asset:
        return render_template("asset.html", asset=None)

    if request.method == "POST":
        description = request.form.get("description")

        # Lưu vào file CSV
        with open("damage_reports.csv", "a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow([
                asset["ID_assets"],
                asset["Type_asset"],
                asset["Auditorium"],
                asset["Floor"],
                asset["Room"],
                description
            ])

        return render_template("report_success.html", asset=asset)

    return render_template("report_form.html", asset=asset)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)


