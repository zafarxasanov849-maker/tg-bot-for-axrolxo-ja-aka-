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

let trackingLoaded = false;

function switchTab(name) {
  activeTab = name;
  ['umumiy', 'kunlik', 'tracking'].forEach(t => {
    document.getElementById('panel-' + t).style.display = t === name ? '' : 'none';
    document.getElementById('tab-' + t).classList.toggle('active', t === name);
  });
  if (name === 'kunlik'  && !dailyLoaded)    loadDaily();
  if (name === 'tracking' && !trackingLoaded) loadTracking();
}

function reloadActive() {
  if (activeTab === 'umumiy')   { loadUmumiy(); }
  else if (activeTab === 'kunlik') { dailyLoaded = false; loadDaily(); }
  else { trackingLoaded = false; loadTracking(); }
}

// ─── UMUMIY tab ───────────────────────────────────────────────────────────────

async function loadTotals() {
  const res = await fetch('/api/totals');
  const json = await res.json();
  if (!json.ok) return;
  const d = json.data;

  document.getElementById('tot_revenue').textContent = fmtMoney(d.total_revenue);
  document.getElementById('tot_sales').textContent   = fmt(d.total_sales);
  document.getElementById('tot_leads').textContent   = fmt(d.total_leads);
  document.getElementById('tot_spend').textContent   = fmtMoney(d.total_ad_spend);
  document.getElementById('tot_cac').textContent     = fmtMoney(d.blended_cac);
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
  ['tot_revenue','tot_sales','tot_leads','tot_spend','tot_cac','tot_roi','tot_days']
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

// ─── TRACKING tab ─────────────────────────────────────────────────────────────

const STAGE_LABELS = {
  ad_viewed:           '👁 Reklamani ko\'rdi',
  link_clicked:        '🖱 Havolani bosdi',
  video_watched:       '▶️ Video ko\'rdi',
  lead_captured:       '📋 Lead bo\'ldi',
  seminar_registered:  '📝 Seminar ro\'yxat',
  seminar_attended:    '🎓 Keldi',
  contacted:           '💬 Bog\'lanildi',
  deposited:           '💰 Depozit',
  purchased:           '✅ Xarid',
  dropped_off:         '❌ Ketdi',
};

const STAGE_ORDER = [
  'ad_viewed','link_clicked','video_watched','lead_captured',
  'seminar_registered','seminar_attended','contacted','deposited','purchased',
];

let allJourneyRecords = [];
let allLinkStats = [];

async function loadTracking() {
  trackingLoaded = true;
  const [statsRes, journeyRes] = await Promise.all([
    fetch('/api/tracking/stats'),
    fetch('/api/tracking/journey'),
  ]);
  const statsJson   = await statsRes.json();
  const journeyJson = await journeyRes.json();

  if (statsJson.ok)   { allLinkStats = statsJson.data;   renderLinksTable(statsJson.data); }
  if (journeyJson.ok) { allJourneyRecords = journeyJson.data; renderJourneyTable(journeyJson.data); populateLinkFilter(journeyJson.data); }
}

function renderLinksTable(stats) {
  const tbody = document.getElementById('linksBody');
  if (!stats.length) {
    tbody.innerHTML = '<tr><td colspan="7" class="loading">Hali havola yaratilmagan. Yuqoridagi formdan yarating.</td></tr>';
    return;
  }
  const BOT = 'https://t.me/YourBotUsername?start=';
  tbody.innerHTML = stats.map(s => `
    <tr style="cursor:pointer" onclick="showLinkDetail('${s.token}')">
      <td><strong>${s.name || s.token}</strong></td>
      <td>${s.source || '—'}</td>
      <td><code>${s.token}</code></td>
      <td>
        <button class="copy-btn" onclick="event.stopPropagation();copyLink('${s.token}')">📋 Nusxa</button>
      </td>
      <td style="color:#4e8ef7;font-weight:600">${s.total_customers}</td>
      <td style="color:#34d399;font-weight:600">${s.purchased}</td>
      <td style="color:${s.stuck.length ? '#f87171' : '#64748b'};font-weight:600">${s.stuck.length}</td>
    </tr>
  `).join('');
}

function copyLink(token) {
  const text = `https://t.me/YourBotUsername?start=${token}`;
  navigator.clipboard.writeText(text).then(() => alert('Havola nusxalandi:\n' + text));
}

function showLinkDetail(token) {
  const stat = allLinkStats.find(s => s.token === token);
  if (!stat) return;

  // Drop-off chart
  document.getElementById('dropoffSection').style.display = '';
  document.getElementById('dropoffTitle').textContent = `📉 "${stat.name}" — funnel tushish`;
  const counts = STAGE_ORDER.map(s => stat.stages[s] || 0);
  makeChart('dropoffChart', 'bar', STAGE_ORDER.map(s => STAGE_LABELS[s] || s), [{
    label: 'Mijozlar soni',
    data: counts,
    backgroundColor: counts.map((_, i) => `rgba(78,142,247,${1 - i * 0.08})`),
    borderRadius: 6,
  }]);

  // Stuck table
  document.getElementById('stuckSection').style.display = stat.stuck.length ? '' : 'none';
  document.getElementById('stuckTitle').textContent = `⏸ "${stat.name}" — qotib qolganlar (${stat.stuck.length} ta)`;
  document.getElementById('stuckBody').innerHTML = stat.stuck.map(c => `
    <tr>
      <td><strong>${c.customer_id}</strong></td>
      <td>${STAGE_LABELS[c.stage] || c.stage}</td>
      <td>${c.funnel_type || '—'}</td>
      <td>${c.date || '—'}</td>
      <td>${c.notes || '—'}</td>
    </tr>
  `).join('') || '<tr><td colspan="5" class="loading">—</td></tr>';

  document.getElementById('dropoffSection').scrollIntoView({ behavior: 'smooth' });
}

function populateLinkFilter(records) {
  const sel = document.getElementById('journeyLinkFilter');
  const tokens = [...new Set(records.map(r => r.link_token).filter(Boolean))];
  sel.innerHTML = '<option value="">— Barcha havolalar</option>' +
    tokens.map(t => `<option value="${t}">${t}</option>`).join('');
}

function renderJourneyTable(records) {
  const tbody = document.getElementById('journeyBody');
  if (!records.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="loading">Hali yozuv yo\'q</td></tr>';
    return;
  }
  tbody.innerHTML = records.slice(0, 200).map(r => `
    <tr>
      <td>${r.date || '—'}</td>
      <td><strong>${r.customer_id || '—'}</strong></td>
      <td><code>${r.link_token || 'direct'}</code></td>
      <td>${r.funnel_type || '—'}</td>
      <td>${STAGE_LABELS[r.stage] || r.stage || '—'}</td>
      <td>${r.notes || '—'}</td>
    </tr>
  `).join('');
}

function filterJourney() {
  const q    = (document.getElementById('journeySearch').value || '').toLowerCase();
  const link = document.getElementById('journeyLinkFilter').value;
  let filtered = allJourneyRecords;
  if (q)    filtered = filtered.filter(r => (r.customer_id || '').toLowerCase().includes(q));
  if (link) filtered = filtered.filter(r => r.link_token === link);
  renderJourneyTable(filtered);
}

async function createLink() {
  const name   = document.getElementById('lnkName').value.trim();
  const source = document.getElementById('lnkSource').value.trim();
  const notes  = document.getElementById('lnkNotes').value.trim();
  if (!name || !source) { alert('Nom va manba majburiy!'); return; }

  const res  = await fetch('/api/tracking/links', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, source, notes }),
  });
  const json = await res.json();
  if (!json.ok) { alert('Xato: ' + json.error); return; }

  const msg = document.getElementById('linkCreatedMsg');
  const link = `https://t.me/YourBotUsername?start=${json.token}`;
  msg.style.display = '';
  msg.innerHTML = `✅ Yaratildi! Token: <code>${json.token}</code><br>Havola: <code>${link}</code>
    <button class="copy-btn" style="margin-left:8px" onclick="navigator.clipboard.writeText('${link}').then(()=>alert('Nusxalandi!'))">📋 Nusxa</button>`;

  document.getElementById('lnkName').value = '';
  document.getElementById('lnkSource').value = '';
  document.getElementById('lnkNotes').value = '';
  trackingLoaded = false;
  await loadTracking();
}

// ─── Init ─────────────────────────────────────────────────────────────────────

loadUmumiy();
