from flask import Flask, render_template
import csv

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

# Trang chủ
@app.route("/")
def home():
    return """
    <h1>Demo hệ thống AIMS</h1>
    <p>Hệ thống đang hoạt động.</p>
    """

# Trang hiển thị tài sản khi quét QR
@app.route("/asset/<asset_id>")
def asset_detail(asset_id):
    asset = assets_data.get(asset_id)

    if not asset:
        return render_template("not_found.html"), 404

    return render_template("asset.html", asset=asset)


import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
