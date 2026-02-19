import os
import pynetbox
from flask import Flask, render_template, request, jsonify, make_response
import graphviz
import io

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

@app.route("/api/graph-svg")
def get_graph_svg():
    """
    Fetches devices and cables based on filters and returns a Graphviz SVG.
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

        if not devices:
             return jsonify({"error": "No devices found"}), 404

        # Initialize Graphviz Digraph
        dot = graphviz.Digraph(comment='NetBox Kabelplan', format='svg')
        dot.attr(rankdir='LR', splines='ortho', nodesep='1.0', ranksep='2.0', layout='dot')
        dot.attr('node', shape='none', fontname='Helvetica', fontsize='12')
        dot.attr('edge', fontname='Helvetica', fontsize='10')

        device_ids = set()
        device_ports = {} # device_id -> [port_obj, ...]
        device_map = {} # device_id -> device_obj

        device_id_list = [d.id for d in devices]

        # Pre-fetch interfaces for layout
        interfaces = []
        chunk_size = 50
        for i in range(0, len(device_id_list), chunk_size):
            chunk = device_id_list[i:i+chunk_size]
            interfaces.extend(list(nb.dcim.interfaces.filter(device_id=chunk)))

        for i in interfaces:
            d_id = str(i.device.id)
            if d_id not in device_ports:
                device_ports[d_id] = []
            device_ports[d_id].append(i)

        # 2. Create Nodes
        for d in devices:
            d_id = str(d.id)
            device_ids.add(d_id)
            device_map[d_id] = d

            ports = device_ports.get(d_id, [])
            ports.sort(key=lambda x: x.name)

            # Create HTML-like label table
            # We use a table to represent the device and its ports
            # <TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0"> ... </TABLE>

            label = '<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" BGCOLOR="#E3F2FD">'
            # Header
            label += f'<TR><TD COLSPAN="2" BGCOLOR="#2196F3" PORT="header"><FONT COLOR="white"><B>{d.name}</B><BR/>({d.device_type.model})</FONT></TD></TR>'

            # Ports
            for p in ports:
                p_id = str(p.id)
                # Escape port name for HTML
                p_name = p.name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                # Important: PORT attribute is used for connection
                label += f'<TR><TD PORT="p{p_id}" ALIGN="LEFT" BALIGN="LEFT"> {p_name} </TD><TD ALIGN="RIGHT"> </TD></TR>'

            label += '</TABLE>>'

            dot.node(d_id, label=label)

        # 3. Create Edges (Cables)
        # We need to fetch cables relevant to these devices.
        # Fetching all site cables can be heavy, but filtering by device list is tedious.
        # Let's fetch all site cables and filter in memory as before.
        cables = list(nb.dcim.cables.filter(site=site_slug))

        for cable in cables:
            term_a = cable.a_terminations[0] if cable.a_terminations else None
            term_b = cable.b_terminations[0] if cable.b_terminations else None

            if not term_a or not term_b:
                continue

            # Helper
            def get_term_info(term):
                if hasattr(term, 'device') and hasattr(term, 'id'):
                    return str(term.device.id), str(term.id)
                return None, None

            dev_a_id, int_a_id = get_term_info(term_a)
            dev_b_id, int_b_id = get_term_info(term_b)

            if dev_a_id and dev_b_id:
                # Check visibility
                visible_a = dev_a_id in device_ids
                visible_b = dev_b_id in device_ids

                if visible_a and visible_b:
                    # Graphviz record ports: node:port
                    source = f"{dev_a_id}:p{int_a_id}"
                    target = f"{dev_b_id}:p{int_b_id}"

                    label = cable.label or ""
                    color = cable.color or "black"
                    if color and not color.startswith("#") and not color in ['black', 'red', 'blue', 'green']:
                         color = "black" # Fallback

                    dot.edge(source, target, label=label, color=color, penwidth='2.0')

        # Render to SVG
        svg_bytes = dot.pipe()

        response = make_response(svg_bytes)
        response.headers['Content-Type'] = 'image/svg+xml'
        return response

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
