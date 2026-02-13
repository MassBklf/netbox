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
            const width = 160; // Increased width for better label fit
            // Increase height slightly to space out ports
            const portCount = nodeData.ports.length;
            const height = Math.max(80, portCount * 25); // 25px per port for better spacing

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
                    fontSize: 14,
                    fontWeight: 'bold',
                    textWrap: {
                        width: width - 10,
                        ellipsis: true
                    }
                }
            });
            device.set('id', nodeData.id);

            // Add Ports
            const portsIn = [];
            const portsOut = [];

            // Distribute ports
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

            // Define port groups with better label positioning
            device.set('ports', {
                groups: {
                    'left': {
                        position: { name: 'left' },
                        attrs: {
                            circle: { fill: '#ffffff', stroke: '#333333', strokeWidth: 1, r: 5 },
                            text: {
                                fill: '#000000',
                                fontSize: 11, // Increased font size
                                x: -12, // Move label further out
                                y: 0,
                                textAnchor: 'end',
                                fontWeight: 'bold' // Bold labels
                            }
                        },
                        label: { position: { name: 'left' } }
                    },
                    'right': {
                        position: { name: 'right' },
                        attrs: {
                            circle: { fill: '#ffffff', stroke: '#333333', strokeWidth: 1, r: 5 },
                            text: {
                                fill: '#000000',
                                fontSize: 11,
                                x: 12,
                                y: 0,
                                textAnchor: 'start',
                                fontWeight: 'bold'
                            }
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

                // Tuned Manhattan Router
                link.router('manhattan', {
                    step: 20, // Grid step size
                    padding: 30, // Padding around obstacles
                    maximumLoops: 2000,
                    excludeTypes: ['standard.Rectangle'] // Avoid routing through nodes
                });

                link.connector('rounded', { radius: 10 });
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
                            fill: '#ffffff',
                            stroke: '#666',
                            strokeWidth: 1,
                            rx: 3, ry: 3
                        }
                    },
                    position: 0.5 // Center label
                }]);
                cells.push(link);
            }
        });

        graph.resetCells(cells);

        // 3. Auto Layout with increased spacing
        joint.layout.DirectedGraph.layout(graph, {
            dagre: dagre,
            graphlib: graphlib,
            setLinkVertices: false,
            rankDir: 'LR',
            nodeSep: 150, // Increased horizontal separation
            rankSep: 300, // Increased rank separation
            marginX: 100,
            marginY: 100
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
