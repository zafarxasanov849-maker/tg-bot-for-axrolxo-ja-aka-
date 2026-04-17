const CHART_DEFAULTS = {
  color: '#e2e8f0',
  gridColor: 'rgba(255,255,255,0.06)',
  accent: '#F5A623',
  blue: '#4e8ef7',
  green: '#34d399',
  red: '#f87171',
};

let charts = {};
let activeTab = 'umumiy';
let dailyLoaded = false;

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
  const el = document.getElementById(id);
  if (!el) return;
  const ctx = el.getContext('2d');
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

// ─── Tab switching ────────────────────────────────────────────────────────────

function switchTab(name) {
  activeTab = name;
  document.getElementById('panel-umumiy').style.display = name === 'umumiy' ? '' : 'none';
  document.getElementById('panel-kunlik').style.display = name === 'kunlik' ? '' : 'none';
  document.getElementById('tab-umumiy').classList.toggle('active', name === 'umumiy');
  document.getElementById('tab-kunlik').classList.toggle('active', name === 'kunlik');

  if (name === 'kunlik' && !dailyLoaded) {
    loadDaily();
  }
}

function reloadActive() {
  if (activeTab === 'umumiy') {
    loadUmumiy();
  } else {
    dailyLoaded = false;
    loadDaily();
  }
}

// ─── UMUMIY tab ───────────────────────────────────────────────────────────────

async function loadTotals() {
  const res = await fetch('/api/totals');
  const json = await res.json();
  if (!json.ok) return;
  const d = json.data;

  document.getElementById('tot_sales').textContent   = fmt(d.total_sales);
  document.getElementById('tot_revenue').textContent = fmtMoney(d.total_revenue);
  document.getElementById('tot_leads').textContent   = fmt(d.total_leads);
  document.getElementById('tot_spend').textContent   = fmtMoney(d.total_ad_spend);
  document.getElementById('tot_cac').textContent     = fmtMoney(d.blended_cac);
  document.getElementById('tot_ltv').textContent     = fmtMoney(d.avg_ltv);
  document.getElementById('tot_roi').textContent     = d.overall_roi + 'x';
  document.getElementById('tot_roi_sub').textContent =
    `${fmtMoney(d.total_revenue)} / ${fmtMoney(d.total_ad_spend)}`;
  document.getElementById('tot_days').textContent    = d.days_count || '—';
}

async function loadFunnelComparison() {
  const res = await fetch('/api/funnel_comparison');
  const json = await res.json();
  if (!json.ok) return;
  const d = json.data;

  const v = d.vsl;
  document.getElementById('vsl_spend').textContent   = fmtMoney(v.ad_spend);
  document.getElementById('vsl_views').textContent   = fmt(v.page_views);
  document.getElementById('vsl_starts').textContent  = fmt(v.video_start);
  document.getElementById('vsl_cta').textContent     = fmt(v.cta_clicks);
  document.getElementById('vsl_conv').textContent    = v.view_to_cta + '%';
  document.getElementById('vsl_sales').textContent   = fmt(v.sales);
  document.getElementById('vsl_revenue').textContent = fmtMoney(v.revenue);
  document.getElementById('vsl_roi').textContent     = v.roi + 'x';

  const l = d.lead_magnet;
  document.getElementById('lm_spend').textContent        = fmtMoney(l.ad_spend);
  document.getElementById('lm_views').textContent        = fmt(l.lp_views);
  document.getElementById('lm_leads').textContent        = fmt(l.new_leads);
  document.getElementById('lm_lead_conv').textContent    = l.lead_conv + '%';
  document.getElementById('lm_contact').textContent      = fmt(l.contacted);
  document.getElementById('lm_contact_conv').textContent = l.contact_conv + '%';
  document.getElementById('lm_sales').textContent        = fmt(l.sales);
  document.getElementById('lm_revenue').textContent      = fmtMoney(l.revenue);
  document.getElementById('lm_roi').textContent          = l.roi + 'x';

  const s = d.seminar;
  document.getElementById('sem_spend').textContent      = fmtMoney(s.ad_spend);
  document.getElementById('sem_reg').textContent        = fmt(s.registrations);
  document.getElementById('sem_show').textContent       = fmt(s.show_up);
  document.getElementById('sem_show_conv').textContent  = s.show_rate + '%';
  document.getElementById('sem_dep').textContent        = fmt(s.deposits);
  document.getElementById('sem_sales').textContent      = fmt(s.sales);
  document.getElementById('sem_close_conv').textContent = s.close_rate + '%';
  document.getElementById('sem_full').textContent       = fmt(s.full_payments);
  document.getElementById('sem_revenue').textContent    = fmtMoney(s.revenue);
  document.getElementById('sem_roi').textContent        = s.roi + 'x';

  makeChart('funnelRoiChart', 'bar',
    ['VSL', 'Lead Magnet', 'Seminar'],
    [{
      label: 'ROI (x)',
      data: [v.roi, l.roi, s.roi],
      backgroundColor: ['rgba(245,166,35,0.7)', 'rgba(78,142,247,0.7)', 'rgba(52,211,153,0.7)'],
      borderRadius: 6,
    }]
  );
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

async function loadUmumiy() {
  ['tot_sales','tot_revenue','tot_leads','tot_spend','tot_cac','tot_ltv','tot_roi','tot_days']
    .forEach(id => { const el = document.getElementById(id); if (el) el.textContent = '...'; });
  await Promise.all([loadTotals(), loadFunnelComparison(), loadLTV()]);
}

// ─── KUNLIK tab ───────────────────────────────────────────────────────────────

function getDateParams() {
  const from = document.getElementById('dateFrom')?.value;
  const to   = document.getElementById('dateTo')?.value;
  const params = new URLSearchParams();
  if (from) params.set('from', from);
  if (to)   params.set('to', to);
  return params.toString() ? '?' + params.toString() : '';
}

function exportCSV() {
  window.location.href = '/api/export' + getDateParams();
}

async function loadDaily() {
  dailyLoaded = true;
  ['todaySales','todayRevenue','todayLeads','todaySpend','todayCAC','avgLTV','overallROI']
    .forEach(id => { const el = document.getElementById(id); if (el) el.textContent = '...'; });

  const res = await fetch('/api/summary' + getDateParams());
  const json = await res.json();
  if (!json.ok || !json.data.length) return;

  const data = json.data;
  const sf = v => parseFloat(v) || 0;

  const periodSpend   = data.reduce((a, r) => a + sf(r.total_ad_spend), 0);
  const periodLeads   = data.reduce((a, r) => a + sf(r.total_leads), 0);
  const periodSales   = data.reduce((a, r) => a + sf(r.total_sales), 0);
  const periodRevenue = data.reduce((a, r) => a + sf(r.total_revenue), 0);
  const avgCAC        = periodSales ? Math.round(periodSpend / periodSales) : 0;
  const avgLTVval     = data.reduce((a, r) => a + sf(r.avg_ltv), 0) / data.length;
  const roi           = periodSpend ? (periodRevenue / periodSpend).toFixed(2) : 0;

  document.getElementById('todaySales').textContent   = fmt(periodSales);
  document.getElementById('todayRevenue').textContent = fmtMoney(periodRevenue);
  document.getElementById('todayLeads').textContent   = fmt(periodLeads);
  document.getElementById('todaySpend').textContent   = fmtMoney(periodSpend);
  document.getElementById('todayCAC').textContent     = fmtMoney(avgCAC);
  document.getElementById('avgLTV').textContent       = fmtMoney(avgLTVval);
  document.getElementById('overallROI').textContent   = roi + 'x';
  document.getElementById('roiSub').textContent       =
    `${fmtMoney(periodRevenue)} / ${fmtMoney(periodSpend)}`;

  const labels = data.map(r => r.date);

  makeChart('revenueChart', 'line', labels, [{
    label: 'Daromad',
    data: data.map(r => sf(r.total_revenue)),
    borderColor: CHART_DEFAULTS.accent,
    backgroundColor: 'rgba(245,166,35,0.12)',
    tension: 0.4, fill: true, pointRadius: 3,
  }]);

  makeChart('leadsSalesChart', 'bar', labels, [
    { label: 'Leads',    data: data.map(r => sf(r.total_leads)), backgroundColor: 'rgba(78,142,247,0.7)' },
    { label: 'Sotuvlar', data: data.map(r => sf(r.total_sales)), backgroundColor: 'rgba(52,211,153,0.7)' },
  ]);

  makeChart('spendCacChart', 'line', labels, [
    {
      label: 'Ad Spend',
      data: data.map(r => sf(r.total_ad_spend)),
      borderColor: CHART_DEFAULTS.red,
      backgroundColor: 'rgba(248,113,113,0.1)',
      tension: 0.4, fill: true, yAxisID: 'y',
    },
    {
      label: 'CAC',
      data: data.map(r => sf(r.blended_cac)),
      borderColor: CHART_DEFAULTS.blue,
      backgroundColor: 'rgba(78,142,247,0.1)',
      tension: 0.4, fill: true, yAxisID: 'y1',
    },
  ], {
    scales: {
      x:  { ticks: { color: '#8892a4' }, grid: { color: CHART_DEFAULTS.gridColor } },
      y:  { type: 'linear', position: 'left',  ticks: { color: '#8892a4' }, grid: { color: CHART_DEFAULTS.gridColor } },
      y1: { type: 'linear', position: 'right', ticks: { color: '#8892a4' }, grid: { drawOnChartArea: false } },
    },
  });

  makeChart('convChart', 'line', labels, [
    { label: 'VSL %',         data: data.map(r => sf(r.vsl_conv_rate)),     borderColor: CHART_DEFAULTS.accent, tension: 0.4, pointRadius: 3 },
    { label: 'Lead Magnet %', data: data.map(r => sf(r.lm_conv_rate)),      borderColor: CHART_DEFAULTS.blue,   tension: 0.4, pointRadius: 3 },
    { label: 'Seminar %',     data: data.map(r => sf(r.seminar_conv_rate)), borderColor: CHART_DEFAULTS.green,  tension: 0.4, pointRadius: 3 },
  ]);

  const tbody = document.getElementById('dailyBody');
  tbody.innerHTML = [...data].reverse().map(r => `
    <tr>
      <td>${r.date}</td>
      <td>${fmtMoney(r.total_ad_spend)}</td>
      <td>${fmt(r.total_leads)}</td>
      <td>${fmt(r.total_sales)}</td>
      <td>${fmtMoney(r.total_revenue)}</td>
      <td>${fmtMoney(r.blended_cac)}</td>
      <td>${fmtMoney(r.avg_ltv)}</td>
      <td>${r.vsl_conv_rate || 0}%</td>
      <td>${r.lm_conv_rate || 0}%</td>
      <td>${r.seminar_conv_rate || 0}%</td>
    </tr>
  `).join('');
}

// ─── Init ─────────────────────────────────────────────────────────────────────

loadUmumiy();
