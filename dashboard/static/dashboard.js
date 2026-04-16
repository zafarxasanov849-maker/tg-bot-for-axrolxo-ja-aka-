const CHART_DEFAULTS = {
  color: '#e2e8f0',
  gridColor: 'rgba(255,255,255,0.06)',
  accent: '#F5A623',
  blue: '#4e8ef7',
  green: '#34d399',
  red: '#f87171',
};

let charts = {};

function fmt(n) {
  if (!n && n !== 0) return '—';
  const num = parseFloat(n);
  if (isNaN(num)) return '—';
  if (num >= 1_000_000) return (num / 1_000_000).toFixed(1) + 'M';
  if (num >= 1_000) return (num / 1_000).toFixed(0) + 'K';
  return num.toLocaleString();
}

function fmtMoney(n) {
  if (!n && n !== 0) return '—';
  const num = parseFloat(n);
  if (isNaN(num)) return '—';
  return fmt(num) + ' UZS';
}

function destroyChart(id) {
  if (charts[id]) { charts[id].destroy(); delete charts[id]; }
}

function makeChart(id, type, labels, datasets, opts = {}) {
  destroyChart(id);
  const ctx = document.getElementById(id).getContext('2d');
  charts[id] = new Chart(ctx, {
    type,
    data: { labels, datasets },
    options: {
      responsive: true,
      plugins: {
        legend: { labels: { color: CHART_DEFAULTS.color, font: { size: 12 } } },
      },
      scales: type !== 'pie' ? {
        x: { ticks: { color: '#8892a4', font: { size: 11 } }, grid: { color: CHART_DEFAULTS.gridColor } },
        y: { ticks: { color: '#8892a4', font: { size: 11 } }, grid: { color: CHART_DEFAULTS.gridColor } },
      } : {},
      ...opts,
    },
  });
}

function getDateParams() {
  const from = document.getElementById('dateFrom')?.value;
  const to = document.getElementById('dateTo')?.value;
  const params = new URLSearchParams();
  if (from) params.set('from', from);
  if (to) params.set('to', to);
  return params.toString() ? '?' + params.toString() : '';
}

function exportCSV() {
  const params = getDateParams();
  window.location.href = '/api/export' + params;
}

async function loadSummary() {
  const res = await fetch('/api/summary' + getDateParams());
  const json = await res.json();
  if (!json.ok || !json.data.length) return;

  const data = json.data;
  const today = data[data.length - 1];

  document.getElementById('todaySales').textContent = fmt(today.total_sales);
  document.getElementById('todayRevenue').textContent = fmtMoney(today.total_revenue);
  document.getElementById('todayLeads').textContent = fmt(today.total_leads);
  document.getElementById('todaySpend').textContent = fmtMoney(today.total_ad_spend);
  document.getElementById('todayCAC').textContent = fmtMoney(today.blended_cac);
  document.getElementById('avgLTV').textContent = fmtMoney(today.avg_ltv);

  const labels = data.map(r => r.date);

  // Revenue chart
  makeChart('revenueChart', 'line', labels, [{
    label: 'Daromad',
    data: data.map(r => parseFloat(r.total_revenue) || 0),
    borderColor: CHART_DEFAULTS.accent,
    backgroundColor: 'rgba(245,166,35,0.12)',
    tension: 0.4, fill: true, pointRadius: 3,
  }]);

  // Leads & Sales
  makeChart('leadsSalesChart', 'bar', labels, [
    {
      label: 'Leads',
      data: data.map(r => parseFloat(r.total_leads) || 0),
      backgroundColor: 'rgba(78,142,247,0.7)',
    },
    {
      label: 'Sotuvlar',
      data: data.map(r => parseFloat(r.total_sales) || 0),
      backgroundColor: 'rgba(52,211,153,0.7)',
    },
  ]);

  // Spend vs CAC
  makeChart('spendCacChart', 'line', labels, [
    {
      label: 'Ad Spend',
      data: data.map(r => parseFloat(r.total_ad_spend) || 0),
      borderColor: CHART_DEFAULTS.red,
      backgroundColor: 'rgba(248,113,113,0.1)',
      tension: 0.4, fill: true, yAxisID: 'y',
    },
    {
      label: 'CAC',
      data: data.map(r => parseFloat(r.blended_cac) || 0),
      borderColor: CHART_DEFAULTS.blue,
      backgroundColor: 'rgba(78,142,247,0.1)',
      tension: 0.4, fill: true, yAxisID: 'y1',
    },
  ], {
    scales: {
      x: { ticks: { color: '#8892a4' }, grid: { color: CHART_DEFAULTS.gridColor } },
      y: { type: 'linear', position: 'left', ticks: { color: '#8892a4' }, grid: { color: CHART_DEFAULTS.gridColor } },
      y1: { type: 'linear', position: 'right', ticks: { color: '#8892a4' }, grid: { drawOnChartArea: false } },
    },
  });

  // Conversion rates
  makeChart('convChart', 'line', labels, [
    {
      label: 'VSL %',
      data: data.map(r => parseFloat(r.vsl_conv_rate) || 0),
      borderColor: CHART_DEFAULTS.accent,
      tension: 0.4, pointRadius: 3,
    },
    {
      label: 'Lead Magnet %',
      data: data.map(r => parseFloat(r.lm_conv_rate) || 0),
      borderColor: CHART_DEFAULTS.blue,
      tension: 0.4, pointRadius: 3,
    },
    {
      label: 'Seminar %',
      data: data.map(r => parseFloat(r.seminar_conv_rate) || 0),
      borderColor: CHART_DEFAULTS.green,
      tension: 0.4, pointRadius: 3,
    },
  ]);
}

async function loadLTV() {
  const res = await fetch('/api/ltv');
  const json = await res.json();
  const tbody = document.getElementById('ltvBody');
  if (!json.ok || !json.data.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="loading">Ma\'lumot yo\'q</td></tr>';
    return;
  }
  tbody.innerHTML = json.data.map(r => `
    <tr>
      <td>${r.customer_id || '—'}</td>
      <td>${r.first_funnel || '—'}</td>
      <td>${r.first_purchase_date || '—'}</td>
      <td>${fmtMoney(r.total_revenue)}</td>
      <td>${r.purchase_count || '—'}</td>
      <td style="color:#F5A623;font-weight:600">${fmtMoney(r.ltv)}</td>
    </tr>
  `).join('');
}

async function loadAll() {
  document.getElementById('todaySales').textContent = '...';
  document.getElementById('todayRevenue').textContent = '...';
  document.getElementById('todayLeads').textContent = '...';
  document.getElementById('todaySpend').textContent = '...';
  document.getElementById('todayCAC').textContent = '...';
  document.getElementById('avgLTV').textContent = '...';
  await Promise.all([loadSummary(), loadLTV()]);
}

loadAll();
