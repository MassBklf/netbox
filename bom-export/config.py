import os

NETBOX_URL = os.getenv("NETBOX_URL")
NETBOX_API_TOKEN = os.getenv("NETBOX_API_TOKEN")

if not NETBOX_URL or not NETBOX_API_TOKEN:
    raise RuntimeError("NETBOX_URL oder NETBOX_API_TOKEN fehlt")