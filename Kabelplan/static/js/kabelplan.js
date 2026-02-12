document.addEventListener('DOMContentLoaded', () => {
    const siteSelect = document.getElementById('site-select');
    const locationSelect = document.getElementById('location-select');
    const rackSelect = document.getElementById('rack-select');
    const loadBtn = document.getElementById('load-btn');
    const fitBtn = document.getElementById('fit-btn');
    const exportBtn = document.getElementById('export-btn');
    const loader = document.getElementById('loader');
    const container = document.getElementById('mynetwork');

    let network = null;
    let allLocations = [];
    let allRacks = [];

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
        if (network) network.destroy(); // Clear existing graph

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

                drawGraph(data.nodes, data.edges);
            })
            .catch(err => {
                console.error('Error loading graph:', err);
                loader.classList.add('d-none');
                alert('Fehler beim Laden der Daten.');
            });
    });

    // Fit Graph
    fitBtn.addEventListener('click', () => {
        if (network) network.fit({ animation: true });
    });

    // Export Graph
    exportBtn.addEventListener('click', () => {
        if (!network) return;

        // Setup canvas for export
        const canvas = container.getElementsByTagName('canvas')[0];
        if (!canvas) return;

        // Create a temporary link
        const link = document.createElement('a');
        link.download = `kabelplan-${siteSelect.value}-${new Date().toISOString().slice(0,10)}.png`;
        link.href = canvas.toDataURL('image/png');
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    });

    function drawGraph(nodesData, edgesData) {
        const data = {
            nodes: new vis.DataSet(nodesData),
            edges: new vis.DataSet(edgesData)
        };

        const options = {
            nodes: {
                shape: 'box',
                font: {
                    size: 14,
                    face: 'Arial'
                },
                margin: 10,
                color: {
                    border: '#2B7CE9',
                    background: '#D2E5FF'
                }
            },
            edges: {
                width: 2,
                color: { color: '#848484' },
                arrows: {
                    to: { enabled: true, scaleFactor: 0.5 },
                    from: { enabled: true, scaleFactor: 0.5 }
                },
                smooth: {
                    type: 'continuous'
                },
                font: {
                    align: 'top'
                }
            },
            layout: {
                improvedLayout: true,
                hierarchical: {
                    enabled: false
                }
            },
            physics: {
                stabilization: false,
                barnesHut: {
                    gravitationalConstant: -2000,
                    centralGravity: 0.3,
                    springLength: 95,
                    springConstant: 0.04,
                    damping: 0.09,
                    avoidOverlap: 0.1
                }
            },
            interaction: {
                navigationButtons: true,
                keyboard: true
            }
        };

        network = new vis.Network(container, data, options);

        // Optional: Double click to focus
        network.on("doubleClick", function (params) {
            if (params.nodes.length > 0) {
                network.focus(params.nodes[0], {
                    animation: true,
                    scale: 1.5
                });
            }
        });
    }
});
