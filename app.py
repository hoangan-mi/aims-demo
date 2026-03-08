from flask import Flask, render_template, request, redirect, session, jsonify
import csv
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "aims_secret"

ASSET_FILE = "assets.csv"
HISTORY_FILE = "location_history.csv"


# ===============================
# LOAD ASSETS
# ===============================

def load_assets():

    assets = {}

    if not os.path.exists(ASSET_FILE):
        return assets

    with open(ASSET_FILE, newline='', encoding="utf-8") as f:

        reader = csv.DictReader(f)

        for row in reader:

            asset_id = row["ID_assets"].strip()

            assets[asset_id] = row

    return assets


# ===============================
# LOGIN (demo)
# ===============================

@app.route("/login")
def login():

    session["username"] = "demo"

    # role demo: admin / manager / staff
    session["role"] = "admin"

    return redirect("/scan")


# ===============================
# SCAN PAGE
# ===============================

@app.route("/scan")
def scan():

    if "username" not in session:
        return redirect("/login")

    return render_template("scan.html")


# ===============================
# API ASSET
# ===============================

@app.route("/api/asset/<asset_id>")
def api_asset(asset_id):

    if "username" not in session:
        return jsonify({"status":"error","message":"not login"})

    assets = load_assets()

    asset = assets.get(asset_id.strip())

    if not asset:
        return jsonify({"status":"error","message":"not found"})

    return jsonify({
        "status":"ok",
        "data":asset
    })


# ===============================
# UPDATE LOCATION
# ===============================

@app.route("/update_location", methods=["POST"])
def update_location():

    if "username" not in session:
        return redirect("/login")

    role = session.get("role")

    if role not in ["admin","manager"]:
        return "Permission denied"

    asset_id = request.form.get("asset_id")
    building = request.form.get("building")
    floor = request.form.get("floor")
    room = request.form.get("room")

    rows = []

    updated = False

    with open(ASSET_FILE, newline='', encoding="utf-8") as f:

        reader = csv.DictReader(f)

        for row in reader:

            if row["ID_assets"] == asset_id:

                old_building = row["Building"]
                old_floor = row["Floor"]
                old_room = row["Room"]

                row["Building"] = building
                row["Floor"] = floor
                row["Room"] = room

                updated = True

            rows.append(row)

    # SAVE CSV

    if rows:

        fieldnames = rows[0].keys()

        with open(ASSET_FILE, "w", newline='', encoding="utf-8") as f:

            writer = csv.DictWriter(f, fieldnames=fieldnames)

            writer.writeheader()
            writer.writerows(rows)

    # SAVE HISTORY

    if updated:

        write_header = not os.path.exists(HISTORY_FILE)

        with open(HISTORY_FILE, "a", newline='', encoding="utf-8") as f:

            writer = csv.writer(f)

            if write_header:
                writer.writerow([
                    "time",
                    "user",
                    "asset_id",
                    "old_building",
                    "old_floor",
                    "old_room",
                    "new_building",
                    "new_floor",
                    "new_room"
                ])

            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                session["username"],
                asset_id,
                old_building,
                old_floor,
                old_room,
                building,
                floor,
                room
            ])

    return redirect("/scan")


# ===============================

if __name__ == "__main__":
    app.run(debug=True)
