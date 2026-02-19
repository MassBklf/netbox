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
    let panZoomInstance = null;
    let currentSvgData = null;

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

    // Load Graph (SVG)
    loadBtn.addEventListener('click', () => {
        const siteSlug = siteSelect.value;
        const locationId = locationSelect.value;
        const rackId = rackSelect.value;

        if (!siteSlug) {
            alert('Bitte wählen Sie einen Standort aus.');
            return;
        }

        loader.classList.remove('d-none');
        container.innerHTML = ''; // Clear container
        if (panZoomInstance) {
            panZoomInstance.destroy();
            panZoomInstance = null;
        }

        const params = new URLSearchParams({
            site: siteSlug
        });
        if (locationId) params.append('location', locationId);
        if (rackId) params.append('rack', rackId);

        fetch(`/api/graph-svg?${params.toString()}`)
            .then(response => {
                if (!response.ok) throw new Error('Network response was not ok');
                return response.blob();
            })
            .then(blob => {
                const reader = new FileReader();
                reader.onloadend = function() {
                    const svgContent = reader.result;
                    // FileReader returns data URL if using readAsDataURL, but we want text for innerHTML
                    // Let's use text() method of blob
                    blob.text().then(text => {
                        loader.classList.add('d-none');
                        container.innerHTML = text;
                        currentSvgData = text;

                        // Find the SVG element and enable pan-zoom
                        const svgElement = container.querySelector('svg');
                        if (svgElement) {
                            svgElement.setAttribute('width', '100%');
                            svgElement.setAttribute('height', '100%');

                            panZoomInstance = svgPanZoom(svgElement, {
                                zoomEnabled: true,
                                controlIconsEnabled: true,
                                fit: true,
                                center: true
                            });
                        } else {
                            alert('Keine SVG-Daten empfangen.');
                        }
                    });
                }
                reader.readAsDataURL(blob); // Actually just triggering the blob read flow or use blob.text()
            })
            .catch(err => {
                console.error('Error loading graph:', err);
                loader.classList.add('d-none');
                alert('Fehler beim Laden der Daten.');
            });
    });

    // Fit Graph
    fitBtn.addEventListener('click', () => {
        if (panZoomInstance) {
            panZoomInstance.fit();
            panZoomInstance.center();
        }
    });

    // Export SVG
    exportBtn.addEventListener('click', () => {
        if (!currentSvgData) return;

        const blob = new Blob([currentSvgData], { type: 'image/svg+xml' });
        const url = URL.createObjectURL(blob);

        const link = document.createElement('a');
        link.download = `kabelplan-${siteSelect.value}.svg`;
        link.href = url;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    });
});
