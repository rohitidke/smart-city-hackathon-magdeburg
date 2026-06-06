/**
 * Chart.js Helper Functions for Smart City Dashboard
 * Reusable chart configurations with dark theme
 */

const CHART_COLORS = {
  primary: '#6c63ff',
  secondary: '#48c7a7',
  danger: '#ff6b6b',
  warning: '#ffc850',
  info: '#5b8cff',
  purple: '#9b59b6',
  teal: '#1abc9c',
};

const CHART_DEFAULTS = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      labels: {
        color: '#e2e8f0',
        font: {
          size: 12,
        },
      },
    },
  },
  scales: {
    x: {
      ticks: {
        color: '#8892a4',
      },
      grid: {
        color: '#2a2f45',
      },
    },
    y: {
      ticks: {
        color: '#8892a4',
      },
      grid: {
        color: '#2a2f45',
      },
    },
  },
};

/**
 * Create a line chart
 */
function createLineChart(ctx, data, options = {}) {
  return new Chart(ctx, {
    type: 'line',
    data: data,
    options: {
      ...CHART_DEFAULTS,
      ...options,
    },
  });
}

/**
 * Create a bar chart
 */
function createBarChart(ctx, data, options = {}) {
  return new Chart(ctx, {
    type: 'bar',
    data: data,
    options: {
      ...CHART_DEFAULTS,
      ...options,
    },
  });
}

/**
 * Create a pie chart
 */
function createPieChart(ctx, data, options = {}) {
  const defaults = { ...CHART_DEFAULTS };
  delete defaults.scales;  // Pie charts don't have scales

  return new Chart(ctx, {
    type: 'pie',
    data: data,
    options: {
      ...defaults,
      ...options,
    },
  });
}

/**
 * Create a doughnut chart
 */
function createDoughnutChart(ctx, data, options = {}) {
  const defaults = { ...CHART_DEFAULTS };
  delete defaults.scales;

  return new Chart(ctx, {
    type: 'doughnut',
    data: data,
    options: {
      ...defaults,
      ...options,
    },
  });
}

/**
 * Create climate temperature trend line chart
 */
function createClimateTrendChart(ctx, climateData) {
  const years = climateData.map(d => d.year);
  const temps = climateData.map(d => d.avg_temp);

  return createLineChart(ctx, {
    labels: years,
    datasets: [
      {
        label: 'Durchschnittstemperatur (°C)',
        data: temps,
        borderColor: CHART_COLORS.danger,
        backgroundColor: `${CHART_COLORS.danger}33`,
        fill: true,
        tension: 0.4,
      },
    ],
  }, {
    plugins: {
      title: {
        display: true,
        text: 'Temperaturentwicklung in Magdeburg',
        color: '#e2e8f0',
      },
    },
  });
}

/**
 * Create accident by year line chart
 */
function createAccidentTrendChart(ctx, accidentsByYear) {
  const years = Object.keys(accidentsByYear).sort();
  const counts = years.map(y => accidentsByYear[y]);

  return createLineChart(ctx, {
    labels: years,
    datasets: [
      {
        label: 'Unfälle gesamt',
        data: counts,
        borderColor: CHART_COLORS.warning,
        backgroundColor: `${CHART_COLORS.warning}33`,
        fill: true,
        tension: 0.4,
      },
    ],
  }, {
    plugins: {
      title: {
        display: true,
        text: 'Unfallentwicklung (2016-2023)',
        color: '#e2e8f0',
      },
    },
  });
}

/**
 * Create accident by type pie chart
 */
function createAccidentTypeChart(ctx, accidentsByType) {
  const labels = Object.keys(accidentsByType);
  const data = Object.values(accidentsByType);

  return createPieChart(ctx, {
    labels: labels,
    datasets: [
      {
        data: data,
        backgroundColor: [
          CHART_COLORS.primary,
          CHART_COLORS.secondary,
          CHART_COLORS.danger,
          CHART_COLORS.warning,
        ],
      },
    ],
  }, {
    plugins: {
      title: {
        display: true,
        text: 'Unfälle nach Verkehrsmittel',
        color: '#e2e8f0',
      },
    },
  });
}

/**
 * Create rent by district bar chart
 */
function createRentDistrictChart(ctx, rentData) {
  const districts = rentData.map(d => d.district);
  const rents = rentData.map(d => d.avg_rent);

  return createBarChart(ctx, {
    labels: districts,
    datasets: [
      {
        label: 'Durchschnittsmiete (€/m²)',
        data: rents,
        backgroundColor: CHART_COLORS.secondary,
      },
    ],
  }, {
    plugins: {
      title: {
        display: true,
        text: 'Mietpreise nach Stadtteil',
        color: '#e2e8f0',
      },
    },
    indexAxis: 'y',  // Horizontal bar chart
  });
}

/**
 * Create tax revenue trend area chart
 */
function createTaxRevenueChart(ctx, revenueTrend) {
  const years = revenueTrend.map(d => d.year);
  const totals = revenueTrend.map(d => d.total);

  return createLineChart(ctx, {
    labels: years,
    datasets: [
      {
        label: 'Steuereinnahmen (Mio. €)',
        data: totals,
        borderColor: CHART_COLORS.primary,
        backgroundColor: `${CHART_COLORS.primary}55`,
        fill: true,
        tension: 0.4,
      },
    ],
  }, {
    plugins: {
      title: {
        display: true,
        text: 'Steuereinnahmen-Entwicklung',
        color: '#e2e8f0',
      },
    },
  });
}

/**
 * Create tree species bar chart
 */
function createTreeSpeciesChart(ctx, speciesData) {
  const species = Object.keys(speciesData).slice(0, 10);
  const counts = Object.values(speciesData).slice(0, 10);

  return createBarChart(ctx, {
    labels: species,
    datasets: [
      {
        label: 'Anzahl Bäume',
        data: counts,
        backgroundColor: CHART_COLORS.teal,
      },
    ],
  }, {
    plugins: {
      title: {
        display: true,
        text: 'Top 10 Baumarten',
        color: '#e2e8f0',
      },
    },
    indexAxis: 'y',
  });
}

// Export functions for global use
window.ChartHelpers = {
  createLineChart,
  createBarChart,
  createPieChart,
  createDoughnutChart,
  createClimateTrendChart,
  createAccidentTrendChart,
  createAccidentTypeChart,
  createRentDistrictChart,
  createTaxRevenueChart,
  createTreeSpeciesChart,
  CHART_COLORS,
};
