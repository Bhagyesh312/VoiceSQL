/**
 * chart-renderer.js — Chart.js wrapper for query result visualization
 */

const ChartRenderer = (() => {
  let _instance = null;

  const COLORS_BG = [
    "rgba(245,166,35,0.7)","rgba(0,212,170,0.7)","rgba(99,179,237,0.7)",
    "rgba(246,135,179,0.7)","rgba(154,117,247,0.7)","rgba(255,107,107,0.7)",
    "rgba(72,199,142,0.7)","rgba(255,190,76,0.7)",
  ];
  const COLORS_BORDER = COLORS_BG.map(c => c.replace("0.7","1"));

  function render(canvasId, type, columns, rows) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    // Destroy previous instance
    if (_instance) { _instance.destroy(); _instance = null; }

    const labels = rows.map(r => String(r[0]));
    const values = rows.map(r => parseFloat(r[1]) || 0);

    const cfg = type === "pie"
      ? _pieConfig(labels, values)
      : type === "line"
      ? _lineConfig(labels, values, columns[1] || "Value")
      : _barConfig(labels, values, columns[1] || "Value");

    _instance = new Chart(canvas, cfg);
  }

  function _barConfig(labels, values, label) {
    return {
      type: "bar",
      data: {
        labels,
        datasets: [{
          label,
          data: values,
          backgroundColor: COLORS_BG,
          borderColor: COLORS_BORDER,
          borderWidth: 1.5,
          borderRadius: 4,
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: true,
        plugins: {
          legend: { labels: { color: "#8888a8", font: { family: "DM Mono" } } },
          tooltip: { bodyFont: { family: "DM Mono" }, titleFont: { family: "Syne" } }
        },
        scales: {
          x: { ticks: { color: "#8888a8", font: { family: "DM Mono", size: 11 } }, grid: { color: "#2a2a3a" } },
          y: { ticks: { color: "#8888a8", font: { family: "DM Mono", size: 11 } }, grid: { color: "#2a2a3a" } }
        }
      }
    };
  }

  function _lineConfig(labels, values, label) {
    return {
      type: "line",
      data: {
        labels,
        datasets: [{
          label,
          data: values,
          borderColor: COLORS_BORDER[0],
          backgroundColor: "rgba(99,102,241,0.1)",
          borderWidth: 2,
          pointBackgroundColor: COLORS_BORDER[0],
          pointRadius: 4,
          tension: 0.3,
          fill: true,
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: true,
        plugins: {
          legend: { labels: { color: "#8888a8", font: { family: "DM Mono" } } },
          tooltip: { bodyFont: { family: "DM Mono" }, titleFont: { family: "Syne" } }
        },
        scales: {
          x: { ticks: { color: "#8888a8", font: { family: "DM Mono", size: 11 } }, grid: { color: "#2a2a3a" } },
          y: { ticks: { color: "#8888a8", font: { family: "DM Mono", size: 11 } }, grid: { color: "#2a2a3a" } }
        }
      }
    };
  }

  function _pieConfig(labels, values) {
    return {
      type: "pie",
      data: {
        labels,
        datasets: [{ data: values, backgroundColor: COLORS_BG, borderColor: "#0a0a0f", borderWidth: 2 }]
      },
      options: {
        responsive: true, maintainAspectRatio: true,
        plugins: {
          legend: { position: "right", labels: { color: "#8888a8", font: { family: "DM Mono" }, boxWidth: 12 } },
          tooltip: { bodyFont: { family: "DM Mono" }, titleFont: { family: "Syne" } }
        }
      }
    };
  }

  function destroy() {
    if (_instance) { _instance.destroy(); _instance = null; }
  }

  return { render, destroy };
})();
