from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from .netbox import get_sites, get_devices_by_site, get_inventory_items
from .exporter import create_excel

import io

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    sites = get_sites()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "sites": sites}
    )


@app.get("/export")
def export(site_id: int):
    rows = []

    devices = get_devices_by_site(site_id)

    for device in devices:
        rows.append([
            "Device",
            device["name"],
            device["device_type"]["manufacturer"]["name"],
            device["device_type"]["model"],
            device["device_type"]["part_number"],
            device["serial"],
            device["rack"]["name"] if device["rack"] else "",
            device["site"]["name"],
            device["location"]["name"] if device["location"] else "",
            device["role"]["name"] if device["role"] else "",
            ""
        ])

        items = get_inventory_items(device["id"])
        for item in items:
            rows.append([
                "Inventory",
                item["name"],
                item["manufacturer"]["name"] if item["manufacturer"] else "",
                "",
                item["part_id"],
                item["serial"],
                "",
                device["site"]["name"],
                device["location"]["name"] if device["location"] else "",
                item["role"]["name"] if item["role"] else "",
                device["name"]
            ])

    wb = create_excel(rows)

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)

    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": "attachment; filename=inventar.xlsx"
        }
    )
