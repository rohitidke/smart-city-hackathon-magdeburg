/**
 * Leaflet.js Helper Functions for Smart City Dashboard
 * Map configurations with dark theme
 */

// Magdeburg coordinates
const MAGDEBURG_CENTER = [52.1205, 11.6276];
const DEFAULT_ZOOM = 12;

/**
 * Create base map with dark theme
 */
function createBaseMap(containerId, options = {}) {
  const map = L.map(containerId, {
    center: options.center || MAGDEBURG_CENTER,
    zoom: options.zoom || DEFAULT_ZOOM,
    ...options,
  });

  // Add dark tile layer (CartoDB Dark Matter)
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '©OpenStreetMap, ©CartoDB',
    maxZoom: 19,
  }).addTo(map);

  return map;
}

/**
 * Create accident heatmap
 */
async function createAccidentMap(containerId) {
  const map = createBaseMap(containerId);

  try {
    const response = await fetch('/api/data/accidents/geojson');
    const geojson = await response.json();

    // Create marker cluster group
    const markers = L.markerClusterGroup({
      iconCreateFunction: function(cluster) {
        const count = cluster.getChildCount();
        let size = 'small';
        if (count > 50) size = 'large';
        else if (count > 20) size = 'medium';

        return L.divIcon({
          html: `<div>${count}</div>`,
          className: `marker-cluster marker-cluster-${size}`,
          iconSize: L.point(40, 40),
        });
      },
    });

    // Add markers
    L.geoJSON(geojson, {
      pointToLayer: function(feature, latlng) {
        const props = feature.properties;
        const color = props.ist_rad ? '#ffc850' : '#ff6b6b';

        return L.circleMarker(latlng, {
          radius: 6,
          fillColor: color,
          color: '#fff',
          weight: 1,
          opacity: 1,
          fillOpacity: 0.8,
        });
      },
      onEachFeature: function(feature, layer) {
        const props = feature.properties;
        layer.bindPopup(`
          <strong>Unfall ${props.jahr}</strong><br>
          Kategorie: ${props.kategorie}<br>
          ${props.ist_rad ? '🚴 Fahrrad beteiligt' : ''}
        `);
      },
    }).addTo(markers);

    markers.addTo(map);
  } catch (error) {
    console.error('Error loading accident data:', error);
  }

  return map;
}

/**
 * Create rent choropleth map
 */
async function createRentMap(containerId) {
  const map = createBaseMap(containerId);

  try {
    const [districtsResponse, rentResponse] = await Promise.all([
      fetch('/api/data/districts/geojson'),
      fetch('/api/charts/rent-by-district'),
    ]);

    const districts = await districtsResponse.json();
    const rentData = await rentResponse.json();

    // Create lookup map
    const rentLookup = {};
    rentData.forEach(d => {
      rentLookup[d.district] = d.avg_rent;
    });

    // Color scale function
    function getColor(rent) {
      return rent > 10 ? '#ff6b6b' :
             rent > 9 ? '#ffc850' :
             rent > 8 ? '#48c7a7' :
             rent > 7 ? '#5b8cff' :
                        '#6c63ff';
    }

    // Style function
    function style(feature) {
      const districtName = feature.properties.name || feature.properties.NAME;
      const rent = rentLookup[districtName] || 0;

      return {
        fillColor: getColor(rent),
        weight: 2,
        opacity: 1,
        color: '#2a2f45',
        fillOpacity: 0.7,
      };
    }

    // Add district layer
    const districtLayer = L.geoJSON(districts, {
      style: style,
      onEachFeature: function(feature, layer) {
        const districtName = feature.properties.name || feature.properties.NAME;
        const rent = rentLookup[districtName];

        if (rent) {
          layer.bindPopup(`
            <strong>${districtName}</strong><br>
            Durchschnittsmiete: <strong>€${rent}/m²</strong>
          `);
        }

        layer.on({
          mouseover: function(e) {
            e.target.setStyle({
              weight: 3,
              fillOpacity: 0.9,
            });
          },
          mouseout: function(e) {
            districtLayer.resetStyle(e.target);
          },
        });
      },
    }).addTo(map);

    // Add legend
    const legend = L.control({ position: 'bottomright' });
    legend.onAdd = function() {
      const div = L.DomUtil.create('div', 'info legend');
      const grades = [0, 7, 8, 9, 10];
      div.innerHTML = '<h4>Miete (€/m²)</h4>';

      for (let i = 0; i < grades.length; i++) {
        div.innerHTML +=
          `<i style="background:${getColor(grades[i] + 1)}"></i> ` +
          grades[i] + (grades[i + 1] ? '&ndash;' + grades[i + 1] + '<br>' : '+');
      }
      return div;
    };
    legend.addTo(map);

  } catch (error) {
    console.error('Error loading rent data:', error);
  }

  return map;
}

/**
 * Create transit stops map
 */
async function createTransitMap(containerId) {
  const map = createBaseMap(containerId);

  try {
    const response = await fetch('/api/data/transit/stops');
    const stops = await response.json();

    // Add markers
    stops.forEach(stop => {
      if (stop.lat && stop.lon) {
        L.circleMarker([stop.lat, stop.lon], {
          radius: 5,
          fillColor: '#48c7a7',
          color: '#fff',
          weight: 1,
          fillOpacity: 0.8,
        })
        .bindPopup(`
          <strong>${stop.name}</strong><br>
          ${stop.lines ? `Linien: ${stop.lines.join(', ')}` : ''}
        `)
        .addTo(map);
      }
    });

  } catch (error) {
    console.error('Error loading transit data:', error);
  }

  return map;
}

/**
 * Create cafes map
 */
async function createCafesMap(containerId) {
  const map = createBaseMap(containerId);

  try {
    const response = await fetch('/api/data/cafes/geojson');
    const geojson = await response.json();

    L.geoJSON(geojson, {
      pointToLayer: function(feature, latlng) {
        return L.circleMarker(latlng, {
          radius: 6,
          fillColor: '#ffc850',
          color: '#fff',
          weight: 1,
          fillOpacity: 0.8,
        });
      },
      onEachFeature: function(feature, layer) {
        const props = feature.properties;
        layer.bindPopup(`
          <strong>${props.name || 'Café/Restaurant'}</strong><br>
          ${props.cuisine ? `Küche: ${props.cuisine}` : ''}
        `);
      },
    }).addTo(map);

  } catch (error) {
    console.error('Error loading cafe data:', error);
  }

  return map;
}

// Custom CSS for map legend
const legendCSS = `
.info.legend {
  background: rgba(26, 29, 39, 0.95);
  border: 1px solid #2a2f45;
  border-radius: 8px;
  padding: 10px;
  color: #e2e8f0;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
}

.info.legend h4 {
  margin: 0 0 8px 0;
  font-size: 14px;
  color: #48c7a7;
}

.info.legend i {
  width: 18px;
  height: 18px;
  float: left;
  margin-right: 8px;
  opacity: 0.8;
  border-radius: 2px;
}

.marker-cluster-small {
  background-color: rgba(72, 199, 167, 0.6);
}

.marker-cluster-medium {
  background-color: rgba(255, 200, 80, 0.6);
}

.marker-cluster-large {
  background-color: rgba(255, 107, 107, 0.6);
}

.marker-cluster div {
  width: 30px;
  height: 30px;
  margin-left: 5px;
  margin-top: 5px;
  text-align: center;
  border-radius: 15px;
  font-weight: 700;
  background-color: rgba(26, 29, 39, 0.9);
  color: #e2e8f0;
  line-height: 30px;
}
`;

// Inject CSS
const style = document.createElement('style');
style.textContent = legendCSS;
document.head.appendChild(style);

// Export functions
window.MapHelpers = {
  createBaseMap,
  createAccidentMap,
  createRentMap,
  createTransitMap,
  createCafesMap,
  MAGDEBURG_CENTER,
};
