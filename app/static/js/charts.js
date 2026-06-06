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

// Get current theme colors
function getThemeColors() {
  const isDark = document.documentElement.getAttribute('data-theme') !== 'light';
  return {
    textColor: isDark ? '#e2e8f0' : '#1a202c',
    mutedColor: isDark ? '#8892a4' : '#4a5568',
    gridColor: isDark ? '#2a2f45' : '#e2e8f0',
  };
}

function getChartDefaults() {
  const colors = getThemeColors();
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: {
          color: colors.textColor,
          font: {
            size: 12,
          },
        },
      },
    },
    scales: {
      x: {
        ticks: {
          color: colors.mutedColor,
        },
        grid: {
          color: colors.gridColor,
        },
      },
      y: {
        ticks: {
          color: colors.mutedColor,
        },
        grid: {
          color: colors.gridColor,
        },
      },
    },
  };
}

const CHART_DEFAULTS = getChartDefaults();

/**
 * Create a line chart
 */
function createLineChart(ctx, data, options = {}) {
  return new Chart(ctx, {
    type: 'line',
    data: data,
    options: {
      ...getChartDefaults(),
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
      ...getChartDefaults(),
      ...options,
    },
  });
}

/**
 * Create a pie chart
 */
function createPieChart(ctx, data, options = {}) {
  const defaults = { ...getChartDefaults() };
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
  const defaults = { ...getChartDefaults() };
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
  const colors = getThemeColors();

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
        color: colors.textColor,
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
  const colors = getThemeColors();

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
        color: colors.textColor,
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
  const colors = getThemeColors();

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
        color: colors.textColor,
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
  const colors = getThemeColors();

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
        color: colors.textColor,
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
  const colors = getThemeColors();

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
        color: colors.textColor,
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
  const colors = getThemeColors();

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
        color: colors.textColor,
      },
    },
    indexAxis: 'y',
  });
}

/**
 * Create transit passengers line chart (KISS-MD)
 */
function createTransitPassengersChart(ctx, passengersData) {
  const years = passengersData.map(d => d.year);
  const passengers = passengersData.map(d => d.passengers);
  const colors = getThemeColors();

  return createLineChart(ctx, {
    labels: years,
    datasets: [
      {
        label: 'Fahrgäste (Millionen)',
        data: passengers.map(p => p / 1000000),  // Convert to millions
        borderColor: CHART_COLORS.info,
        backgroundColor: `${CHART_COLORS.info}33`,
        fill: true,
        tension: 0.4,
      },
    ],
  }, {
    plugins: {
      title: {
        display: true,
        text: 'Fahrgastzahlen MVB',
        color: colors.textColor,
      },
    },
  });
}

/**
 * Create vehicle fleet line chart (KISS-MD)
 */
function createVehicleFleetChart(ctx, vehicleData) {
  const years = vehicleData.map(d => d.year);
  const vehicles = vehicleData.map(d => d.total_vehicles);
  const colors = getThemeColors();

  return createLineChart(ctx, {
    labels: years,
    datasets: [
      {
        label: 'KFZ-Bestand',
        data: vehicles,
        borderColor: CHART_COLORS.purple,
        backgroundColor: `${CHART_COLORS.purple}33`,
        fill: true,
        tension: 0.4,
      },
    ],
  }, {
    plugins: {
      title: {
        display: true,
        text: 'Kraftfahrzeugbestand in Magdeburg',
        color: colors.textColor,
      },
    },
  });
}

/**
 * Create population pyramid chart (Demographics)
 */
function createPopulationPyramid(ctx, ageGenderData) {
  const colors = getThemeColors();

  // Filter to get 5-year age groups for cleaner visualization
  const ageGroups = [];
  for (let i = 0; i < 100; i += 5) {
    const groupData = ageGenderData.filter(d => {
      const age = parseInt(d.age);
      return age >= i && age < i + 5;
    });

    if (groupData.length > 0) {
      const male = groupData.reduce((sum, d) => sum + (d.male || 0), 0);
      const female = groupData.reduce((sum, d) => sum + (d.female || 0), 0);
      ageGroups.push({
        label: `${i}-${i+4}`,
        male: -male,  // Negative for left side
        female: female
      });
    }
  }

  // Calculate max value for symmetric scale
  const maxMale = Math.max(...ageGroups.map(g => Math.abs(g.male)));
  const maxFemale = Math.max(...ageGroups.map(g => g.female));
  const maxValue = Math.max(maxMale, maxFemale);
  const roundedMax = Math.ceil(maxValue / 1000) * 1000; // Round up to nearest 1000

  return new Chart(ctx, {
    type: 'bar',
    data: {
      labels: ageGroups.map(g => g.label),
      datasets: [
        {
          label: 'Männer',
          data: ageGroups.map(g => g.male),
          backgroundColor: CHART_COLORS.primary,
          borderWidth: 0,
        },
        {
          label: 'Frauen',
          data: ageGroups.map(g => g.female),
          backgroundColor: CHART_COLORS.secondary,
          borderWidth: 0,
        },
      ],
    },
    options: {
      ...getChartDefaults(),
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        title: {
          display: true,
          text: 'Bevölkerungspyramide nach Alter und Geschlecht',
          color: colors.textColor,
        },
        legend: {
          labels: {
            color: colors.textColor,
          },
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              return context.dataset.label + ': ' + Math.abs(context.parsed.x).toLocaleString('de-DE');
            }
          }
        }
      },
      scales: {
        x: {
          min: -roundedMax,
          max: roundedMax,
          ticks: {
            color: colors.mutedColor,
            callback: function(value) {
              return Math.abs(value).toLocaleString('de-DE');
            }
          },
          grid: {
            color: colors.gridColor,
            drawTicks: true,
          },
        },
        y: {
          ticks: {
            color: colors.mutedColor,
            font: {
              size: 11,
            }
          },
          grid: {
            display: false,
          },
        },
      },
    },
  });
}

/**
 * Create dependency ratio trend chart (Demographics)
 */
function createDependencyRatioChart(ctx, ratioData) {
  const years = ratioData.map(d => d.year);
  const colors = getThemeColors();

  return createLineChart(ctx, {
    labels: years,
    datasets: [
      {
        label: 'Jugendquotient (%)',
        data: ratioData.map(d => d.youth_ratio),
        borderColor: CHART_COLORS.info,
        backgroundColor: `${CHART_COLORS.info}33`,
        fill: false,
        tension: 0.4,
      },
      {
        label: 'Altenquotient (%)',
        data: ratioData.map(d => d.elderly_ratio),
        borderColor: CHART_COLORS.warning,
        backgroundColor: `${CHART_COLORS.warning}33`,
        fill: false,
        tension: 0.4,
      },
    ],
  }, {
    plugins: {
      title: {
        display: true,
        text: 'Demografische Abhängigkeitsquoten',
        color: colors.textColor,
      },
    },
  });
}

/**
 * Create foreign residents trend chart (Demographics)
 */
function createForeignResidentsChart(ctx, foreignData) {
  const years = foreignData.map(d => d.year);
  const totals = foreignData.map(d => d.total_foreign);
  const colors = getThemeColors();

  return createLineChart(ctx, {
    labels: years,
    datasets: [
      {
        label: 'Ausländische Einwohner',
        data: totals,
        borderColor: CHART_COLORS.teal,
        backgroundColor: `${CHART_COLORS.teal}33`,
        fill: true,
        tension: 0.4,
      },
    ],
  }, {
    plugins: {
      title: {
        display: true,
        text: 'Entwicklung der ausländischen Bevölkerung',
        color: colors.textColor,
      },
    },
  });
}

/**
 * Create construction completions chart (Housing)
 */
function createConstructionChart(ctx, constructionData) {
  const years = constructionData.map(d => d.year);
  const buildings = constructionData.map(d => d.total_buildings);
  const colors = getThemeColors();

  return new Chart(ctx, {
    type: 'bar',
    data: {
      labels: years,
      datasets: [
        {
          label: 'Fertiggestellte Gebäude',
          data: buildings,
          backgroundColor: CHART_COLORS.warning,
          borderWidth: 0,
        },
      ],
    },
    options: {
      ...getChartDefaults(),
      plugins: {
        title: {
          display: true,
          text: 'Baufertigstellungen nach Jahr',
          color: colors.textColor,
        },
        legend: {
          labels: {
            color: colors.textColor,
          },
        },
      },
      scales: {
        x: {
          ticks: { color: colors.mutedColor },
          grid: { color: colors.gridColor },
        },
        y: {
          ticks: { color: colors.mutedColor },
          grid: { color: colors.gridColor },
          beginAtZero: true,
        },
      },
    },
  });
}

/**
 * Create employment trend chart (Labor Market)
 */
function createEmploymentChart(ctx, employmentData) {
  const years = employmentData.map(d => d.year);
  const employed = employmentData.map(d => d.total_employed);
  const colors = getThemeColors();

  return createLineChart(ctx, {
    labels: years,
    datasets: [
      {
        label: 'Beschäftigte',
        data: employed,
        borderColor: CHART_COLORS.primary,
        backgroundColor: `${CHART_COLORS.primary}33`,
        fill: true,
        tension: 0.4,
      },
    ],
  }, {
    plugins: {
      title: {
        display: true,
        text: 'Sozialversicherungspflichtig Beschäftigte am Arbeitsort',
        color: colors.textColor,
      },
    },
  });
}

/**
 * Create schools by type bar chart (Education - Phase 2)
 */
function createSchoolsByTypeChart(ctx, schoolsByType) {
  const types = Object.keys(schoolsByType);
  const counts = Object.values(schoolsByType);
  const colors = getThemeColors();

  return createBarChart(ctx, {
    labels: types,
    datasets: [
      {
        label: 'Anzahl Schulen',
        data: counts,
        backgroundColor: CHART_COLORS.info,
      },
    ],
  }, {
    plugins: {
      title: {
        display: true,
        text: 'Schulen nach Schultyp (2023)',
        color: colors.textColor,
      },
    },
    indexAxis: 'y',
  });
}

/**
 * Create tourism arrivals trend line chart (Tourism - Phase 2)
 */
function createTourismArrivalsChart(ctx, arrivalsData) {
  const years = arrivalsData.map(d => d.year);
  const colors = getThemeColors();

  return createLineChart(ctx, {
    labels: years,
    datasets: [
      {
        label: 'Gesamt',
        data: arrivalsData.map(d => d.total_arrivals),
        borderColor: CHART_COLORS.primary,
        backgroundColor: `${CHART_COLORS.primary}33`,
        fill: false,
        tension: 0.4,
      },
      {
        label: 'Inland',
        data: arrivalsData.map(d => d.domestic_arrivals),
        borderColor: CHART_COLORS.secondary,
        backgroundColor: `${CHART_COLORS.secondary}33`,
        fill: false,
        tension: 0.4,
      },
      {
        label: 'Ausland',
        data: arrivalsData.map(d => d.foreign_arrivals),
        borderColor: CHART_COLORS.warning,
        backgroundColor: `${CHART_COLORS.warning}33`,
        fill: false,
        tension: 0.4,
      },
    ],
  }, {
    plugins: {
      title: {
        display: true,
        text: 'Gästeankünfte in Magdeburg',
        color: colors.textColor,
      },
    },
  });
}

/**
 * Create overnight stays trend line chart (Tourism - Phase 2)
 */
function createOvernightStaysChart(ctx, overnightData) {
  const years = overnightData.map(d => d.year);
  const colors = getThemeColors();

  return createLineChart(ctx, {
    labels: years,
    datasets: [
      {
        label: 'Gesamt',
        data: overnightData.map(d => d.total_nights),
        borderColor: CHART_COLORS.teal,
        backgroundColor: `${CHART_COLORS.teal}33`,
        fill: true,
        tension: 0.4,
      },
      {
        label: 'Inland',
        data: overnightData.map(d => d.domestic_nights),
        borderColor: CHART_COLORS.secondary,
        backgroundColor: `${CHART_COLORS.secondary}33`,
        fill: false,
        tension: 0.4,
      },
      {
        label: 'Ausland',
        data: overnightData.map(d => d.foreign_nights),
        borderColor: CHART_COLORS.purple,
        backgroundColor: `${CHART_COLORS.purple}33`,
        fill: false,
        tension: 0.4,
      },
    ],
  }, {
    plugins: {
      title: {
        display: true,
        text: 'Übernachtungen in Magdeburg',
        color: colors.textColor,
      },
    },
  });
}

/**
 * Create energy consumption stacked area chart (Stabstelle Klima)
 */
function createEnergyConsumptionChart(ctx, energyData) {
  const years = energyData.map(d => d.year);
  const colors = getThemeColors();

  return new Chart(ctx, {
    type: 'line',
    data: {
      labels: years,
      datasets: [
        {
          label: 'Haushalte',
          data: energyData.map(d => d.haushalte / 1000),  // Convert to GWh
          borderColor: CHART_COLORS.primary,
          backgroundColor: `${CHART_COLORS.primary}99`,
          fill: true,
          tension: 0.4,
        },
        {
          label: 'Industrie',
          data: energyData.map(d => d.industrie / 1000),
          borderColor: CHART_COLORS.warning,
          backgroundColor: `${CHART_COLORS.warning}99`,
          fill: true,
          tension: 0.4,
        },
        {
          label: 'GHD',
          data: energyData.map(d => d.ghd / 1000),
          borderColor: CHART_COLORS.secondary,
          backgroundColor: `${CHART_COLORS.secondary}99`,
          fill: true,
          tension: 0.4,
        },
        {
          label: 'Verkehr',
          data: energyData.map(d => d.verkehr / 1000),
          borderColor: CHART_COLORS.info,
          backgroundColor: `${CHART_COLORS.info}99`,
          fill: true,
          tension: 0.4,
        },
      ],
    },
    options: {
      ...getChartDefaults(),
      plugins: {
        title: {
          display: true,
          text: 'Endenergieverbrauch nach Sektoren (GWh)',
          color: colors.textColor,
        },
        legend: {
          labels: {
            color: colors.textColor,
          },
        },
      },
      scales: {
        x: {
          ticks: { color: colors.mutedColor },
          grid: { color: colors.gridColor },
        },
        y: {
          stacked: true,
          ticks: { color: colors.mutedColor },
          grid: { color: colors.gridColor },
        },
      },
    },
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
  createTransitPassengersChart,
  createVehicleFleetChart,
  createEnergyConsumptionChart,
  createPopulationPyramid,
  createDependencyRatioChart,
  createForeignResidentsChart,
  createEmploymentChart,
  createConstructionChart,
  createSchoolsByTypeChart,
  createTourismArrivalsChart,
  createOvernightStaysChart,
  CHART_COLORS,
};
