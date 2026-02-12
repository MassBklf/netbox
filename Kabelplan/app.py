import os
import requests
from flask import Flask, render_template, request, jsonify

# Configuration
NETBOX_URL = os.getenv("NETBOX_URL", "http://localhost:8000")
NETBOX_TOKEN = os.getenv("NETBOX_TOKEN", "")

# Headers
HEADERS = {}
if NETBOX_TOKEN:
    HEADERS["Authorization"] = f"Token {NETBOX_TOKEN}"

app = Flask(__name__)

# --- Helper Functions ---

def netbox_request(endpoint, params=None):
    """Makes a request to NetBox and handles errors."""
    url = f"{NETBOX_URL}/api/{endpoint}"
    try:
        response = requests.get(url, headers=HEADERS, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {endpoint}: {e}")
        return None

def get_all_results(endpoint, params=None):
    """Handles NetBox pagination to fetch all results."""
    results = []

    # Initial request
    data = netbox_request(endpoint, params)
    if not data:
        return []

    results.extend(data.get("results", []))

    # Handle pagination
    while data.get("next"):
        next_url = data["next"]
        # Remove base URL to get the relative endpoint/params
        # Or just use the full URL if requests allows it (it does)
        try:
            response = requests.get(next_url, headers=HEADERS)
            response.raise_for_status()
            data = response.json()
            results.extend(data.get("results", []))
        except requests.exceptions.RequestException as e:
            print(f"Error fetching next page: {e}")
            break

    return results

# --- Routes ---

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/filter-options")
def get_filter_options():
    """Returns Sites, Locations, and Racks for dropdowns."""
    sites = get_all_results("dcim/sites/")
    locations = get_all_results("dcim/locations/")
    racks = get_all_results("dcim/racks/")

    return jsonify({
        "sites": sorted(sites, key=lambda x: x["name"]),
        "locations": sorted(locations, key=lambda x: x["name"]),
        "racks": sorted(racks, key=lambda x: x["name"])
    })

@app.route("/api/graph-data")
def get_graph_data():
    """
    Fetches devices and cables based on filters and returns graph data.
    Filters: site (slug), location (id), rack (id)
    """
    site_slug = request.args.get("site")
    location_id = request.args.get("location")
    rack_id = request.args.get("rack")

    if not site_slug:
        return jsonify({"error": "Site is required"}), 400

    # 1. Fetch Devices
    device_params = {"site": site_slug}
    if location_id:
        device_params["location_id"] = location_id
    if rack_id:
        device_params["rack_id"] = rack_id

    devices = get_all_results("dcim/devices/", device_params)

    # Create a map of Device ID -> Device Info for quick lookup
    device_map = {}
    for d in devices:
        device_map[d["id"]] = {
            "id": d["id"],
            "name": d["name"] or f"Device {d['id']}",
            "role": d["device_role"]["name"] if d.get("device_role") else "Unknown",
            "type": d["device_type"]["model"] if d.get("device_type") else "Unknown",
            "location": d["location"]["name"] if d.get("location") else None
        }

    # 2. Fetch Cables
    # We fetch cables for the site.
    # If a specific location/rack is selected, we filter cables that connect to our fetched devices.
    cable_params = {"site": site_slug}
    cables = get_all_results("dcim/cables/", cable_params)

    nodes = []
    edges = []
    added_device_ids = set()
    added_interface_ids = set()

    for cable in cables:
        term_a = cable.get("termination_a")
        term_b = cable.get("termination_b")

        if not term_a or not term_b:
            continue

        # Helper to extract device info from a termination
        def get_device_info(term):
            # Check if termination is directly on a device (Interface, ConsolePort, etc.)
            if isinstance(term, dict) and term.get("device"):
                return term["device"]["id"], term["device"]["name"]
            return None, None

        dev_a_id, dev_a_name = get_device_info(term_a)
        dev_b_id, dev_b_name = get_device_info(term_b)

        # Filtering Logic
        include_cable = False

        if location_id or rack_id:
            # Check if at least one device is in our filtered list
            if (dev_a_id and dev_a_id in device_map) or (dev_b_id and dev_b_id in device_map):
                include_cable = True
        else:
            # Site only: show if at least one device is in the site (which is all of them usually)
            include_cable = True

        if include_cable:
            # Helper to add Device Node
            def add_device_node(d_id, d_name):
                if d_id not in added_device_ids:
                    if d_id in device_map:
                        d_info = device_map[d_id]
                        nodes.append({
                            "id": d_id,
                            "label": d_info["name"],
                            "group": d_info["role"],
                            "title": f"Role: {d_info['role']}<br>Type: {d_info['type']}",
                            "shape": "box",
                            "font": {"size": 20}
                        })
                    else:
                        nodes.append({
                            "id": d_id,
                            "label": d_name,
                            "group": "External",
                            "title": "External Device",
                            "shape": "box",
                            "font": {"size": 20}
                        })
                    added_device_ids.add(d_id)

            # Helper to add Interface Node and Link to Device
            def add_interface_node_and_link(d_id, term):
                # term_id is unique per interface/port in NetBox
                # We prefix it to avoid collision (though ints shouldn't collide with strings if we use that)
                # But safer to use strings for all IDs
                term_id = term.get("id")
                node_id = f"if_{term_id}"

                if node_id not in added_interface_ids:
                    nodes.append({
                        "id": node_id,
                        "label": term.get("name", "?"),
                        "group": "Interface",
                        "shape": "box",
                        "color": {"background": "white", "border": "black"},
                        "font": {"size": 10},
                        "widthConstraint": {"maximum": 100}
                    })
                    added_interface_ids.add(node_id)

                    # Link Interface to Device
                    edges.append({
                        "from": d_id,
                        "to": node_id,
                        "length": 50, # Short distance
                        "color": "black",
                        "width": 2
                    })
                return node_id

            if dev_a_id and dev_b_id:
                # Add Devices
                add_device_node(dev_a_id, dev_a_name)
                add_device_node(dev_b_id, dev_b_name)

                # Add Interfaces
                if_node_a = add_interface_node_and_link(dev_a_id, term_a)
                if_node_b = add_interface_node_and_link(dev_b_id, term_b)

                # Add Cable (Interface <-> Interface)
                cable_label = cable.get("label") or f"#{cable.get('id')}"

                edges.append({
                    "from": if_node_a,
                    "to": if_node_b,
                    "label": cable_label,
                    "arrows": "to;from",
                    "length": 200, # Longer distance for cable
                    "font": {"align": "top"}
                })

    return jsonify({"nodes": nodes, "edges": edges})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
