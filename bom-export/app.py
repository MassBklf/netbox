import os
import io
import datetime
import requests
import pandas as pd
from flask import Flask, render_template, request, Response

# ======================
# Konfiguration
# ======================
NETBOX_URL = os.getenv("NETBOX_URL", "")
NETBOX_TOKEN = os.getenv("NETBOX_TOKEN", "")  # leer bei Demo
EXPORT_DIR = "exports"

HEADERS = {}
if NETBOX_TOKEN:
    HEADERS["Authorization"] = f"Token {NETBOX_TOKEN}"

os.makedirs(EXPORT_DIR, exist_ok=True)

app = Flask(__name__)


# ======================
# Hilfsfunktionen
# ======================
def netbox_get(endpoint, params=None):
    url = f"{NETBOX_URL}/api/{endpoint}"
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json()


def get_all_results(endpoint, params=None):
    """Behandelt Pagination von NetBox"""
    results = []
    while True:
        data = netbox_get(endpoint, params)
        results.extend(data["results"])
        if not data["next"]:
            break
        endpoint = data["next"].replace(f"{NETBOX_URL}/api/", "")
        params = None
    return results


# ======================
# Routes
# ======================
@app.route("/bom-export", methods=["GET"])
def index():
    sites = get_all_results("dcim/sites/")
    sites = sorted(sites, key=lambda s: s["name"])
    return render_template("index.html", sites=sites)


@app.route("/bom-export/export", methods=["POST"])
def export():
    site_slug = request.form.get("site_slug")
    site_name = request.form.get("site_name")

    devices = get_all_results(
        "dcim/devices/",
        params={"site": site_slug, "limit": 1000}
    )

    rows = []
    for d in devices:
        rows.append({
            "Location": d["location"]["name"] if d.get("location") else "",
            "Rack": d["rack"]["name"] if d.get("rack") else "",
            "Device Name": d.get("name", ""),
            "Manufacturer": (
                d["device_type"]["manufacturer"]["name"]
                if d.get("device_type") and d["device_type"].get("manufacturer")
                else ""
            ),
            "Device Type": (
                d["device_type"]["display"]
                if d.get("device_type")
                else ""
            ),
            "Serial Number": d.get("serial", ""),
            "Role": (
                d["role"]["name"]
                if d.get("role")
                else ""
            )
        })

    df = pd.DataFrame(rows)

    if not df.empty:
        df = df.sort_values(by=["Location", "Rack", "Device Name"])

    # Dateiname
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    safe_site = site_name.replace(" ", "_")
    filename = f"{safe_site}_BOM_{date_str}.xlsx"

    # Excel erzeugen
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False)
    excel_bytes = buffer.getvalue()

    # Archivieren
    with open(os.path.join(EXPORT_DIR, filename), "wb") as f:
        f.write(excel_bytes)

    # Download
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"'
    }

    return Response(
        excel_bytes,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers
    )


# ======================
# Start
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
