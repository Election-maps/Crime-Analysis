// State Management
const state = {
  filters: {
    sub_div: 'All',
    ps: 'All',
    head: 'All',
    year: 'All',
    month: 'All',
    gravity: 'All'
  },
  caseQuery: '',
  casePage: 1,
  casePageSize: 25,
  charts: {}
};

// DOM Ready
document.addEventListener('DOMContentLoaded', async () => {
  setupTabs();
  setupEventListeners();
  await loadFilterOptions();
  await refreshAll();
});

// Setup Navigation Tabs
function setupTabs() {
  const tabs = document.querySelectorAll('.nav-tab');
  const panes = document.querySelectorAll('.tab-pane');

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const target = tab.dataset.tab;

      tabs.forEach(t => {
        t.classList.remove('border-blue-500', 'text-blue-400');
        t.classList.add('border-transparent', 'text-slate-400');
      });
      tab.classList.add('border-blue-500', 'text-blue-400');
      tab.classList.remove('border-transparent', 'text-slate-400');

      panes.forEach(pane => {
        if (pane.id === target) {
          pane.classList.remove('hidden');
        } else {
          pane.classList.add('hidden');
        }
      });

      // Lazy load tab-specific data
      if (target === 'tab-stations') loadStationData();
      if (target === 'tab-crimes') loadCrimeHeadData();
      if (target === 'tab-pendency') loadPendencyData();
      if (target === 'tab-explorer') loadCaseData();
    });
  });
}

// Setup Event Listeners
function setupEventListeners() {
  const filterIds = ['subDivSelect', 'psSelect', 'headSelect', 'yearSelect', 'monthSelect', 'gravitySelect'];
  
  filterIds.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('change', () => {
        state.filters.sub_div = document.getElementById('subDivSelect').value;
        state.filters.ps = document.getElementById('psSelect').value;
        state.filters.head = document.getElementById('headSelect').value;
        state.filters.year = document.getElementById('yearSelect').value;
        state.filters.month = document.getElementById('monthSelect').value;
        state.filters.gravity = document.getElementById('gravitySelect').value;
        state.casePage = 1;
        refreshAll();
      });
    }
  });

  document.getElementById('resetFiltersBtn').addEventListener('click', () => {
    document.getElementById('subDivSelect').value = 'All';
    document.getElementById('psSelect').value = 'All';
    document.getElementById('headSelect').value = 'All';
    document.getElementById('yearSelect').value = 'All';
    document.getElementById('monthSelect').value = 'All';
    document.getElementById('gravitySelect').value = 'All';
    state.filters = { sub_div: 'All', ps: 'All', head: 'All', year: 'All', month: 'All', gravity: 'All' };
    state.casePage = 1;
    refreshAll();
  });

  document.getElementById('refreshBtn').addEventListener('click', refreshAll);

  // Station search in table
  document.getElementById('stationSearchInput').addEventListener('input', (e) => {
    const val = e.target.value.toLowerCase();
    const rows = document.querySelectorAll('#stationTableBody tr');
    rows.forEach(r => {
      const text = r.innerText.toLowerCase();
      r.style.display = text.includes(val) ? '' : 'none';
    });
  });

  // Case search input with debounce
  let searchTimeout = null;
  document.getElementById('caseSearchInput').addEventListener('input', (e) => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      state.caseQuery = e.target.value;
      state.casePage = 1;
      loadCaseData();
    }, 300);
  });

  document.getElementById('pageSizeSelect').addEventListener('change', (e) => {
    state.casePageSize = parseInt(e.target.value);
    state.casePage = 1;
    loadCaseData();
  });

  document.getElementById('prevPageBtn').addEventListener('click', () => {
    if (state.casePage > 1) {
      state.casePage--;
      loadCaseData();
    }
  });

  document.getElementById('nextPageBtn').addEventListener('click', () => {
    state.casePage++;
    loadCaseData();
  });

  // Modal close handlers
  document.getElementById('closeModalBtn').addEventListener('click', closeModal);
  document.getElementById('modalOkBtn').addEventListener('click', closeModal);
  document.getElementById('caseModal').addEventListener('click', (e) => {
    if (e.target.id === 'caseModal') closeModal();
  });

  // Export CSV
  document.getElementById('exportBtn').addEventListener('click', exportSummaryCSV);
}

// Build Query String from Filters
function getQueryString(extra = {}) {
  const params = new URLSearchParams();
  if (state.filters.sub_div !== 'All') params.append('sub_div', state.filters.sub_div);
  if (state.filters.ps !== 'All') params.append('ps', state.filters.ps);
  if (state.filters.head !== 'All') params.append('head', state.filters.head);
  if (state.filters.year !== 'All') params.append('year', state.filters.year);
  if (state.filters.month !== 'All') params.append('month', state.filters.month);
  if (state.filters.gravity !== 'All') params.append('gravity', state.filters.gravity);

  for (const [k, v] of Object.entries(extra)) {
    if (v !== undefined && v !== null && v !== '') params.append(k, v);
  }
  return params.toString();
}

// Load Dropdown Options
async function loadFilterOptions() {
  try {
    const res = await fetch('/api/filters');
    const data = await res.json();

    populateSelect('subDivSelect', data.sub_divisions);
    populateSelect('psSelect', data.police_stations);
    populateSelect('headSelect', data.crime_heads);
    populateSelect('yearSelect', data.years);
  } catch (err) {
    console.error('Error loading filters:', err);
  }
}

function populateSelect(elemId, items) {
  const select = document.getElementById(elemId);
  const currentVal = select.value;
  // Keep first option
  select.innerHTML = select.options[0].outerHTML;
  items.forEach(item => {
    const opt = document.createElement('option');
    opt.value = item;
    opt.textContent = item;
    select.appendChild(opt);
  });
  select.value = currentVal;
}

// Global Refresh
async function refreshAll() {
  await loadKPIs();
  await loadTrends();
  await loadOverviewCrimeTable();

  // If on active tab, load its data
  const activeTab = document.querySelector('.nav-tab.border-blue-500').dataset.tab;
  if (activeTab === 'tab-stations') loadStationData();
  if (activeTab === 'tab-crimes') loadCrimeHeadData();
  if (activeTab === 'tab-pendency') loadPendencyData();
  if (activeTab === 'tab-explorer') loadCaseData();
}

// Load KPIs
async function loadKPIs() {
  try {
    const res = await fetch(`/api/kpis?${getQueryString()}`);
    const data = await res.json();

    document.getElementById('kpi-total').textContent = (data.total || 0).toLocaleString();
    document.getElementById('kpi-grave').textContent = (data.grave || 0).toLocaleString();
    document.getElementById('kpi-non-grave').textContent = (data.non_grave || 0).toLocaleString();
    document.getElementById('kpi-ui').textContent = (data.ui || 0).toLocaleString();
    document.getElementById('kpi-long-pending').textContent = (data.long_pending || 0).toLocaleString();
    document.getElementById('kpi-cs').textContent = (data.chargesheeted || 0).toLocaleString();
    document.getElementById('kpi-cs-rate').textContent = `${data.cs_rate}%`;
    document.getElementById('kpi-p-disp').textContent = (data.police_disposed || 0).toLocaleString();
    document.getElementById('kpi-c-disp').textContent = (data.court_disposed || 0).toLocaleString();
    document.getElementById('kpi-disp-rate').textContent = `${data.disp_rate}%`;

    updateStageDonut(data);
  } catch (err) {
    console.error('Error loading KPIs:', err);
  }
}

// Render Stage Donut Chart
function updateStageDonut(kpis) {
  const ctx = document.getElementById('stageDonutChart').getContext('2d');
  if (state.charts.donut) state.charts.donut.destroy();

  const labels = ['Under Investigation', 'Charge-Sheeted', 'Police Disposed', 'Court Disposed'];
  const values = [kpis.ui, kpis.chargesheeted, kpis.police_disposed, kpis.court_disposed];

  state.charts.donut = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: values,
        backgroundColor: ['#f59e0b', '#10b981', '#6366f1', '#0ea5e9'],
        borderWidth: 2,
        borderColor: '#0f172a'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => ` ${ctx.label}: ${ctx.raw.toLocaleString()} cases`
          }
        }
      },
      cutout: '68%'
    }
  });
}

// Load Trend Chart
async function loadTrends() {
  try {
    const res = await fetch(`/api/trends?${getQueryString()}`);
    const data = await res.json();
    
    document.getElementById('trendTypeBadge').textContent = data.type === 'monthly' ? 'Monthly Trend' : 'Yearly Trend';
    const ctx = document.getElementById('trendChart').getContext('2d');
    if (state.charts.trend) state.charts.trend.destroy();

    state.charts.trend = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: data.labels,
        datasets: [
          {
            label: 'Reported Cases',
            data: data.totals,
            backgroundColor: 'rgba(59, 130, 246, 0.75)',
            borderColor: '#3b82f6',
            borderRadius: 4
          },
          {
            label: 'Charge-Sheeted',
            data: data.chargesheeted,
            backgroundColor: 'rgba(16, 185, 129, 0.75)',
            borderColor: '#10b981',
            borderRadius: 4
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { grid: { color: '#1e293b' }, ticks: { color: '#94a3b8' } },
          y: { grid: { color: '#1e293b' }, ticks: { color: '#94a3b8' } }
        },
        plugins: {
          legend: { labels: { color: '#cbd5e1', font: { size: 11 } } }
        }
      }
    });
  } catch (err) {
    console.error('Error loading trends:', err);
  }
}

// Load Top 5 Crime Heads on Overview
async function loadOverviewCrimeTable() {
  try {
    const res = await fetch(`/api/crime-heads?${getQueryString({ limit: 6 })}`);
    const data = await res.json();
    const tbody = document.getElementById('overviewCrimeHeadTable');
    tbody.innerHTML = '';

    data.forEach(item => {
      const tr = document.createElement('tr');
      tr.className = 'hover:bg-slate-800/40 transition';
      tr.innerHTML = `
        <td class="py-2.5 px-3 font-medium text-white flex items-center gap-2">
          <i class="fa-solid fa-folder-closed text-blue-400"></i> ${item.crime_head}
        </td>
        <td class="py-2.5 px-3 text-right font-bold text-slate-100">${item.total.toLocaleString()}</td>
        <td class="py-2.5 px-3 text-right text-amber-400 font-semibold">${item.ui.toLocaleString()}</td>
        <td class="py-2.5 px-3 text-right text-emerald-400 font-semibold">${item.chargesheeted.toLocaleString()}</td>
        <td class="py-2.5 px-3 text-right font-bold">${item.cs_rate}%</td>
        <td class="py-2.5 px-3">
          <div class="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
            <div class="bg-gradient-to-r from-blue-500 to-emerald-400 h-2 rounded-full" style="width: ${Math.min(item.cs_rate, 100)}%"></div>
          </div>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error('Error loading top crime heads:', err);
  }
}

// TAB 2: Station Performance
async function loadStationData() {
  try {
    const res = await fetch(`/api/stations?${getQueryString()}`);
    const data = await res.json();
    const tbody = document.getElementById('stationTableBody');
    tbody.innerHTML = '';

    data.forEach((st, idx) => {
      let ratingClass = 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20';
      let ratingText = 'Optimal';
      if (st.cs_rate < 30) {
        ratingClass = 'bg-rose-500/10 text-rose-400 border border-rose-500/20';
        ratingText = 'Critical';
      } else if (st.cs_rate < 50) {
        ratingClass = 'bg-amber-500/10 text-amber-400 border border-amber-500/20';
        ratingText = 'Moderate';
      }

      const tr = document.createElement('tr');
      tr.className = 'hover:bg-slate-800/50 transition';
      tr.innerHTML = `
        <td class="py-3 px-3 text-slate-500 font-mono">${idx + 1}</td>
        <td class="py-3 px-4 font-bold text-white flex items-center gap-2">
          <i class="fa-solid fa-shield text-slate-500"></i> ${st.station}
        </td>
        <td class="py-3 px-3 text-slate-400">${st.sub_division || '--'}</td>
        <td class="py-3 px-3 text-right font-bold text-slate-100">${st.total.toLocaleString()}</td>
        <td class="py-3 px-3 text-right text-amber-400 font-semibold">${st.ui.toLocaleString()}</td>
        <td class="py-3 px-3 text-right text-emerald-400 font-semibold">${st.chargesheeted.toLocaleString()}</td>
        <td class="py-3 px-3 text-right text-indigo-400 font-semibold">${st.disposed.toLocaleString()}</td>
        <td class="py-3 px-3 text-right text-rose-400 font-semibold">${st.long_pending.toLocaleString()}</td>
        <td class="py-3 px-3 text-right font-bold text-emerald-400">${st.cs_rate}%</td>
        <td class="py-3 px-4 text-center">
          <span class="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${ratingClass}">${ratingText}</span>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error('Error loading stations:', err);
  }
}

// TAB 3: Crime Head Analytics
async function loadCrimeHeadData() {
  try {
    const res = await fetch(`/api/crime-heads?${getQueryString({ limit: 12 })}`);
    const data = await res.json();

    const labels = data.map(d => d.crime_head);
    const totals = data.map(d => d.total);
    const csRates = data.map(d => d.cs_rate);

    // Volume Chart
    const ctx1 = document.getElementById('crimeHeadsChart').getContext('2d');
    if (state.charts.crimeVol) state.charts.crimeVol.destroy();

    state.charts.crimeVol = new Chart(ctx1, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Total Cases',
          data: totals,
          backgroundColor: '#3b82f6',
          borderRadius: 4
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { grid: { color: '#1e293b' }, ticks: { color: '#94a3b8' } },
          y: { grid: { display: false }, ticks: { color: '#cbd5e1', font: { size: 10 } } }
        },
        plugins: { legend: { display: false } }
      }
    });

    // CS Rate Chart
    const ctx2 = document.getElementById('crimeCsRateChart').getContext('2d');
    if (state.charts.crimeCs) state.charts.crimeCs.destroy();

    state.charts.crimeCs = new Chart(ctx2, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Charge-Sheet Rate (%)',
          data: csRates,
          backgroundColor: '#10b981',
          borderRadius: 4
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { max: 100, grid: { color: '#1e293b' }, ticks: { color: '#94a3b8', callback: v => `${v}%` } },
          y: { grid: { display: false }, ticks: { color: '#cbd5e1', font: { size: 10 } } }
        },
        plugins: { legend: { display: false } }
      }
    });
  } catch (err) {
    console.error('Error loading crime heads:', err);
  }
}

// TAB 4: Pendency Analytics
async function loadPendencyData() {
  try {
    const res = await fetch(`/api/pendency?${getQueryString()}`);
    const data = await res.json();

    const ctx = document.getElementById('pendencyChart').getContext('2d');
    if (state.charts.pendency) state.charts.pendency.destroy();

    const bracketLabels = Object.keys(data.brackets);
    const bracketValues = Object.values(data.brackets);

    state.charts.pendency = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: bracketLabels,
        datasets: [{
          label: 'Cases in Backlog',
          data: bracketValues,
          backgroundColor: ['#10b981', '#3b82f6', '#f59e0b', '#f97316', '#ef4444'],
          borderRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { grid: { color: '#1e293b' }, ticks: { color: '#94a3b8' } },
          y: { grid: { color: '#1e293b' }, ticks: { color: '#94a3b8' } }
        },
        plugins: { legend: { display: false } }
      }
    });

    // Render Reasons
    const cont = document.getElementById('reasonsContainer');
    cont.innerHTML = '';
    const maxCnt = data.reasons.length > 0 ? data.reasons[0].count : 1;

    data.reasons.forEach(r => {
      const pct = Math.round((r.count / maxCnt) * 100);
      const div = document.createElement('div');
      div.className = 'bg-slate-800/60 p-3 rounded-lg border border-slate-700/60';
      div.innerHTML = `
        <div class="flex justify-between text-xs mb-1">
          <span class="font-medium text-slate-200">${r.reason}</span>
          <span class="font-bold text-amber-400">${r.count.toLocaleString()} cases</span>
        </div>
        <div class="w-full bg-slate-900 rounded-full h-1.5 overflow-hidden">
          <div class="bg-amber-500 h-1.5 rounded-full" style="width: ${pct}%"></div>
        </div>
      `;
      cont.appendChild(div);
    });
  } catch (err) {
    console.error('Error loading pendency:', err);
  }
}

// TAB 5: Case Explorer
let currentCasesData = [];
async function loadCaseData() {
  try {
    const qStr = getQueryString({
      q: state.caseQuery,
      page: state.casePage,
      page_size: state.casePageSize
    });

    const res = await fetch(`/api/cases?${qStr}`);
    const data = await res.json();
    currentCasesData = data.items;

    document.getElementById('caseRecordCount').textContent = data.total.toLocaleString();
    document.getElementById('currentPageNum').textContent = data.page;
    document.getElementById('totalPagesNum').textContent = data.total_pages;
    document.getElementById('prevPageBtn').disabled = data.page <= 1;
    document.getElementById('nextPageBtn').disabled = data.page >= data.total_pages;

    const tbody = document.getElementById('caseTableBody');
    tbody.innerHTML = '';

    if (data.items.length === 0) {
      tbody.innerHTML = `<tr><td colspan="9" class="text-center py-8 text-slate-500">No cases match the selected filters.</td></tr>`;
      return;
    }

    data.items.forEach(c => {
      let stageBadge = 'bg-slate-800 text-slate-300 border border-slate-700';
      const stageLower = (c.stage || '').toLowerCase();
      if (stageLower.includes('ui') || stageLower.includes('under')) {
        stageBadge = 'bg-amber-500/10 text-amber-400 border border-amber-500/30';
      } else if (stageLower.includes('charge') || stageLower.includes('pt')) {
        stageBadge = 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30';
      } else if (stageLower.includes('dispos')) {
        stageBadge = 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/30';
      }

      const tr = document.createElement('tr');
      tr.className = 'hover:bg-slate-800/50 transition';
      tr.innerHTML = `
        <td class="py-3 px-3 font-mono font-bold text-white">${c.fir_no || '--'}</td>
        <td class="py-3 px-3 text-slate-400">${c.fir_date || '--'}</td>
        <td class="py-3 px-3 font-medium text-slate-200">${c.police_station || '--'}</td>
        <td class="py-3 px-3 text-slate-300 font-medium">${c.crime_head || '--'}</td>
        <td class="py-3 px-3 font-mono text-slate-400 max-w-[140px] truncate" title="${c.acts_sec || ''}">${c.acts_sec || '--'}</td>
        <td class="py-3 px-3 text-slate-300">${c.io_name || '--'}</td>
        <td class="py-3 px-3">
          <span class="px-2 py-0.5 rounded text-[10px] font-semibold ${stageBadge}">${c.stage || 'N/A'}</span>
        </td>
        <td class="py-3 px-3 text-right font-mono font-bold ${c.days_pending > 365 ? 'text-rose-400' : 'text-slate-300'}">${c.days_pending || 0}</td>
        <td class="py-3 px-3 text-center">
          <button class="view-detail-btn px-2.5 py-1 bg-slate-800 hover:bg-blue-600 text-slate-200 hover:text-white rounded text-[11px] font-medium transition" data-id="${c.id}">
            View
          </button>
        </td>
      `;
      tbody.appendChild(tr);
    });

    document.querySelectorAll('.view-detail-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = parseInt(btn.dataset.id);
        const item = currentCasesData.find(x => x.id === id);
        if (item) openCaseModal(item);
      });
    });
  } catch (err) {
    console.error('Error loading cases:', err);
  }
}

// Modal Details
function openCaseModal(caseItem) {
  document.getElementById('modalFirNo').textContent = `FIR NO: ${caseItem.fir_no || '--'}`;
  document.getElementById('modalPsName').textContent = `Police Station: ${caseItem.police_station || '--'}`;
  document.getElementById('modalFirDate').textContent = caseItem.fir_date || '--';
  document.getElementById('modalIoName').textContent = caseItem.io_name || '--';
  document.getElementById('modalSubDiv').textContent = caseItem.sub_division || '--';
  document.getElementById('modalHead').textContent = `${caseItem.crime_head || '--'} (${caseItem.sub_head || 'N/A'})`;
  document.getElementById('modalGravity').textContent = caseItem.gravity_type || '--';
  document.getElementById('modalDays').textContent = `${caseItem.days_pending || 0} days`;
  document.getElementById('modalActs').textContent = caseItem.acts_sec || '--';
  document.getElementById('modalStage').textContent = caseItem.stage || '--';
  document.getElementById('modalReason').textContent = caseItem.reason_ui || 'Not Specified';
  document.getElementById('modalBrief').textContent = caseItem.brief || 'No case brief recorded.';

  document.getElementById('caseModal').classList.remove('hidden');
}

function closeModal() {
  document.getElementById('caseModal').classList.add('hidden');
}

// Export Summary to CSV
async function exportSummaryCSV() {
  try {
    const res = await fetch(`/api/stations?${getQueryString()}`);
    const data = await res.json();
    
    let csv = 'Police Station,Sub-Division,Total Cases,Under Investigation,Charge-Sheeted,Disposed,Long Pending (>1y),CS Rate (%)\n';
    data.forEach(s => {
      csv += `"${s.station}","${s.sub_division}",${s.total},${s.ui},${s.chargesheeted},${s.disposed},${s.long_pending},${s.cs_rate}\n`;
    });

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.setAttribute('download', `Police_Crime_Summary_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  } catch (err) {
    alert('Failed to export summary: ' + err.message);
  }
}
