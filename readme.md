# NetBox Standort Exporter

Kleine Webanwendung zum Export von NetBox-Geräten und Inventory-Items
nach Standort als Excel-Datei.

## ✨ Features

- Standort-Auswahl per Web-UI
- Export von:
  - Devices
  - Inventory Items (z. B. Monitore, Module, Netzteile)
- Excel-Export (.xlsx)
- Zugriff über NetBox REST API
- Docker- & Reverse-Proxy-ready

## 🧱 Architektur

- FastAPI
- NetBox REST API
- openpyxl
- Docker / Docker Compose
- Reverse Proxy (z. B. Nginx)

## 🚀 Quick Start

### Voraussetzungen
- Docker
- Docker Compose
- NetBox API Token mit `dcim:read`

### `.env` Datei erstellen

```env
NETBOX_URL=https://netbox.example.local
NETBOX_API_TOKEN=xxxxxxxxxxxxxxxx
```

### Proxy
```
location /export/ {
    proxy_pass http://netbox-exporter:8000/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```