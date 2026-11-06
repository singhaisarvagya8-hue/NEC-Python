/* ==========================================================================
   FinTrack Pro - Dynamic Chart.js Analytics Integrations
   ========================================================================== */

let categoryChartInstance = null;
let trendChartInstance = null;
let dailyChartInstance = null;

function getChartThemeColors() {
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  return {
    textColor: isDark ? '#9ca3af' : '#475569',
    gridColor: isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.06)',
    cardBg: isDark ? '#111827' : '#ffffff',
  };
}

const PALETTE = [
  '#6366f1', '#ec4899', '#f59e0b', '#10b981', '#06b6d4', 
  '#8b5cf6', '#ef4444', '#14b8a6', '#f97316', '#84cc16'
];

/**
 * Render or update Category Spending Breakdown Donut Chart
 */
function renderCategoryChart(breakdown, currencySymbol) {
  const canvas = document.getElementById('categoryChart');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  const theme = getChartThemeColors();

  if (categoryChartInstance) {
    categoryChartInstance.destroy();
  }

  if (!breakdown || breakdown.length === 0) {
    categoryChartInstance = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['No Expenses Recorded'],
        datasets: [{
          data: [1],
          backgroundColor: [theme.gridColor],
          borderWidth: 0,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { enabled: false }
        }
      }
    });
    return;
  }

  const labels = breakdown.map(item => item.category);
  const data = breakdown.map(item => item.total);
  const bgColors = breakdown.map((_, i) => PALETTE[i % PALETTE.length]);

  categoryChartInstance = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: data,
        backgroundColor: bgColors,
        borderWidth: 2,
        borderColor: theme.cardBg,
        hoverOffset: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '72%',
      plugins: {
        legend: {
          position: 'right',
          labels: {
            color: theme.textColor,
            boxWidth: 12,
            boxHeight: 12,
            font: { size: 12, weight: '500' },
            padding: 12
          }
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              const val = context.parsed;
              const total = context.dataset.data.reduce((a, b) => a + b, 0);
              const pct = total > 0 ? ((val / total) * 100).toFixed(1) : 0;
              return ` ${context.label}: ${currencySymbol}${val.toFixed(2)} (${pct}%)`;
            }
          }
        }
      }
    }
  });
}

/**
 * Render or update 6-Month Income vs Expense Bar Chart
 */
function renderTrendChart(trends, currencySymbol) {
  const canvas = document.getElementById('trendChart');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  const theme = getChartThemeColors();

  if (trendChartInstance) {
    trendChartInstance.destroy();
  }

  if (!trends || trends.length === 0) return;

  const labels = trends.map(t => {
    const [year, month] = t.month.split('-');
    const dateObj = new Date(year, parseInt(month) - 1, 1);
    return dateObj.toLocaleString('default', { month: 'short' });
  });

  const incomeData = trends.map(t => t.income);
  const expenseData = trends.map(t => t.expense);

  trendChartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Income',
          data: incomeData,
          backgroundColor: '#10b981',
          borderRadius: 6,
          barPercentage: 0.6,
          categoryPercentage: 0.65,
        },
        {
          label: 'Expenses',
          data: expenseData,
          backgroundColor: '#f43f5e',
          borderRadius: 6,
          barPercentage: 0.6,
          categoryPercentage: 0.65,
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: theme.textColor, font: { size: 11 } }
        },
        y: {
          grid: { color: theme.gridColor },
          ticks: {
            color: theme.textColor,
            font: { size: 11 },
            callback: value => `${currencySymbol}${value}`
          }
        }
      },
      plugins: {
        legend: {
          position: 'top',
          labels: {
            color: theme.textColor,
            boxWidth: 12,
            font: { size: 12 }
          }
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              return ` ${context.dataset.label}: ${currencySymbol}${context.parsed.y.toFixed(2)}`;
            }
          }
        }
      }
    }
  });
}

/**
 * Render or update Daily Spending Velocity Line Chart
 */
function renderDailyChart(dailyData, currencySymbol) {
  const canvas = document.getElementById('dailyChart');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  const theme = getChartThemeColors();

  if (dailyChartInstance) {
    dailyChartInstance.destroy();
  }

  if (!dailyData || dailyData.length === 0) return;

  const labels = dailyData.map(d => {
    const parts = d.date.split('-');
    return `${parts[1]}/${parts[2]}`;
  });
  const data = dailyData.map(d => d.amount);

  dailyChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: 'Daily Expenses',
        data: data,
        borderColor: '#6366f1',
        backgroundColor: 'rgba(99, 102, 241, 0.12)',
        tension: 0.35,
        fill: true,
        pointBackgroundColor: '#6366f1',
        pointRadius: 3,
        pointHoverRadius: 6,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: theme.textColor, font: { size: 10 } }
        },
        y: {
          grid: { color: theme.gridColor },
          ticks: {
            color: theme.textColor,
            font: { size: 11 },
            callback: value => `${currencySymbol}${value}`
          }
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: function(context) {
              return ` Spent: ${currencySymbol}${context.parsed.y.toFixed(2)}`;
            }
          }
        }
      }
    }
  });
}

// Global update helper for theme toggling
window.refreshAllCharts = function(overviewData, currencySymbol) {
  if (!overviewData) return;
  renderCategoryChart(overviewData.category_breakdown, currencySymbol);
  renderTrendChart(overviewData.monthly_trends, currencySymbol);
  renderDailyChart(overviewData.daily_spending, currencySymbol);
};
