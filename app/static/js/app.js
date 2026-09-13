/**
 * 🌸 HouseholdAccountBook - Modern Client Application
 */

const STATE = {
  currentYear: 2026,
  currentMonth: new Date().getMonth() + 1,
  currentTab: 'today', // 'today' | 'annual' | 1..12
  categories: [],
  paymentMethods: [],
  networkInfo: null,
  trendChart: null,
  donutChart: null
};

// --- Initialization ---
document.addEventListener('DOMContentLoaded', async () => {
  // PWA Service Worker
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/static/sw.js').catch(console.warn);
  }

  // Set default date to today YYYY-MM-DD
  const todayStr = getTodayString();
  const dateInput = document.getElementById('inputDate');
  if (dateInput) dateInput.value = todayStr;

  // Set today date title
  const dateTitle = document.getElementById('todayDateTitle');
  if (dateTitle) {
    const d = new Date();
    const days = ['일', '월', '화', '수', '목', '금', '토'];
    dateTitle.textContent = `${d.getFullYear()}년 ${d.getMonth() + 1}월 ${d.getDate()}일 (${days[d.getDay()]})`;
  }

  // Generate 1월 ~ 12월 Navigation buttons
  renderMonthTabs();

  // Load Metadata
  await loadMetadata();

  // Load Today overview
  await loadTodayOverview();

  // Pre-load network info for QR
  loadNetworkInfo();
});

function getTodayString() {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function formatKRW(val) {
  return Number(val || 0).toLocaleString('ko-KR');
}

// --- Metadata Loading ---
async function loadMetadata() {
  try {
    const [catsRes, paysRes] = await Promise.all([
      fetch('/api/meta/categories'),
      fetch('/api/meta/payment-methods')
    ]);
    STATE.categories = await catsRes.json();
    STATE.paymentMethods = await paysRes.json();

    renderCategoryChips();
    renderPaymentPills();
    renderFilterCategories();
  } catch (err) {
    console.error('Failed to load metadata', err);
  }
}

async function loadNetworkInfo() {
  try {
    const res = await fetch('/api/meta/network-info');
    STATE.networkInfo = await res.json();
  } catch (err) {
    console.warn('Network info unavailable', err);
  }
}

// --- Month Tabs Generation ---
function renderMonthTabs() {
  const container = document.getElementById('monthTabsContainer');
  if (!container) return;
  container.innerHTML = '';

  for (let m = 1; m <= 12; m++) {
    const btn = document.createElement('button');
    btn.id = `tab-btn-month-${m}`;
    btn.className = `category-chip text-xs px-2.5 py-1 ${m === STATE.currentMonth ? 'border-purple-300' : ''}`;
    btn.textContent = `${m}월`;
    btn.onclick = () => switchTab(m);
    container.appendChild(btn);
  }
}

// --- Category & Payment Rendering ---
function renderCategoryChips() {
  const container = document.getElementById('categoryChipsList');
  if (!container) return;
  container.innerHTML = '';

  STATE.categories.forEach((cat, idx) => {
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className = `category-chip ${idx === 0 ? 'active' : ''}`;
    chip.style.backgroundColor = cat.color_hex + '33'; // 20% opacity
    chip.innerHTML = `<span>●</span> <span>${cat.name}</span>`;
    chip.onclick = () => {
      document.querySelectorAll('#categoryChipsList .category-chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      document.getElementById('selectedCategoryId').value = cat.id;
    };
    container.appendChild(chip);
  });
  if (STATE.categories[0]) {
    document.getElementById('selectedCategoryId').value = STATE.categories[0].id;
  }
}

function renderPaymentPills() {
  const container = document.getElementById('paymentPillsList');
  if (!container) return;
  container.innerHTML = '';

  STATE.paymentMethods.forEach((pay, idx) => {
    const pill = document.createElement('button');
    pill.type = 'button';
    pill.className = `pay-pill ${idx === 0 ? 'active' : ''}`;
    pill.textContent = pay.name;
    pill.onclick = () => {
      document.querySelectorAll('#paymentPillsList .pay-pill').forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      document.getElementById('selectedPaymentId').value = pay.id;
    };
    container.appendChild(pill);
  });
  if (STATE.paymentMethods[0]) {
    document.getElementById('selectedPaymentId').value = STATE.paymentMethods[0].id;
  }
}

function renderFilterCategories() {
  const select = document.getElementById('filterCategory');
  if (!select) return;
  select.innerHTML = '<option value="">전체 카테고리</option>';
  STATE.categories.forEach(cat => {
    const opt = document.createElement('option');
    opt.value = cat.id;
    opt.textContent = cat.name;
    select.appendChild(opt);
  });
}

// --- Quick Amount Helpers ---
function addAmount(val) {
  const input = document.getElementById('inputAmount');
  const current = Number(input.value) || 0;
  input.value = current + val;
}

function clearAmount() {
  document.getElementById('inputAmount').value = '';
}

// --- Tab Navigation ---
function switchTab(tab) {
  STATE.currentTab = tab;

  // View containers
  const viewToday = document.getElementById('view-today');
  const viewMonth = document.getElementById('view-month');
  const viewAnnual = document.getElementById('view-annual');

  viewToday.classList.add('hidden');
  viewMonth.classList.add('hidden');
  viewAnnual.classList.add('hidden');

  // Clear tab buttons styling
  document.querySelectorAll('.category-chip').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.bottom-nav-item').forEach(b => b.classList.remove('active'));

  if (tab === 'today') {
    viewToday.classList.remove('hidden');
    const b = document.getElementById('tab-btn-today');
    if (b) b.classList.add('active');
    const mb = document.getElementById('mobile-nav-today');
    if (mb) mb.classList.add('active');
    loadTodayOverview();
  } else if (tab === 'annual') {
    viewAnnual.classList.remove('hidden');
    const b = document.getElementById('tab-btn-annual');
    if (b) b.classList.add('active');
    const mb = document.getElementById('mobile-nav-annual');
    if (mb) mb.classList.add('active');
    loadAnnualDashboard();
  } else if (typeof tab === 'number') {
    STATE.currentMonth = tab;
    viewMonth.classList.remove('hidden');
    const b = document.getElementById(`tab-btn-month-${tab}`);
    if (b) b.classList.add('active');
    const mb = document.getElementById('mobile-nav-month');
    if (mb) mb.classList.add('active');
    loadMonthDetail(tab);
  }
}

function switchToCurrentMonth() {
  switchTab(STATE.currentMonth || new Date().getMonth() + 1);
}

function onYearChange() {
  STATE.currentYear = Number(document.getElementById('yearSelector').value);
  if (STATE.currentTab === 'today') {
    loadTodayOverview();
  } else if (STATE.currentTab === 'annual') {
    loadAnnualDashboard();
  } else {
    loadMonthDetail(STATE.currentTab);
  }
}

function refreshData() {
  if (STATE.currentTab === 'today') loadTodayOverview();
  else if (STATE.currentTab === 'annual') loadAnnualDashboard();
  else loadMonthDetail(STATE.currentTab);
}

// --- Today Quick Overview & History ---
async function loadTodayOverview() {
  try {
    const res = await fetch('/api/transactions/overview');
    const data = await res.json();

    document.getElementById('todayAmountText').textContent = formatKRW(data.today_expense_total);
    document.getElementById('todayCountBadge').textContent = `${data.today_transaction_count}건`;

    // Monthly summary in top card
    const s = data.month_summary;
    document.getElementById('currMonthLabel').textContent = s.month;
    document.getElementById('monthIncomeText').textContent = `${formatKRW(s.total_income)}원`;
    document.getElementById('monthFixedExpText').textContent = `${formatKRW(s.fixed_expense)}원`;
    document.getElementById('monthVarExpText').textContent = `${formatKRW(s.variable_expense)}원`;
    document.getElementById('monthBalanceText').textContent = `${formatKRW(s.balance)}원`;
    document.getElementById('savingsRateBadge').textContent = `저축률 ${s.savings_rate}%`;

    // Budget progress
    const expRate = s.total_income > 0 ? Math.min(100, Math.round(s.total_expense / s.total_income * 100)) : 0;
    document.getElementById('budgetProgressBar').style.width = `${expRate}%`;

    // Today transaction items
    renderTodayTransactions(data.recent_transactions);
  } catch (err) {
    console.error('Failed to load today overview', err);
  }
}

function renderTodayTransactions(items) {
  const container = document.getElementById('todayTransactionsList');
  if (!container) return;

  if (!items || items.length === 0) {
    container.innerHTML = '<div class="p-6 text-center text-gray-400 text-xs">오늘 등록된 지출 내역이 없습니다. 위 양식에서 추가해보세요! ☕</div>';
    return;
  }

  container.innerHTML = items.map(item => `
    <div class="glass-card p-3 flex items-center justify-between hover:bg-white/80 transition">
      <div class="flex items-center gap-3">
        <span class="w-2.5 h-2.5 rounded-full" style="background-color: ${item.category_color}"></span>
        <div>
          <div class="flex items-center gap-2">
            <span class="text-xs font-bold text-gray-800">${escapeHtml(item.title)}</span>
            <span class="badge-category" style="background-color: ${item.category_color}22; color: #1F2937">${item.category_name}</span>
            <span class="badge-pay">${item.payment_method_name}</span>
          </div>
          ${item.memo ? `<span class="text-[11px] text-gray-400">${escapeHtml(item.memo)}</span>` : ''}
        </div>
      </div>
      <div class="flex items-center gap-3">
        <span class="text-sm font-bold text-rose-600">-${formatKRW(item.amount)}원</span>
        <button onclick="deleteTransaction(${item.id})" class="text-gray-400 hover:text-rose-500 p-1 rounded" title="삭제">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
          </svg>
        </button>
      </div>
    </div>
  `).join('');
}

// --- Quick Submit Handler ---
async function handleQuickSubmit(e) {
  e.preventDefault();
  const btn = document.getElementById('btnSubmitExpense');
  btn.disabled = true;
  btn.textContent = '등록 중...';

  const payload = {
    transaction_date: document.getElementById('inputDate').value,
    amount: Number(document.getElementById('inputAmount').value),
    category_id: Number(document.getElementById('selectedCategoryId').value),
    title: document.getElementById('inputTitle').value.trim(),
    payment_method_id: Number(document.getElementById('selectedPaymentId').value),
    memo: document.getElementById('inputMemo').value.trim()
  };

  try {
    const res = await fetch('/api/transactions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error('등록 실패');

    // Reset amount & title
    document.getElementById('inputAmount').value = '';
    document.getElementById('inputTitle').value = '';
    document.getElementById('inputMemo').value = '';

    // Show temporary badge or vibration
    if (navigator.vibrate) navigator.vibrate(50);
    await loadTodayOverview();
  } catch (err) {
    alert('등록에 실패했습니다: ' + err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = '✨ 지출 등록 완료';
  }
}

async function deleteTransaction(id) {
  if (!confirm('정말 삭제하시겠습니까?')) return;
  try {
    const res = await fetch(`/api/transactions/${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('삭제 실패');
    if (STATE.currentTab === 'today') loadTodayOverview();
    else if (typeof STATE.currentTab === 'number') loadMonthDetail(STATE.currentTab);
  } catch (err) {
    alert('삭제 실패: ' + err.message);
  }
}

// --- Month Detail View Loading ---
async function loadMonthDetail(m) {
  const y = STATE.currentYear;
  document.getElementById('monthDetailTitle').textContent = `${y}년 ${m}월 상세 가계부`;

  try {
    const [summaryRes, plansRes] = await Promise.all([
      fetch(`/api/analytics/monthly/${y}/${m}`),
      fetch(`/api/fixed-plans/${y}/${m}`)
    ]);
    const summary = await summaryRes.json();
    const plans = await plansRes.json();

    // Summary Cards
    document.getElementById('tabMonthIncome').textContent = `${formatKRW(summary.total_income)}원`;
    document.getElementById('tabMonthFixed').textContent = `${formatKRW(summary.fixed_expense)}원`;
    document.getElementById('tabMonthVar').textContent = `${formatKRW(summary.variable_expense)}원`;
    document.getElementById('tabMonthTotalExp').textContent = `${formatKRW(summary.total_expense)}원`;
    document.getElementById('tabMonthSavings').textContent = `${formatKRW(summary.savings_investment)}원`;
    document.getElementById('tabMonthBalance').textContent = `${formatKRW(summary.balance)}원`;

    // Render Fixed Plans Tables
    renderFixedTable('fixedIncomeBody', plans.incomes);
    renderFixedTable('fixedExpenseBody', plans.expenses);
    renderFixedTable('savingsBody', plans.savings);

    // Load Variable Expenses
    loadMonthVariableExpenses();
  } catch (err) {
    console.error('Failed to load month detail', err);
  }
}

function renderFixedTable(tbodyId, items) {
  const tbody = document.getElementById(tbodyId);
  if (!tbody) return;
  tbody.innerHTML = items.map((item, idx) => `
    <tr class="hover:bg-white/50">
      <td class="py-1.5"><input type="text" value="${escapeHtml(item.item_name)}" class="glass-input text-xs py-1 px-1.5 item-name" style="width: 90px"></td>
      <td class="py-1.5"><input type="text" value="${escapeHtml(item.day || '')}" class="glass-input text-xs py-1 px-1.5 item-day" style="width: 50px"></td>
      <td class="py-1.5"><input type="text" value="${escapeHtml(item.description || '')}" class="glass-input text-xs py-1 px-1.5 item-desc" style="width: 100px"></td>
      <td class="py-1.5 text-right"><input type="number" value="${item.amount}" class="glass-input text-xs py-1 px-1.5 text-right item-amt font-semibold" style="width: 80px"></td>
      <td class="py-1.5 text-center"><button onclick="this.closest('tr').remove()" class="text-gray-400 hover:text-rose-500">✕</button></td>
    </tr>
  `).join('');
}

function addFixedRow(type) {
  const tbodyId = type === 'income' ? 'fixedIncomeBody' : (type === 'expense' ? 'fixedExpenseBody' : 'savingsBody');
  const tbody = document.getElementById(tbodyId);
  const tr = document.createElement('tr');
  tr.className = 'hover:bg-white/50';
  tr.innerHTML = `
    <td class="py-1.5"><input type="text" placeholder="항목명" class="glass-input text-xs py-1 px-1.5 item-name" style="width: 90px"></td>
    <td class="py-1.5"><input type="text" placeholder="일" class="glass-input text-xs py-1 px-1.5 item-day" style="width: 50px"></td>
    <td class="py-1.5"><input type="text" placeholder="내용" class="glass-input text-xs py-1 px-1.5 item-desc" style="width: 100px"></td>
    <td class="py-1.5 text-right"><input type="number" value="0" class="glass-input text-xs py-1 px-1.5 text-right item-amt font-semibold" style="width: 80px"></td>
    <td class="py-1.5 text-center"><button onclick="this.closest('tr').remove()" class="text-gray-400 hover:text-rose-500">✕</button></td>
  `;
  tbody.appendChild(tr);
}

async function saveCurrentMonthFixedPlans(asTemplate) {
  const y = STATE.currentYear;
  const m = STATE.currentMonth;

  function parseTable(tbodyId) {
    const rows = document.querySelectorAll(`#${tbodyId} tr`);
    const list = [];
    rows.forEach(r => {
      const name = r.querySelector('.item-name')?.value.trim();
      const day = r.querySelector('.item-day')?.value.trim();
      const desc = r.querySelector('.item-desc')?.value.trim();
      const amt = Number(r.querySelector('.item-amt')?.value) || 0;
      if (name) {
        list.push({
          year: y,
          month: m,
          item_name: name,
          day: day,
          description: desc,
          amount: amt
        });
      }
    });
    return list;
  }

  const payload = {
    year: y,
    month: m,
    incomes: parseTable('fixedIncomeBody'),
    expenses: parseTable('fixedExpenseBody'),
    savings: parseTable('savingsBody')
  };

  try {
    const res = await fetch(`/api/fixed-plans/${y}/${m}?set_as_template=${asTemplate}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error('저장 실패');
    alert(asTemplate ? '기본 템플릿으로 저장되었습니다!' : `${m}월 고정 계획이 저장되었습니다!`);
    loadMonthDetail(m);
  } catch (err) {
    alert('저장 실패: ' + err.message);
  }
}

async function loadMonthVariableExpenses() {
  const y = STATE.currentYear;
  const m = STATE.currentMonth;
  const catFilter = document.getElementById('filterCategory')?.value || '';

  let url = `/api/transactions?year=${y}&month=${m}&limit=500`;
  if (catFilter) url += `&category_id=${catFilter}`;

  try {
    const res = await fetch(url);
    const items = await res.json();
    const tbody = document.getElementById('monthVarExpenseBody');
    if (!tbody) return;

    if (items.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="text-center py-6 text-gray-400">등록된 변동 지출 내역이 없습니다.</td></tr>';
      return;
    }

    tbody.innerHTML = items.map(item => `
      <tr>
        <td class="text-center font-mono">${item.transaction_date.slice(5)}</td>
        <td class="text-center">
          <span class="badge-category" style="background-color: ${item.category_color}22;">${item.category_name}</span>
        </td>
        <td class="font-medium">${escapeHtml(item.title)}</td>
        <td class="text-center"><span class="badge-pay">${item.payment_method_name}</span></td>
        <td class="text-right font-bold text-rose-600">${formatKRW(item.amount)}원</td>
        <td class="text-gray-400 text-xs">${escapeHtml(item.memo || '')}</td>
        <td class="text-center">
          <button onclick="deleteTransaction(${item.id})" class="text-gray-400 hover:text-rose-500">✕</button>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    console.error('Failed to load month variable expenses', err);
  }
}

// --- Annual Dashboard & Charts ---
async function loadAnnualDashboard() {
  const y = STATE.currentYear;
  document.getElementById('annualTitle').textContent = `${y}년 연간 가계부 대시보드`;

  try {
    const [annualRes, catsRes] = await Promise.all([
      fetch(`/api/analytics/annual/${y}`),
      fetch(`/api/analytics/categories/${y}/${STATE.currentMonth}`)
    ]);
    const data = await annualRes.json();
    const catBreakdown = await catsRes.json();

    // Top KPI cards
    document.getElementById('annTotalIncome').textContent = `${formatKRW(data.annual_total.total_income)}원`;
    document.getElementById('annTotalExpense').textContent = `${formatKRW(data.annual_total.total_expense)}원`;
    document.getElementById('annTotalSavings').textContent = `${formatKRW(data.annual_total.savings_investment)}원`;
    document.getElementById('annAvgRate').textContent = `${data.annual_total.savings_rate}%`;

    // Render Annual Table
    renderAnnualTable(data);

    // Render Charts
    renderTrendChart(data);
    renderDonutChart(catBreakdown);
  } catch (err) {
    console.error('Failed to load annual dashboard', err);
  }
}

function renderAnnualTable(data) {
  const tbody = document.getElementById('annualTableBody');
  if (!tbody) return;

  const monthRows = data.months.map(m => `
    <tr class="cursor-pointer hover:bg-purple-50/50" onclick="switchTab(${m.month})">
      <td class="text-center font-bold text-purple-700">${m.month_name}</td>
      <td class="text-right">${formatKRW(m.total_income)}</td>
      <td class="text-right">${formatKRW(m.fixed_expense)}</td>
      <td class="text-right">${formatKRW(m.variable_expense)}</td>
      <td class="text-right font-semibold text-rose-600">${formatKRW(m.total_expense)}</td>
      <td class="text-right font-semibold text-blue-600">${formatKRW(m.savings_investment)}</td>
      <td class="text-right font-semibold text-emerald-600">${formatKRW(m.balance)}</td>
      <td class="text-center font-bold text-purple-600">${m.savings_rate}%</td>
    </tr>
  `).join('');

  const totalRow = `
    <tr class="bg-purple-100/70 font-bold">
      <td class="text-center text-purple-900">${data.annual_total.month_name}</td>
      <td class="text-right">${formatKRW(data.annual_total.total_income)}</td>
      <td class="text-right">${formatKRW(data.annual_total.fixed_expense)}</td>
      <td class="text-right">${formatKRW(data.annual_total.variable_expense)}</td>
      <td class="text-right text-rose-700">${formatKRW(data.annual_total.total_expense)}</td>
      <td class="text-right text-blue-700">${formatKRW(data.annual_total.savings_investment)}</td>
      <td class="text-right text-emerald-700">${formatKRW(data.annual_total.balance)}</td>
      <td class="text-center text-purple-900">${data.annual_total.savings_rate}%</td>
    </tr>
  `;

  const avgRow = `
    <tr class="bg-gray-100/80 font-bold">
      <td class="text-center text-gray-800">${data.monthly_average.month_name}</td>
      <td class="text-right">${formatKRW(data.monthly_average.total_income)}</td>
      <td class="text-right">${formatKRW(data.monthly_average.fixed_expense)}</td>
      <td class="text-right">${formatKRW(data.monthly_average.variable_expense)}</td>
      <td class="text-right">${formatKRW(data.monthly_average.total_expense)}</td>
      <td class="text-right">${formatKRW(data.monthly_average.savings_investment)}</td>
      <td class="text-right">${formatKRW(data.monthly_average.balance)}</td>
      <td class="text-center">${data.monthly_average.savings_rate}%</td>
    </tr>
  `;

  tbody.innerHTML = monthRows + totalRow + avgRow;
}

function renderTrendChart(data) {
  const ctx = document.getElementById('annualTrendChart');
  if (!ctx) return;
  if (STATE.trendChart) STATE.trendChart.destroy();

  const labels = data.months.map(m => m.month_name);
  const incomes = data.months.map(m => m.total_income);
  const expenses = data.months.map(m => m.total_expense);
  const savings = data.months.map(m => m.savings_investment);

  STATE.trendChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [
        {
          label: '총 수입',
          data: incomes,
          backgroundColor: '#A8E6CFcc',
          borderColor: '#A8E6CF',
          borderWidth: 1.5,
          borderRadius: 6
        },
        {
          label: '총 지출',
          data: expenses,
          backgroundColor: '#FFB7B2cc',
          borderColor: '#FFB7B2',
          borderWidth: 1.5,
          borderRadius: 6
        },
        {
          label: '저축 및 투자',
          data: savings,
          backgroundColor: '#BEE3F8cc',
          borderColor: '#BEE3F8',
          borderWidth: 1.5,
          borderRadius: 6
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'top', labels: { font: { family: 'Pretendard', size: 12 } } }
      },
      scales: {
        y: {
          ticks: {
            callback: (v) => v >= 10000 ? (v / 10000) + '만' : v,
            font: { size: 11 }
          },
          grid: { color: 'rgba(229, 231, 235, 0.4)' }
        },
        x: {
          grid: { display: false }
        }
      }
    }
  });
}

function renderDonutChart(catData) {
  const ctx = document.getElementById('categoryDonutChart');
  if (!ctx) return;
  if (STATE.donutChart) STATE.donutChart.destroy();

  if (!catData || catData.length === 0) {
    ctx.parentElement.innerHTML = '<div class="text-xs text-gray-400 text-center">지출 데이터가 없습니다</div>';
    return;
  }

  const labels = catData.map(c => c.name);
  const data = catData.map(c => c.amount);
  const colors = catData.map(c => c.color_hex);

  STATE.donutChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: data,
        backgroundColor: colors,
        borderWidth: 2,
        borderColor: '#ffffff'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '65%',
      plugins: {
        legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } }
      }
    }
  });
}

// --- Modals & File Handling ---
function openQRModal() {
  const modal = document.getElementById('modalQR');
  const img = document.getElementById('modalQRImage');
  const urlSpan = document.getElementById('modalQRUrl');

  if (STATE.networkInfo) {
    img.src = STATE.networkInfo.qr_code;
    urlSpan.textContent = STATE.networkInfo.mobile_url;
  }
  modal.classList.remove('hidden');
}

function closeQRModal() {
  document.getElementById('modalQR').classList.add('hidden');
}

function openBackupModal() {
  document.getElementById('modalBackup').classList.remove('hidden');
}

function closeBackupModal() {
  document.getElementById('modalBackup').classList.add('hidden');
}

function downloadExcelFile() {
  window.location.href = `/api/spreadsheet/export/${STATE.currentYear}`;
}

async function handleExcelUpload(e) {
  const file = e.target.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch('/api/spreadsheet/import', {
      method: 'POST',
      body: formData
    });
    const result = await res.json();
    if (!res.ok) throw new Error(result.detail || '가져오기 실패');

    alert(`성공적으로 가져왔습니다!\n- 변동 지출: ${result.imported.variable_expenses}건\n- 고정 수입: ${result.imported.fixed_incomes}건\n- 고정 지출: ${result.imported.fixed_expenses}건\n- 저축/투자: ${result.imported.savings}건`);
    closeBackupModal();
    refreshData();
  } catch (err) {
    alert('가져오기 실패: ' + err.message);
  } finally {
    e.target.value = '';
  }
}

function downloadJsonBackup() {
  window.location.href = '/api/spreadsheet/backup-json';
}

async function handleJsonRestore(e) {
  const file = e.target.files[0];
  if (!file) return;

  if (!confirm('기존 데이터가 덮어씌워집니다. 진행하시겠습니까?')) {
    e.target.value = '';
    return;
  }

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch('/api/spreadsheet/restore-json', {
      method: 'POST',
      body: formData
    });
    const result = await res.json();
    if (!res.ok) throw new Error(result.detail || '복원 실패');
    alert('데이터가 성공적으로 복원되었습니다!');
    closeBackupModal();
    refreshData();
  } catch (err) {
    alert('복원 실패: ' + err.message);
  } finally {
    e.target.value = '';
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
