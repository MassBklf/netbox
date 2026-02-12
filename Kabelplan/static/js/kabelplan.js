document.addEventListener('DOMContentLoaded', () => {
    const siteSelect = document.getElementById('site-select');
    const locationSelect = document.getElementById('location-select');
    const rackSelect = document.getElementById('rack-select');
    const loadBtn = document.getElementById('load-btn');
    const fitBtn = document.getElementById('fit-btn');
    const exportBtn = document.getElementById('export-btn');
    const loader = document.getElementById('loader');
    const container = document.getElementById('mynetwork');

    let allLocations = [];
    let allRacks = [];

    // JointJS Setup
    const graph = new joint.dia.Graph();
    const paper = new joint.dia.Paper({
        el: container,
        model: graph,
        width: '100%',
        height: '100%',
        gridSize: 10,
        drawGrid: true,
        background: {
            color: '#fafafa'
        },
        interactive: { linkMove: false }, // Prevent moving links manually
        defaultLink: new joint.shapes.standard.Link({
            attrs: {
                line: {
                    stroke: '#333333',
                    strokeWidth: 2
                }
            }
        })
    });

    // Zoom/Pan State
    let scale = 1;
    let currentX = 0;
    let currentY = 0;

    // Pan
    paper.on('blank:pointerdown', (evt, x, y) => {
        const scale = paper.scale();
        evt.data = { x: x * scale.sx, y: y * scale.sy };
    });

    paper.on('blank:pointermove', (evt, x, y) => {
        if (evt.data) {
            const scale = paper.scale();
            const nextX = x * scale.sx;
            const nextY = y * scale.sy;
            currentX += nextX - evt.data.x;
            currentY += nextY - evt.data.y;
            paper.translate(currentX, currentY);
            evt.data.x = nextX;
            evt.data.y = nextY;
        }
    });

    paper.on('blank:pointerup', (evt) => {
        delete evt.data;
    });

    // Zoom
    container.addEventListener('wheel', (event) => {
        event.preventDefault();
        const delta = Math.sign(event.deltaY) * -0.1;
        scale = Math.max(0.1, Math.min(3, scale + delta));
        paper.scale(scale, scale);
    });


    // Initialize Selects
    fetch('/api/filter-options')
        .then(response => response.json())
        .then(data => {
            // Populate Sites
            data.sites.forEach(site => {
                const option = document.createElement('option');
                option.value = site.slug; // Use slug for API calls
                option.textContent = site.name;
                option.dataset.id = site.id; // Store ID for filtering locations/racks
                siteSelect.appendChild(option);
            });

            allLocations = data.locations;
            allRacks = data.racks;
        })
        .catch(err => console.error('Error fetching filters:', err));

    // Handle Site Change to Filter Locations and Racks
    siteSelect.addEventListener('change', () => {
        const siteSlug = siteSelect.value;
        const siteId = siteSelect.options[siteSelect.selectedIndex].dataset.id;

        locationSelect.innerHTML = '<option value="">Alle</option>';
        rackSelect.innerHTML = '<option value="">Alle</option>';
        locationSelect.disabled = !siteSlug;
        rackSelect.disabled = !siteSlug;

        if (siteId) {
            // Filter Locations
            const filteredLocations = allLocations.filter(loc => loc.site && loc.site.id == siteId);
            filteredLocations.forEach(loc => {
                const option = document.createElement('option');
                option.value = loc.id;
                option.textContent = loc.name;
                locationSelect.appendChild(option);
            });

            // Filter Racks
            const filteredRacks = allRacks.filter(rack => rack.site && rack.site.id == siteId);
            filteredRacks.forEach(rack => {
                const option = document.createElement('option');
                option.value = rack.id;
                option.textContent = rack.name;
                rackSelect.appendChild(option);
            });
        }
    });

    // Load Graph
    loadBtn.addEventListener('click', () => {
        const siteSlug = siteSelect.value;
        const locationId = locationSelect.value;
        const rackId = rackSelect.value;

        if (!siteSlug) {
            alert('Bitte wählen Sie einen Standort aus.');
            return;
        }

        loader.classList.remove('d-none');
        graph.clear(); // Clear existing graph

        // Reset View
        scale = 1;
        currentX = 0;
        currentY = 0;
        paper.scale(1, 1);
        paper.translate(0, 0);

        const params = new URLSearchParams({
            site: siteSlug
        });
        if (locationId) params.append('location', locationId);
        if (rackId) params.append('rack', rackId);

        fetch(`/api/graph-data?${params.toString()}`)
            .then(response => response.json())
            .then(data => {
                loader.classList.add('d-none');

                if (data.nodes.length === 0) {
                    alert('Keine Daten für diese Auswahl gefunden.');
                    return;
                }

                buildGraph(data);
            })
            .catch(err => {
                console.error('Error loading graph:', err);
                loader.classList.add('d-none');
                alert('Fehler beim Laden der Daten.');
            });
    });

    // Fit Graph
    fitBtn.addEventListener('click', () => {
        paper.scaleContentToFit({ padding: 50 });
        // Update local state to match fit
        const t = paper.translate();
        const s = paper.scale();
        currentX = t.tx;
        currentY = t.ty;
        scale = s.sx;
    });

    // Export Graph (Basic SVG export)
    exportBtn.addEventListener('click', () => {
        // JointJS doesn't have built-in image export in open source version easily without plugins?
        // Actually we can convert SVG to Canvas to Image.
        // For now, simpler: Open SVG in new tab or trigger download of SVG.

        const svg = paper.svg;
        const serializer = new XMLSerializer();
        const content = serializer.serializeToString(svg);
        const blob = new Blob([content], { type: 'image/svg+xml' });
        const url = URL.createObjectURL(blob);

        const link = document.createElement('a');
        link.download = `kabelplan-${siteSelect.value}.svg`;
        link.href = url;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    });

    function buildGraph(data) {
        const cells = [];
        const deviceMap = {};

        // 1. Create Nodes (Devices)
        data.nodes.forEach(nodeData => {
            const width = 140;
            // Height depends on number of ports?
            // Let's set a minimum height and grow if many ports.
            const portCount = nodeData.ports.length;
            const height = Math.max(60, portCount * 20); // 20px per port

            const device = new joint.shapes.standard.Rectangle();
            device.position(0, 0);
            device.resize(width, height);
            device.attr({
                body: {
                    fill: '#E3F2FD',
                    stroke: '#2196F3',
                    strokeWidth: 2,
                    rx: 5, ry: 5
                },
                label: {
                    text: nodeData.name + '\n(' + nodeData.model + ')',
                    fill: '#0d47a1',
                    fontSize: 12,
                    fontWeight: 'bold'
                }
            });
            device.set('id', nodeData.id); // Set JointJS ID to match NetBox ID

            // Add Ports
            const portsIn = [];
            const portsOut = [];

            // Heuristic: Distribute ports left/right.
            // Real schematic logic is hard without specific "side" data.
            // Let's put first half on left, second half on right?
            // Or just all on right?
            // Common convention: In left, Out right. But interfaces are bidirectional.
            // Let's just put them all on the right for now (Rack style) or distribute.
            // Let's distribute.

            nodeData.ports.forEach((port, index) => {
                const portObj = {
                    id: port.id,
                    group: index % 2 === 0 ? 'left' : 'right',
                    attrs: {
                        label: { text: port.name }
                    }
                };
                if (index % 2 === 0) portsIn.push(portObj);
                else portsOut.push(portObj);
            });

            // Define port groups
            device.set('ports', {
                groups: {
                    'left': {
                        position: { name: 'left' },
                        attrs: {
                            circle: { fill: '#ffffff', stroke: '#333333', strokeWidth: 1, r: 4 },
                            text: { fill: '#000000', fontSize: 10, x: -10, y: 0, textAnchor: 'end' } // Label outside
                        },
                        label: { position: { name: 'left' } }
                    },
                    'right': {
                        position: { name: 'right' },
                        attrs: {
                            circle: { fill: '#ffffff', stroke: '#333333', strokeWidth: 1, r: 4 },
                            text: { fill: '#000000', fontSize: 10, x: 10, y: 0, textAnchor: 'start' } // Label outside
                        },
                        label: { position: { name: 'right' } }
                    }
                },
                items: [...portsIn, ...portsOut]
            });

            cells.push(device);
            deviceMap[nodeData.id] = device;
        });

        // 2. Create Links (Cables)
        data.links.forEach(linkData => {
            const sourceId = linkData.source.id;
            const sourcePort = linkData.source.port;
            const targetId = linkData.target.id;
            const targetPort = linkData.target.port;

            if (deviceMap[sourceId] && deviceMap[targetId]) {
                const link = new joint.shapes.standard.Link();
                link.source({ id: sourceId, port: sourcePort });
                link.target({ id: targetId, port: targetPort });
                link.router('manhattan', {
                    step: 10,
                    padding: 20
                });
                link.connector('rounded');
                link.attr({
                    line: {
                        stroke: linkData.color || '#333333',
                        strokeWidth: 2,
                        targetMarker: {
                            type: 'path',
                            d: 'M 10 -5 0 0 10 5 z'
                        }
                    }
                });
                link.labels([{
                    attrs: {
                        text: {
                            text: linkData.label
                        },
                        rect: {
                            fill: '#ffffff'
                        }
                    }
                }]);
                cells.push(link);
            }
        });

        graph.resetCells(cells);

        // 3. Auto Layout
        joint.layout.DirectedGraph.layout(graph, {
            dagre: dagre,
            graphlib: graphlib,
            setLinkVertices: false,
            rankDir: 'LR',
            nodeSep: 80,
            rankSep: 200,
            marginX: 50,
            marginY: 50
        });

        // Initial fit
        paper.scaleContentToFit({ padding: 50 });
        const t = paper.translate();
        const s = paper.scale();
        currentX = t.tx;
        currentY = t.ty;
        scale = s.sx;
    }
});
