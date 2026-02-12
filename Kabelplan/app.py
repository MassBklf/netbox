import os
import pynetbox
from flask import Flask, render_template, request, jsonify

# Configuration
NETBOX_URL = os.getenv("NETBOX_URL", "http://localhost:8000")
NETBOX_TOKEN = os.getenv("NETBOX_TOKEN", "")

app = Flask(__name__)

# Initialize NetBox API
nb = pynetbox.api(NETBOX_URL, token=NETBOX_TOKEN)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/filter-options")
def get_filter_options():
    """Returns Sites, Locations, and Racks for dropdowns."""
    try:
        sites = list(nb.dcim.sites.all())
        locations = list(nb.dcim.locations.all())
        racks = list(nb.dcim.racks.all())

        return jsonify({
            "sites": sorted([{"id": s.id, "name": s.name, "slug": s.slug} for s in sites], key=lambda x: x["name"]),
            "locations": sorted([{"id": l.id, "name": l.name, "site": {"id": l.site.id} if l.site else None} for l in locations], key=lambda x: x["name"]),
            "racks": sorted([{"id": r.id, "name": r.name, "site": {"id": r.site.id} if r.site else None} for r in racks], key=lambda x: x["name"])
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/graph-data")
def get_graph_data():
    """
    Fetches devices and cables based on filters and returns graph data.
    """
    site_slug = request.args.get("site")
    location_id = request.args.get("location")
    rack_id = request.args.get("rack")

    if not site_slug:
        return jsonify({"error": "Site is required"}), 400

    try:
        # 1. Fetch Devices
        device_filter = {"site": site_slug}
        if location_id:
            device_filter["location_id"] = location_id
        if rack_id:
            device_filter["rack_id"] = rack_id

        devices = list(nb.dcim.devices.filter(**device_filter))

        nodes = []
        device_ids = set()

        # We need to fetch interfaces for these devices to create ports
        # Optimization: Fetch all interfaces for the site and filter in memory if needed,
        # or fetch per device (slow). Better: fetch interfaces for devices in list.
        # pynetbox filter 'device_id' accepts a list.

        device_id_list = [d.id for d in devices]
        if not device_id_list:
             return jsonify({"nodes": [], "links": []})

        # Process Devices
        for d in devices:
            device_ids.add(str(d.id))
            nodes.append({
                "id": str(d.id),
                "name": d.name or f"Device {d.id}",
                "model": d.device_type.model if d.device_type else "Unknown",
                "role": d.device_role.name if d.device_role else "Unknown",
                "ports": [] # Will be populated
            })

        # 2. Fetch Interfaces (Ports)
        # Fetching interfaces for all devices in scope
        # We process in chunks to avoid URL length issues if many devices
        interfaces = []
        chunk_size = 50
        for i in range(0, len(device_id_list), chunk_size):
            chunk = device_id_list[i:i+chunk_size]
            interfaces.extend(list(nb.dcim.interfaces.filter(device_id=chunk)))

        # Map interfaces to device nodes
        interface_map = {} # id -> {name, device_id}

        node_map = {n["id"]: n for n in nodes}

        for i in interfaces:
            d_id = str(i.device.id)
            if d_id in node_map:
                port_data = {
                    "id": str(i.id),
                    "name": i.name,
                    "type": "copper" # simplistic type
                }
                node_map[d_id]["ports"].append(port_data)
                interface_map[i.id] = {"name": i.name, "device_id": d_id}

        # 3. Fetch Cables
        # We fetch cables connected to our devices
        # Similar chunk approach or fetch by site
        cables = list(nb.dcim.cables.filter(site=site_slug))

        links = []

        for cable in cables:
            # We only care if both ends are in our scope (or at least one if we want to show external links)
            # For now, let's show links where at least one end is in our device list.

            term_a = cable.a_terminations[0] if cable.a_terminations else None
            term_b = cable.b_terminations[0] if cable.b_terminations else None

            if not term_a or not term_b:
                continue

            # Helper to get device/interface ID
            # In pynetbox, terminations are objects. We check if they are interfaces.
            # Assuming 'dcim.interface' type.

            def get_term_info(term):
                if hasattr(term, 'device') and hasattr(term, 'id'):
                    return str(term.device.id), str(term.id)
                return None, None

            dev_a_id, int_a_id = get_term_info(term_a)
            dev_b_id, int_b_id = get_term_info(term_b)

            if dev_a_id and dev_b_id:
                # Check if visible
                visible_a = dev_a_id in device_ids
                visible_b = dev_b_id in device_ids

                if visible_a and visible_b:
                    links.append({
                        "id": str(cable.id),
                        "source": {"id": dev_a_id, "port": int_a_id},
                        "target": {"id": dev_b_id, "port": int_b_id},
                        "label": cable.label or f"#{cable.id}",
                        "color": cable.color or "black"
                    })
                # Note: Handling external links (one end visible) requires adding "External Node" logic
                # For this iteration, we stick to internal links.

        return jsonify({"nodes": nodes, "links": links})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
