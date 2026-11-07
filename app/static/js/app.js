/**
 * 🌸 HouseholdAccountBook - Mobile-First Client Application
 */

const STATE = {
  currentYear: 2026,
  currentMonth: new Date().getMonth() + 1,
  currentTab: 'today', // 'today' | 'annual' | 'spending' | 1..12
  categories: [],
  paymentMethods: [],
  networkInfo: null,
  trendChart: null,
  donutChart: null,
  spendingCategoryChart: null,
  spendingCategoryData: null,
  spendingCategoryDepth: 1,
  spendingCategory2DepthMode: 'sub', // 'sub' | 'merchant'
  selectedCategoryItem: null,
  selected1DepthCategory: null,
  spendingPaymentChart: null,
  spendingWeeklyChart: null,
  spendingDayOfWeekChart: null,
  isEditingFixed: { income: false, expense: false, savings: false },
  isEditingVarExpense: false,
  cachedPlans: { incomes: [], expenses: [], savings: [] },
  cachedVarExpenses: [],
  cardPreviewItems: [],
  cardUploadFile: null
};

// --- Initialization ---
document.addEventListener('DOMContentLoaded', async () => {
  // PWA Service Worker
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/static/sw.js').then(reg => {
      reg.update().catch(() => {});
    }).catch(console.warn);
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

  // Update central month stepper
  updateHeaderMonthLabel();

  // Generate 1월 ~ 12월 Navigation buttons
  renderMonthTabs();

  // Load Metadata
  await loadMetadata();

  // Load Today overview
  await loadTodayOverview();

  // Pre-load network info for QR
  await loadNetworkInfo();

  // Handle URL hash routing immediately
  if (window.location.hash.startsWith('#month')) {
    switchToCurrentMonth();
    if (window.location.hash.includes('edit')) {
      STATE.isEditingVarExpense = true;
      const btn = document.getElementById('btnEditVarExpense');
      if (btn) {
        btn.textContent = '💾 수정 완료';
        btn.classList.add('is-editing');
      }
      const mobileList = document.getElementById('monthVarExpenseMobileList');
      if (mobileList) {
        mobileList.classList.remove('d-view-mode');
        mobileList.classList.add('d-edit-mode');
      }
      const desktopTable = document.getElementById('monthVarExpenseTableContainer');
      if (desktopTable) {
        desktopTable.classList.remove('d-view-mode');
        desktopTable.classList.add('d-edit-mode');
      }
    }
  } else if (window.location.hash === '#settings') {
    openSettingsModal();
  } else if (window.location.hash === '#edit-tx') {
    switchToCurrentMonth();
    document.getElementById('modalEditTransaction')?.classList.remove('hidden');
  }
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

// --- Month Stepper Logic ---
function updateHeaderMonthLabel() {
  const lbl = document.getElementById('headerMonthLabel');
  if (lbl) {
    lbl.textContent = `${STATE.currentYear}년 ${STATE.currentMonth}월`;
  }
  updateMobileMonthBar();
}

function updateMobileMonthBar() {
  const lbl = document.getElementById('mobileMonthBarLabel');
  if (lbl) {
    lbl.textContent = `${STATE.currentYear}년 ${STATE.currentMonth}월`;
  }
  const bar = document.getElementById('mobileMonthBar');
  if (bar) {
    if (STATE.currentTab === 'annual') {
      bar.classList.add('opacity-40', 'pointer-events-none');
    } else {
      bar.classList.remove('opacity-40', 'pointer-events-none');
    }
  }
}

function openMonthPickerModal() {
  const modal = document.getElementById('modalMonthPicker');
  if (!modal) return;
  const title = document.getElementById('monthPickerYearTitle');
  if (title) title.textContent = `${STATE.currentYear}년 월 선택`;
  renderMonthPickerGrid();
  modal.classList.remove('hidden');
}

function closeMonthPickerModal() {
  const modal = document.getElementById('modalMonthPicker');
  if (modal) modal.classList.add('hidden');
}

function renderMonthPickerGrid() {
  const grid = document.getElementById('monthPickerGrid');
  if (!grid) return;
  grid.innerHTML = '';
  const now = new Date();
  const thisMonth = now.getFullYear() === STATE.currentYear ? now.getMonth() + 1 : -1;

  for (let m = 1; m <= 12; m++) {
    const isCurrent = m === STATE.currentMonth;
    const isThisMonth = m === thisMonth;

    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = isCurrent
      ? 'relative py-3.5 px-2 rounded-2xl bg-indigo-600 text-white font-black shadow-md text-sm cursor-pointer'
      : 'relative py-3.5 px-2 rounded-2xl bg-slate-50 hover:bg-indigo-50 text-slate-800 font-bold border border-slate-200 text-sm cursor-pointer active:scale-95 transition-all';

    let badgeHtml = isThisMonth ? '<span class="absolute top-1.5 right-2 text-[9px] px-1 py-0.2 rounded-full bg-emerald-500 text-white font-extrabold">이번달</span>' : '';
    btn.innerHTML = `<span>${m}월</span>${badgeHtml}`;

    btn.onclick = () => {
      onMonthTabClick(m);
      closeMonthPickerModal();
    };
    grid.appendChild(btn);
  }
}

function prevMonth() {
  let m = STATE.currentMonth - 1;
  if (m < 1) {
    m = 12;
    STATE.currentYear -= 1;
    const ys = document.getElementById('yearSelector');
    if (ys) ys.value = STATE.currentYear;
  }
  STATE.currentMonth = m;
  updateHeaderMonthLabel();
  if (STATE.currentTab === 'spending') {
    updateMonthTabsHighlight(m);
    loadSpendingPatterns();
  } else if (STATE.currentTab === 'annual') {
    loadAnnualDashboard();
  } else if (STATE.currentTab === 'today') {
    loadTodayOverview();
  } else {
    switchTab(m);
  }
}

function nextMonth() {
  let m = STATE.currentMonth + 1;
  if (m > 12) {
    m = 1;
    STATE.currentYear += 1;
    const ys = document.getElementById('yearSelector');
    if (ys) ys.value = STATE.currentYear;
  }
  STATE.currentMonth = m;
  updateHeaderMonthLabel();
  if (STATE.currentTab === 'spending') {
    updateMonthTabsHighlight(m);
    loadSpendingPatterns();
  } else if (STATE.currentTab === 'annual') {
    loadAnnualDashboard();
  } else if (STATE.currentTab === 'today') {
    loadTodayOverview();
  } else {
    switchTab(m);
  }
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

// --- Month Tabs Generation & Navigation ---
function updateMonthTabsHighlight(activeMonth) {
  const targetMonth = activeMonth !== undefined ? activeMonth : STATE.currentMonth;
  for (let m = 1; m <= 12; m++) {
    const btn = document.getElementById(`tab-btn-month-${m}`);
    if (!btn) continue;
    // 월간 상세(숫자 탭)이거나 소비 분석('spending')일 때만 선택된 월 버튼 활성화
    if ((typeof STATE.currentTab === 'number' || STATE.currentTab === 'spending') && m === targetMonth) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  }
}

function onMonthTabClick(m) {
  STATE.currentMonth = m;
  if (STATE.currentTab === 'spending') {
    // 소비 분석 중일 때: 소비 분석 화면 유지한 채 해당 월로 이동
    updateHeaderMonthLabel();
    updateMonthTabsHighlight(m);
    loadSpendingPatterns();
  } else {
    // 월간 상세(숫자)이거나, 오늘 빠른등록(today), 연간 대시보드(annual)일 때: 월간 상세(m월)로 이동
    switchTab(m);
  }
}

function renderMonthTabs() {
  const container = document.getElementById('monthTabsContainer');
  if (!container) return;
  container.innerHTML = '';

  for (let m = 1; m <= 12; m++) {
    const btn = document.createElement('button');
    btn.id = `tab-btn-month-${m}`;
    btn.type = 'button';
    btn.className = 'category-chip text-xs px-3 py-1.5 font-bold';
    btn.textContent = `${m}월`;
    btn.onclick = () => onMonthTabClick(m);
    container.appendChild(btn);
  }
  updateMonthTabsHighlight();
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
    chip.innerHTML = `<span style="color: ${cat.color_hex}; font-size: 15px;">●</span> <span>${cat.name}</span>`;
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
  if (tab === 'month') {
    tab = STATE.currentMonth || (new Date().getMonth() + 1);
  }

  STATE.currentTab = tab;

  // View containers
  const viewToday = document.getElementById('view-today');
  const viewMonth = document.getElementById('view-month');
  const viewAnnual = document.getElementById('view-annual');
  const viewSpending = document.getElementById('view-spending');

  viewToday.classList.add('hidden');
  viewMonth.classList.add('hidden');
  viewAnnual.classList.add('hidden');
  if (viewSpending) viewSpending.classList.add('hidden');

  // Clear tab buttons styling
  document.querySelectorAll('.category-chip').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.bottom-nav-item').forEach(b => b.classList.remove('active'));

  if (tab === 'today') {
    viewToday.classList.remove('hidden');
    const b = document.getElementById('tab-btn-today');
    if (b) b.classList.add('active');
    const mb = document.getElementById('mobile-nav-today');
    if (mb) mb.classList.add('active');
    updateHeaderMonthLabel();
    updateMonthTabsHighlight();
    loadTodayOverview();
  } else if (tab === 'annual') {
    viewAnnual.classList.remove('hidden');
    const b = document.getElementById('tab-btn-annual');
    if (b) b.classList.add('active');
    const mb = document.getElementById('mobile-nav-annual');
    if (mb) mb.classList.add('active');
    updateMonthTabsHighlight();
    updateMobileMonthBar();
    loadAnnualDashboard();
  } else if (tab === 'spending') {
    if (viewSpending) viewSpending.classList.remove('hidden');
    const b = document.getElementById('tab-btn-spending');
    if (b) b.classList.add('active');
    const mb = document.getElementById('mobile-nav-spending');
    if (mb) mb.classList.add('active');
    updateHeaderMonthLabel();
    updateMonthTabsHighlight();
    loadSpendingPatterns();
  } else if (typeof tab === 'number') {
    STATE.currentMonth = tab;
    viewMonth.classList.remove('hidden');
    const detailBtn = document.getElementById('tab-btn-month-detail');
    if (detailBtn) detailBtn.classList.add('active');
    const b = document.getElementById(`tab-btn-month-${tab}`);
    if (b) b.classList.add('active');
    const mb = document.getElementById('mobile-nav-month');
    if (mb) mb.classList.add('active');
    updateHeaderMonthLabel();
    updateMonthTabsHighlight(tab);
    loadMonthDetail(tab);
  }
}

function switchToCurrentMonth() {
  switchTab(STATE.currentMonth || new Date().getMonth() + 1);
}

function onYearChange() {
  STATE.currentYear = Number(document.getElementById('yearSelector').value);
  updateHeaderMonthLabel();
  if (STATE.currentTab === 'today') {
    loadTodayOverview();
  } else if (STATE.currentTab === 'annual') {
    loadAnnualDashboard();
  } else if (STATE.currentTab === 'spending') {
    loadSpendingPatterns();
  } else {
    loadMonthDetail(STATE.currentTab);
  }
}

function refreshData() {
  if (STATE.currentTab === 'today') loadTodayOverview();
  else if (STATE.currentTab === 'annual') loadAnnualDashboard();
  else if (STATE.currentTab === 'spending') loadSpendingPatterns();
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
    container.innerHTML = '<div class="glass-card p-6 text-center text-slate-500 font-medium text-sm">오늘 등록된 지출 내역이 없습니다. 위 양식에서 3초 만에 추가해보세요! ☕</div>';
    return;
  }

  container.innerHTML = items.map(item => `
    <div class="glass-card p-3.5 flex items-center justify-between hover:bg-white/95 transition">
      <div class="flex items-center gap-3 min-w-0">
        <span class="w-3.5 h-3.5 rounded-full flex-shrink-0 shadow-xs" style="background-color: ${item.category_color}"></span>
        <div class="min-w-0">
          <div class="flex items-center gap-2 flex-wrap">
            <span class="text-sm sm:text-base font-extrabold text-slate-900">${escapeHtml(item.title)}</span>
            <span class="badge-category" style="background-color: ${item.category_color}25; color: #0F172A">${item.category_name}</span>
            <span class="badge-pay">${item.payment_method_name}</span>
          </div>
          ${item.memo ? `<span class="text-xs text-slate-500 block mt-0.5 truncate">${escapeHtml(item.memo)}</span>` : ''}
        </div>
      </div>
      <div class="flex items-center gap-3 ml-3 flex-shrink-0">
        <span class="text-base sm:text-lg font-black text-rose-600">-${formatKRW(item.amount)}원</span>
        <button onclick="deleteTransaction(${item.id})" class="mobile-tx-del-btn" title="삭제">
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

    // Vibrate haptic if supported
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

    // Summary Cards (High Contrast & Clear Typography)
    document.getElementById('tabMonthIncome').textContent = `${formatKRW(summary.total_income)}원`;
    document.getElementById('tabMonthFixed').textContent = `${formatKRW(summary.fixed_expense)}원`;
    document.getElementById('tabMonthVar').textContent = `${formatKRW(summary.variable_expense)}원`;
    document.getElementById('tabMonthTotalExp').textContent = `${formatKRW(summary.total_expense)}원`;
    document.getElementById('tabMonthSavings').textContent = `${formatKRW(summary.savings_investment)}원`;
    document.getElementById('tabMonthBalance').textContent = `${formatKRW(summary.balance)}원`;

    // Cache plans for seamless edit/view mode switching
    STATE.cachedPlans = plans;

    // Render Fixed Plans Tables (Respecting current edit states)
    renderFixedTable('fixedIncomeBody', plans.incomes, STATE.isEditingFixed.income);
    renderFixedTable('fixedExpenseBody', plans.expenses, STATE.isEditingFixed.expense);
    renderFixedTable('savingsBody', plans.savings, STATE.isEditingFixed.savings);

    // Load Variable Expenses (Both Mobile Cards & Desktop Table)
    await loadMonthVariableExpenses(m);
  } catch (err) {
    console.error('Failed to load month detail', err);
  }
}

function renderFixedTable(tbodyId, items, isEditing = false) {
  const tbody = document.getElementById(tbodyId);
  if (!tbody) return;

  if (!items || items.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" class="py-4 text-center text-slate-400 font-medium">${isEditing ? '등록된 항목이 없습니다. "+ 항목 추가"를 눌러 추가하세요.' : '등록된 항목이 없습니다.'}</td></tr>`;
    return;
  }

  if (!isEditing) {
    // 1) View Mode: Clean, readable formatted text (No input boxes)
    tbody.innerHTML = items.map(item => `
      <tr class="hover:bg-white/70 border-b border-gray-100">
        <td class="fixed-text-cell font-bold text-slate-900">${escapeHtml(item.item_name)}</td>
        <td class="fixed-text-cell text-center font-bold text-slate-600">${escapeHtml(item.day || '-')}</td>
        <td class="fixed-text-cell text-slate-700">${escapeHtml(item.description || '-')}</td>
        <td class="fixed-text-cell text-right fixed-text-amt">${formatKRW(item.amount)}원</td>
        <td class="fixed-text-cell fixed-del-col hidden"></td>
      </tr>
    `).join('');
  } else {
    // 2) Edit Mode: Input boxes and active delete buttons
    tbody.innerHTML = items.map(item => `
      <tr class="hover:bg-white/70 border-b border-gray-100">
        <td class="py-1.5"><input type="text" value="${escapeHtml(item.item_name)}" class="glass-input text-xs py-1.5 px-2 rounded-lg font-bold item-name" style="width: 100px"></td>
        <td class="py-1.5"><input type="text" value="${escapeHtml(item.day || '')}" class="glass-input text-xs py-1.5 px-2 rounded-lg text-center font-bold item-day" style="width: 50px"></td>
        <td class="py-1.5"><input type="text" value="${escapeHtml(item.description || '')}" class="glass-input text-xs py-1.5 px-2 rounded-lg item-desc" style="width: 110px"></td>
        <td class="py-1.5 text-right"><input type="number" value="${item.amount}" min="0" step="1" class="glass-input text-xs py-1.5 px-2 rounded-lg text-right item-amt font-extrabold text-slate-800" style="width: 90px"></td>
        <td class="py-1.5 text-center fixed-del-col"><button onclick="this.closest('tr').remove()" class="text-slate-400 hover:text-rose-600 font-bold p-1">✕</button></td>
      </tr>
    `).join('');
  }
}

async function toggleFixedSectionEdit(type) {
  const isCurrentlyEditing = STATE.isEditingFixed[type];
  const btn = document.getElementById(`btnEditFixed-${type}`);
  const btnAdd = document.getElementById(`btnAddFixed-${type}`);
  const tbodyId = type === 'income' ? 'fixedIncomeBody' : (type === 'expense' ? 'fixedExpenseBody' : 'savingsBody');
  const tableId = type === 'income' ? 'fixedIncomeTable' : (type === 'expense' ? 'fixedExpenseTable' : 'savingsTable');

  if (!isCurrentlyEditing) {
    // Switch to Edit Mode
    STATE.isEditingFixed[type] = true;
    if (btn) {
      btn.textContent = '💾 수정 완료';
      btn.classList.add('is-editing');
    }
    if (btnAdd) btnAdd.classList.remove('hidden');

    const table = document.getElementById(tableId);
    if (table) {
      table.querySelectorAll('.fixed-del-col').forEach(el => el.classList.remove('hidden'));
    }

    const items = STATE.cachedPlans ? (type === 'income' ? STATE.cachedPlans.incomes : (type === 'expense' ? STATE.cachedPlans.expenses : STATE.cachedPlans.savings)) : [];
    renderFixedTable(tbodyId, items, true);
  } else {
    // Finish editing: Extract rows and auto-save
    await saveCurrentMonthFixedPlans(false, false);
    STATE.isEditingFixed[type] = false;
    if (btn) {
      btn.textContent = '✏️ 내용 수정';
      btn.classList.remove('is-editing');
    }
    if (btnAdd) btnAdd.classList.add('hidden');

    const table = document.getElementById(tableId);
    if (table) {
      table.querySelectorAll('.fixed-del-col').forEach(el => el.classList.add('hidden'));
    }

    // Refresh month data & KPI summaries
    await loadMonthDetail(STATE.currentMonth);
  }
}

function addFixedRow(type) {
  if (!STATE.isEditingFixed[type]) {
    toggleFixedSectionEdit(type);
  }
  const tbodyId = type === 'income' ? 'fixedIncomeBody' : (type === 'expense' ? 'fixedExpenseBody' : 'savingsBody');
  const tbody = document.getElementById(tbodyId);
  const tr = document.createElement('tr');
  tr.className = 'hover:bg-white/70 border-b border-gray-100';
  tr.innerHTML = `
    <td class="py-1.5"><input type="text" placeholder="항목명" class="glass-input text-xs py-1.5 px-2 rounded-lg font-bold item-name" style="width: 100px"></td>
    <td class="py-1.5"><input type="text" placeholder="일자" class="glass-input text-xs py-1.5 px-2 rounded-lg text-center font-bold item-day" style="width: 50px"></td>
    <td class="py-1.5"><input type="text" placeholder="설명" class="glass-input text-xs py-1.5 px-2 rounded-lg item-desc" style="width: 110px"></td>
    <td class="py-1.5 text-right"><input type="number" value="0" min="0" step="1" class="glass-input text-xs py-1.5 px-2 rounded-lg text-right item-amt font-extrabold text-slate-800" style="width: 90px"></td>
    <td class="py-1.5 text-center fixed-del-col"><button onclick="this.closest('tr').remove()" class="text-slate-400 hover:text-rose-600 font-bold p-1">✕</button></td>
  `;
  tbody.appendChild(tr);
  const firstInput = tr.querySelector('input');
  if (firstInput) firstInput.focus();
}

async function saveCurrentMonthFixedPlans(isTemplate = false, showAlert = true) {
  const y = STATE.currentYear;
  const m = STATE.currentMonth;

  function extractRows(tbodyId, type) {
    // If currently in edit mode, extract from input boxes
    if (STATE.isEditingFixed[type]) {
      const rows = document.querySelectorAll(`#${tbodyId} tr`);
      return Array.from(rows).map(tr => {
        const name = tr.querySelector('.item-name')?.value.trim() || '';
        const day = tr.querySelector('.item-day')?.value.trim() || '';
        const desc = tr.querySelector('.item-desc')?.value.trim() || '';
        const amt = Number(tr.querySelector('.item-amt')?.value) || 0;
        return { item_name: name, day, description: desc, amount: amt };
      }).filter(it => it.item_name !== '');
    }
    // If currently in view mode, retain cached items
    if (STATE.cachedPlans) {
      if (type === 'income') return STATE.cachedPlans.incomes || [];
      if (type === 'expense') return STATE.cachedPlans.expenses || [];
      if (type === 'savings') return STATE.cachedPlans.savings || [];
    }
    return [];
  }

  const payload = {
    year: y,
    month: m,
    incomes: extractRows('fixedIncomeBody', 'income'),
    expenses: extractRows('fixedExpenseBody', 'expense'),
    savings: extractRows('savingsBody', 'savings'),
    is_template: isTemplate
  };

  try {
    const res = await fetch(`/api/fixed-plans/${y}/${m}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || '저장 실패');
    }
    if (showAlert) {
      alert(isTemplate ? '기본 템플릿으로 저장되었습니다. 신규 월 생성 시 이 값이 기본 반영됩니다.' : '고정 계획이 저장되었습니다.');
      loadMonthDetail(m);
    }
  } catch (err) {
    if (showAlert) {
      alert('저장 실패: ' + err.message);
    } else {
      console.error('고정 계획 자동 저장 실패:', err);
    }
  }
}

// Date formatting helper: 2026-09-18 -> 09/18
function formatShortSlashDate(dateStr) {
  if (!dateStr) return '';
  const parts = String(dateStr).split('-');
  if (parts.length >= 3) {
    return `${parts[1]}/${parts[2]}`;
  }
  return dateStr.slice(5).replace('-', '/');
}

// Section D Edit Mode Toggle
function toggleVariableExpensesEdit() {
  STATE.isEditingVarExpense = !STATE.isEditingVarExpense;
  const btn = document.getElementById('btnEditVarExpense');
  const mobileList = document.getElementById('monthVarExpenseMobileList');
  const desktopContainer = document.getElementById('monthVarExpenseTableContainer');

  if (STATE.isEditingVarExpense) {
    if (btn) {
      btn.textContent = '💾 수정 완료';
      btn.classList.add('is-editing');
    }
    if (mobileList) {
      mobileList.classList.remove('d-view-mode');
      mobileList.classList.add('d-edit-mode');
    }
    if (desktopContainer) {
      desktopContainer.classList.remove('d-view-mode');
      desktopContainer.classList.add('d-edit-mode');
    }
  } else {
    if (btn) {
      btn.textContent = '✏️ 내용 수정';
      btn.classList.remove('is-editing');
    }
    if (mobileList) {
      mobileList.classList.remove('d-edit-mode');
      mobileList.classList.add('d-view-mode');
    }
    if (desktopContainer) {
      desktopContainer.classList.remove('d-edit-mode');
      desktopContainer.classList.add('d-view-mode');
    }
  }
}

const KOREAN_WEEKDAYS = ['일', '월', '화', '수', '목', '금', '토'];

function getKoreanDayOfWeek(dateStr) {
  if (!dateStr) return '';
  try {
    const d = new Date(dateStr + 'T00:00:00');
    return KOREAN_WEEKDAYS[d.getDay()] || '';
  } catch (e) {
    return '';
  }
}

function groupTransactionsByDate(items) {
  if (!items || items.length === 0) return [];
  const groups = [];
  let currentGroup = null;

  items.forEach(item => {
    const date = item.transaction_date;
    if (!currentGroup || currentGroup.date !== date) {
      currentGroup = {
        date: date,
        items: []
      };
      groups.push(currentGroup);
    }
    currentGroup.items.push(item);
  });

  return groups;
}

async function loadMonthVariableExpenses(monthOverride) {
  const y = STATE.currentYear;
  const m = monthOverride || STATE.currentMonth;
  const catFilter = document.getElementById('filterCategory')?.value || '';

  let url = `/api/transactions?year=${y}&month=${m}&limit=500`;
  if (catFilter) url += `&category_id=${catFilter}`;

  try {
    const res = await fetch(url);
    const items = await res.json();
    STATE.cachedVarExpenses = items || [];

    // 1. Render Mobile Timeline Cards (Grouped by Date)
    renderMonthVariableExpensesMobile(items);

    // 2. Render Desktop Spreadsheet Table (Grouped by Date with Merged Date Cells)
    const tbody = document.getElementById('monthVarExpenseBody');
    if (tbody) {
      if (!items || items.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center py-6 text-slate-400 font-medium">등록된 변동 지출 내역이 없습니다.</td></tr>';
      } else {
        const groups = groupTransactionsByDate(items);
        let tableRowsHtml = '';

        groups.forEach(group => {
          const dow = getKoreanDayOfWeek(group.date);
          const dowText = dow ? ` (${dow})` : '';
          const countBadge = group.items.length > 1 ? `<span class="mt-0.5 text-[10px] font-extrabold text-slate-500 bg-slate-200/80 px-1.5 py-0.2 rounded-full">${group.items.length}건</span>` : '';

          group.items.forEach((item, idx) => {
            const isFirst = idx === 0;
            const trClass = isFirst ? 'date-group-first hover:bg-purple-50/40' : 'hover:bg-purple-50/40';

            tableRowsHtml += `<tr class="${trClass}" data-id="${item.id}">`;
            if (isFirst) {
              tableRowsHtml += `
                <td rowspan="${group.items.length}" class="date-group-cell">
                  <div class="flex flex-col items-center justify-center">
                    <span class="font-black text-slate-800 text-xs font-mono tracking-tight">${formatShortSlashDate(group.date)}</span>
                    <span class="text-[10px] text-slate-500 font-bold">${dowText}</span>
                    ${countBadge}
                  </div>
                </td>
              `;
            }

            tableRowsHtml += `
              <td class="text-center">
                <span class="badge-category" style="background-color: ${item.category_color || '#A8E6CF'}25; color: #0F172A;">${escapeHtml(item.category_name || '기타')}</span>
              </td>
              <td class="font-bold text-slate-900">${escapeHtml(item.title)}</td>
              <td class="text-center"><span class="badge-pay">${escapeHtml(item.payment_method_name || '현금')}</span></td>
              <td class="text-right font-black text-rose-600">-${formatKRW(item.amount)}원</td>
              <td class="text-slate-500 text-xs">${escapeHtml(item.memo || '')}</td>
              <td class="text-center d-edit-actions">
                <button onclick="openEditTransactionModal(${item.id})" class="btn-tx-edit">수정</button>
              </td>
              <td class="text-center d-edit-actions">
                <button onclick="deleteTransaction(${item.id})" class="btn-tx-del">삭제</button>
              </td>
            </tr>`;
          });
        });

        tbody.innerHTML = tableRowsHtml;
      }
    }
  } catch (err) {
    console.error('Failed to load month variable expenses', err);
  }
}

// Render Mobile-First Variable Expenses grouped by date:
//       분류      지출내용    수정
//   일자
//       결제수단   금액       삭제
function renderMonthVariableExpensesMobile(items) {
  const container = document.getElementById('monthVarExpenseMobileList');
  if (!container) return;

  if (!items || items.length === 0) {
    container.innerHTML = `
      <div class="glass-card p-8 text-center text-slate-500 font-medium text-sm">
        등록된 변동 지출 내역이 없습니다. ☕
      </div>
    `;
    return;
  }

  const groups = groupTransactionsByDate(items);

  const html = groups.map(group => {
    const dow = getKoreanDayOfWeek(group.date);
    const countBadge = group.items.length > 1 ? `<span class="date-spine-count">${group.items.length}건</span>` : '';

    const itemsHtml = group.items.map(item => `
      <div class="mobile-date-item-row" data-id="${item.id}">
        <!-- Row 1: 분류 + 지출내용 + 수정 버튼 -->
        <div class="item-row-top">
          <div class="flex items-center gap-1.5 min-w-0 flex-1">
            <span class="badge-category flex-shrink-0" style="background-color: ${item.category_color || '#A8E6CF'}30; color: #0F172A;">
              ${escapeHtml(item.category_name || '기타')}
            </span>
            <span class="font-bold text-slate-900 truncate text-xs sm:text-sm">
              ${escapeHtml(item.title)}
            </span>
          </div>
          <div class="d-edit-actions flex-shrink-0">
            <button type="button" onclick="openEditTransactionModal(${item.id})" class="btn-tx-edit">
              수정
            </button>
          </div>
        </div>

        <!-- Row 2: 결제수단 + 금액 + 메모 + 삭제 버튼 -->
        <div class="item-row-bottom">
          <div class="flex items-center gap-1.5 min-w-0 flex-1">
            <span class="badge-pay text-[11px] py-0.5 px-1.5 flex-shrink-0">
              ${escapeHtml(item.payment_method_name || '현금')}
            </span>
            <span class="font-black text-rose-600 text-xs sm:text-sm whitespace-nowrap">
              -${formatKRW(item.amount)}원
            </span>
            ${item.memo ? `<span class="text-[11px] text-slate-400 truncate max-w-[100px] sm:max-w-[140px]">(${escapeHtml(item.memo)})</span>` : ''}
          </div>
          <div class="d-edit-actions flex-shrink-0">
            <button type="button" onclick="deleteTransaction(${item.id})" class="btn-tx-del">
              삭제
            </button>
          </div>
        </div>
      </div>
    `).join('');

    return `
      <div class="mobile-date-group-card" data-date="${group.date}">
        <!-- Col 1: 일자 Spine (Spans all transactions on this date) -->
        <div class="mobile-date-spine">
          <span class="date-spine-slash">${formatShortSlashDate(group.date)}</span>
          <span class="date-spine-dow">${dow ? `(${dow})` : ''}</span>
          ${countBadge}
        </div>

        <!-- Col 2 & 3: Stacked Transactions on this date -->
        <div class="mobile-date-items">
          ${itemsHtml}
        </div>
      </div>
    `;
  }).join('');

  container.innerHTML = html;
}

// Single Transaction Edit Modal Handlers
function openEditTransactionModal(id) {
  const item = (STATE.cachedVarExpenses || []).find(it => it.id === id);
  if (!item) return;

  document.getElementById('editTxId').value = item.id;
  document.getElementById('editTxDate').value = item.transaction_date;
  document.getElementById('editTxTitle').value = item.title;
  document.getElementById('editTxAmount').value = item.amount;
  document.getElementById('editTxMemo').value = item.memo || '';

  // Populate Categories
  const catSelect = document.getElementById('editTxCategory');
  catSelect.innerHTML = STATE.categories.map(c => `
    <option value="${c.id}" ${c.id === item.category_id ? 'selected' : ''}>${escapeHtml(c.name)}</option>
  `).join('');

  // Populate Payment Methods
  const paySelect = document.getElementById('editTxPayment');
  paySelect.innerHTML = STATE.paymentMethods.map(p => `
    <option value="${p.id}" ${p.id === item.payment_method_id ? 'selected' : ''}>${escapeHtml(p.name)}</option>
  `).join('');

  document.getElementById('modalEditTransaction').classList.remove('hidden');
}

function closeEditTransactionModal() {
  document.getElementById('modalEditTransaction').classList.add('hidden');
}

async function submitEditTransaction(event) {
  event.preventDefault();
  const id = document.getElementById('editTxId').value;
  const payload = {
    transaction_date: document.getElementById('editTxDate').value,
    category_id: parseInt(document.getElementById('editTxCategory').value, 10),
    title: document.getElementById('editTxTitle').value.trim(),
    payment_method_id: parseInt(document.getElementById('editTxPayment').value, 10),
    amount: parseInt(document.getElementById('editTxAmount').value, 10),
    memo: document.getElementById('editTxMemo').value.trim()
  };

  try {
    const res = await fetch(`/api/transactions/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error('수정에 실패했습니다.');

    closeEditTransactionModal();
    // Refresh Month Details & KPI Cards
    await loadMonthDetail(STATE.currentMonth);
    // If on today tab, refresh today list as well
    if (STATE.currentTab === 'today') {
      loadTodayOverview();
    }
  } catch (err) {
    alert('수정 실패: ' + err.message);
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
    <tr class="cursor-pointer hover:bg-purple-50/70" onclick="switchTab(${m.month})">
      <td class="text-center font-extrabold text-purple-800">${m.month_name}</td>
      <td class="text-right font-semibold">${formatKRW(m.total_income)}</td>
      <td class="text-right font-semibold">${formatKRW(m.fixed_expense)}</td>
      <td class="text-right font-semibold">${formatKRW(m.variable_expense)}</td>
      <td class="text-right font-extrabold text-rose-600">${formatKRW(m.total_expense)}</td>
      <td class="text-right font-extrabold text-blue-700">${formatKRW(m.savings_investment)}</td>
      <td class="text-right font-extrabold text-emerald-700">${formatKRW(m.balance)}</td>
      <td class="text-center font-black text-purple-700">${m.savings_rate}%</td>
    </tr>
  `).join('');

  const totalRow = `
    <tr class="bg-purple-100/80 font-black">
      <td class="text-center text-purple-950">${data.annual_total.month_name}</td>
      <td class="text-right">${formatKRW(data.annual_total.total_income)}</td>
      <td class="text-right">${formatKRW(data.annual_total.fixed_expense)}</td>
      <td class="text-right">${formatKRW(data.annual_total.variable_expense)}</td>
      <td class="text-right text-rose-700">${formatKRW(data.annual_total.total_expense)}</td>
      <td class="text-right text-blue-800">${formatKRW(data.annual_total.savings_investment)}</td>
      <td class="text-right text-emerald-800">${formatKRW(data.annual_total.balance)}</td>
      <td class="text-center text-purple-950">${data.annual_total.savings_rate}%</td>
    </tr>
  `;

  const avgRow = `
    <tr class="bg-slate-100/90 font-bold">
      <td class="text-center text-slate-800">${data.monthly_average.month_name}</td>
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
          backgroundColor: '#A8E6CFee',
          borderColor: '#48BB78',
          borderWidth: 1.5,
          borderRadius: 6
        },
        {
          label: '총 지출',
          data: expenses,
          backgroundColor: '#FFB7B2ee',
          borderColor: '#E53E3E',
          borderWidth: 1.5,
          borderRadius: 6
        },
        {
          label: '저축 및 투자',
          data: savings,
          backgroundColor: '#BEE3F8ee',
          borderColor: '#3182CE',
          borderWidth: 1.5,
          borderRadius: 6
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'top', labels: { font: { family: 'Pretendard', size: 12, weight: 'bold' } } }
      },
      scales: {
        y: {
          ticks: {
            callback: (v) => v >= 10000 ? (v / 10000) + '만' : v,
            font: { size: 11, weight: 'bold' }
          },
          grid: { color: 'rgba(203, 213, 225, 0.4)' }
        },
        x: {
          grid: { display: false },
          ticks: { font: { size: 11, weight: 'bold' } }
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
    ctx.parentElement.innerHTML = '<div class="text-sm text-slate-500 font-bold text-center">지출 데이터가 없습니다</div>';
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
        legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 12, weight: 'bold' } } }
      }
    }
  });
}

// ====================================================================
// SECTION 4: SPENDING PATTERN ANALYTICS & VISUALIZATION
// ====================================================================

async function loadSpendingPatterns() {
  const y = STATE.currentYear;
  const m = STATE.currentMonth;

  const titleEl = document.getElementById('spendingTitle');
  if (titleEl) titleEl.textContent = `${y}년 ${m}월 소비 분석 리포트`;

  try {
    const res = await fetch(`/api/analytics/spending-patterns?year=${y}&month=${m}`);
    if (!res.ok) throw new Error('소비 패턴 분석 데이터를 불러오지 못했습니다.');
    const data = await res.json();

    // 1) AI/Smart Insight Banner
    const insightEl = document.getElementById('spendingInsightText');
    if (insightEl) insightEl.textContent = data.insight_summary || '소비 내역을 분석하여 리포트를 생성했습니다.';

    // 2) Top High-Contrast KPI Cards
    const spendTotalEl = document.getElementById('spendKpiTotal');
    if (spendTotalEl) spendTotalEl.textContent = `${formatKRW(data.total_spending)}원`;

    const spendMomEl = document.getElementById('spendKpiMoM');
    if (spendMomEl) {
      if (data.spending_diff > 0) {
        spendMomEl.className = 'text-[11px] font-extrabold block mt-1 text-rose-600';
        spendMomEl.textContent = `▲ 전월 대비 +${formatKRW(data.spending_diff)}원 (+${data.spending_diff_rate}%)`;
      } else if (data.spending_diff < 0) {
        spendMomEl.className = 'text-[11px] font-extrabold block mt-1 text-emerald-600';
        spendMomEl.textContent = `▼ 전월 대비 ${formatKRW(data.spending_diff)}원 (${data.spending_diff_rate}%)`;
      } else {
        spendMomEl.className = 'text-[11px] font-bold block mt-1 text-slate-500';
        spendMomEl.textContent = `- 전월 대비 변동 없음 (동일)`;
      }
    }

    const dailyAvgEl = document.getElementById('spendKpiDailyAvg');
    if (dailyAvgEl) dailyAvgEl.textContent = `${formatKRW(data.daily_average)}원`;

    const daysEl = document.getElementById('spendKpiDays');
    if (daysEl) {
      const daysCount = new Date(y, m, 0).getDate();
      daysEl.textContent = `${daysCount}일 기준`;
    }

    const txCountEl = document.getElementById('spendKpiTxCount');
    if (txCountEl) txCountEl.textContent = `${formatKRW(data.transaction_count)}건`;

    const avgTxEl = document.getElementById('spendKpiAvgTx');
    if (avgTxEl) avgTxEl.textContent = `건당 ${formatKRW(data.avg_per_transaction)}원`;

    const noSpendEl = document.getElementById('spendKpiNoSpend');
    if (noSpendEl) noSpendEl.textContent = `${data.no_spend_days}일`;

    const peakDayEl = document.getElementById('spendKpiPeakDay');
    if (peakDayEl) {
      if (data.peak_spending_date && data.peak_spending_amount > 0) {
        const peakFormatted = data.peak_spending_date.length > 5 ? data.peak_spending_date.slice(5) : data.peak_spending_date;
        peakDayEl.textContent = `최대: ${peakFormatted} (${formatKRW(data.peak_spending_amount)}원)`;
      } else {
        peakDayEl.textContent = '최대: -';
      }
    }

    const weekdayWeekendBadge = document.getElementById('weekdayWeekendBadge');
    if (weekdayWeekendBadge) {
      weekdayWeekendBadge.textContent = `평일 ${formatKRW(data.weekday_spending)}원 vs 주말 ${formatKRW(data.weekend_spending)}원`;
    }

    // 3) Visual Charts
    STATE.spendingCategoryData = data.categories;
    STATE.spendingCategoryDepth = 1;
    STATE.selectedCategoryItem = null;
    renderSpendingCategoryChart(data.categories);
    renderSpendingPaymentChart(data.payment_methods);
    renderSpendingWeeklyChart(data.weekly);
    renderSpendingDayOfWeekChart(data.day_of_week);

    // 4) Grids / Tables
    renderSpendingGrids(data);

  } catch (err) {
    console.error('Failed to load spending patterns', err);
    const insightEl = document.getElementById('spendingInsightText');
    if (insightEl) insightEl.textContent = '소비 패턴 분석 중 오류가 발생했습니다: ' + err.message;
  }
}

const SUB_CATEGORY_PALETTE = [
  '#4F46E5', '#2563EB', '#0284C7', '#0D9488', '#059669',
  '#D97706', '#EA580C', '#DC2626', '#DB2777', '#7C3AED',
  '#65A30D', '#0891B2', '#9333EA', '#475569'
];

function updateCategoryCenterInfo(label, amount, subText) {
  const lblEl = document.getElementById('categoryCenterLabel');
  const amtEl = document.getElementById('categoryCenterAmount');
  const subEl = document.getElementById('categoryCenterSub');
  if (lblEl) lblEl.textContent = label;
  if (amtEl) amtEl.textContent = typeof amount === 'number' ? `${formatKRW(amount)}원` : amount;
  if (subEl) subEl.textContent = subText || '';
}

function executeSelectedCategoryDrilldown() {
  if (STATE.selected1DepthCategory) {
    drilldownSpendingCategory(STATE.selected1DepthCategory);
  }
}

function resetCategoryChartToDepth1() {
  STATE.spendingCategoryDepth = 1;
  STATE.selectedCategoryItem = null;
  STATE.selected1DepthCategory = null;

  const modeToggle = document.getElementById('categoryChartModeToggle');
  if (modeToggle) {
    modeToggle.classList.add('hidden');
    modeToggle.classList.remove('inline-flex');
  }

  const btnDrilldown = document.getElementById('btnExecuteDrilldown');
  if (btnDrilldown) {
    btnDrilldown.classList.add('hidden');
    btnDrilldown.classList.remove('inline-flex');
  }

  const btnFooterBack = document.getElementById('btnFooterBack');
  if (btnFooterBack) {
    btnFooterBack.classList.add('hidden');
    btnFooterBack.classList.remove('inline-flex');
  }

  renderSpendingCategoryChart(STATE.spendingCategoryData);
}

function setCategoryChart2DepthMode(mode) {
  STATE.spendingCategory2DepthMode = mode; // 'sub' or 'merchant'

  // Update button active states
  const btnSub = document.getElementById('btnSubCategoryMode');
  const btnMerch = document.getElementById('btnMerchantMode');

  if (mode === 'sub') {
    if (btnSub) {
      btnSub.className = 'px-2.5 py-1 rounded-md bg-white text-indigo-600 shadow-sm transition-all cursor-pointer font-extrabold';
    }
    if (btnMerch) {
      btnMerch.className = 'px-2.5 py-1 rounded-md text-slate-500 hover:text-slate-800 transition-all cursor-pointer font-bold';
    }
  } else {
    if (btnSub) {
      btnSub.className = 'px-2.5 py-1 rounded-md text-slate-500 hover:text-slate-800 transition-all cursor-pointer font-bold';
    }
    if (btnMerch) {
      btnMerch.className = 'px-2.5 py-1 rounded-md bg-white text-indigo-600 shadow-sm transition-all cursor-pointer font-extrabold';
    }
  }

  if (STATE.spendingCategoryDepth === 2 && STATE.selectedCategoryItem) {
    drilldownSpendingCategory(STATE.selectedCategoryItem);
  }
}

function selectCategoryFromTable(categoryId) {
  if (!STATE.spendingCategoryData) return;
  const target = STATE.spendingCategoryData.find(c => c.category_id === categoryId);
  if (target && target.amount > 0) {
    drilldownSpendingCategory(target);
    const container = document.getElementById('categoryChartContainer');
    if (container) {
      container.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }
}

function drilldownSpendingCategory(catItem) {
  if (!catItem) return;
  STATE.spendingCategoryDepth = 2;
  STATE.selectedCategoryItem = catItem;
  STATE.selected1DepthCategory = null;

  const ctx = document.getElementById('chartCategoryDonut');
  if (!ctx) return;
  if (STATE.spendingCategoryChart) STATE.spendingCategoryChart.destroy();

  const isSubMode = STATE.spendingCategory2DepthMode === 'sub';
  const modeLabel = isSubMode ? '소분류별' : '가맹점별';

  // 1) UI Header & Badge Updates
  const titleEl = document.getElementById('categoryChartTitle');
  if (titleEl) {
    titleEl.innerHTML = `<span>🍩 <span class="text-indigo-600 font-black cursor-pointer hover:underline" onclick="resetCategoryChartToDepth1()" title="전체 카테고리로 돌아가기">${escapeHtml(catItem.name)}</span> <span class="text-xs font-bold text-slate-500">(${modeLabel})</span></span>`;
  }
  const backBtn = document.getElementById('btnCategoryChartBack');
  if (backBtn) {
    backBtn.classList.remove('hidden');
    backBtn.classList.add('inline-flex');
  }

  // 2) Toggle Bar Show & Sync
  const modeToggle = document.getElementById('categoryChartModeToggle');
  if (modeToggle) {
    modeToggle.classList.remove('hidden');
    modeToggle.classList.add('inline-flex');
  }
  const btnSub = document.getElementById('btnSubCategoryMode');
  const btnMerch = document.getElementById('btnMerchantMode');
  if (btnSub && btnMerch) {
    if (isSubMode) {
      btnSub.className = 'px-2.5 py-1 rounded-md bg-white text-indigo-600 shadow-sm transition-all cursor-pointer font-extrabold';
      btnMerch.className = 'px-2.5 py-1 rounded-md text-slate-500 hover:text-slate-800 transition-all cursor-pointer font-bold';
    } else {
      btnSub.className = 'px-2.5 py-1 rounded-md text-slate-500 hover:text-slate-800 transition-all cursor-pointer font-bold';
      btnMerch.className = 'px-2.5 py-1 rounded-md bg-white text-indigo-600 shadow-sm transition-all cursor-pointer font-extrabold';
    }
  }

  const badgeEl = document.getElementById('categoryChartSubBadge');
  if (badgeEl) {
    badgeEl.textContent = `총 ${formatKRW(catItem.amount)}원 (${catItem.percentage}%)`;
  }

  // 3) Footer Action Bar Updates for 2Depth
  const btnDrilldown = document.getElementById('btnExecuteDrilldown');
  if (btnDrilldown) {
    btnDrilldown.classList.add('hidden');
    btnDrilldown.classList.remove('inline-flex');
  }
  const btnFooterBack = document.getElementById('btnFooterBack');
  if (btnFooterBack) {
    btnFooterBack.classList.remove('hidden');
    btnFooterBack.classList.add('inline-flex');
  }
  const hintEl = document.getElementById('categoryChartHintText');
  if (hintEl) {
    hintEl.textContent = '💡 세부 항목을 터치하면 중앙에 상세 정보가 표시되며, [전체 카테고리] 버튼으로 언제든 복귀할 수 있습니다.';
  }

  // 4) Select dataset (sub_items vs merchant_items)
  const rawItems = isSubMode ? (catItem.sub_items || []) : (catItem.merchant_items || []);
  const validItems = rawItems.filter(s => s.amount > 0);
  let displayItems = [];

  if (validItems.length === 0) {
    displayItems = [{
      name: catItem.name,
      amount: catItem.amount,
      count: catItem.count || 1,
      percentage: 100.0
    }];
  } else if (validItems.length > 7) {
    const top7 = validItems.slice(0, 7);
    const rest = validItems.slice(7);
    const restAmount = rest.reduce((acc, cur) => acc + cur.amount, 0);
    const restCount = rest.reduce((acc, cur) => acc + cur.count, 0);
    const restPct = catItem.amount > 0 ? Math.round((restAmount / catItem.amount * 100) * 10) / 10 : 0.0;
    displayItems = [
      ...top7,
      {
        name: `기타 (외 ${rest.length}개)`,
        amount: restAmount,
        count: restCount,
        percentage: restPct
      }
    ];
  } else {
    displayItems = [...validItems];
  }

  const labels = displayItems.map(s => s.name);
  const data = displayItems.map(s => s.amount);
  const colors = displayItems.map((s, idx) => {
    if (idx === 0 && catItem.color_hex) return catItem.color_hex;
    return SUB_CATEGORY_PALETTE[idx % SUB_CATEGORY_PALETTE.length];
  });

  // Set default center info for 2Depth
  updateCategoryCenterInfo(catItem.name, catItem.amount, `전체의 ${catItem.percentage}% (${catItem.count || 0}건)`);

  // 5) Render 2Depth Pie/Donut Chart (Touch displays center info, does NOT navigate away!)
  STATE.spendingCategoryChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: data,
        backgroundColor: colors,
        borderWidth: 2,
        borderColor: '#ffffff',
        hoverOffset: 8
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '66%',
      onClick: (event, elements) => {
        // [모바일/PC 친화 UX] 2Depth에서는 터치/클릭 시 1Depth로 복귀하지 않고 중앙 인포머에 해당 세부 항목 정보 표시
        if (elements && elements.length > 0) {
          const idx = elements[0].index;
          const item = displayItems[idx];
          if (item) {
            const countText = item.count ? ` (${item.count}건)` : '';
            updateCategoryCenterInfo(item.name, item.amount, `${item.percentage}%${countText}`);
            if (hintEl) hintEl.textContent = `💡 '${item.name}': ${formatKRW(item.amount)}원 (${item.percentage}%${countText})`;
          }
        } else {
          // 도넛 빈 곳 터치 시 2Depth 카테고리 전체 요약으로 복귀
          updateCategoryCenterInfo(catItem.name, catItem.amount, `전체의 ${catItem.percentage}% (${catItem.count || 0}건)`);
        }
      },
      onHover: (event, elements) => {
        const canvas = event.chart.canvas;
        canvas.style.cursor = elements && elements.length > 0 ? 'pointer' : 'default';
        if (elements && elements.length > 0) {
          const idx = elements[0].index;
          const item = displayItems[idx];
          if (item) {
            const countText = item.count ? ` (${item.count}건)` : '';
            updateCategoryCenterInfo(item.name, item.amount, `${item.percentage}%${countText}`);
          }
        }
      },
      plugins: {
        legend: {
          position: 'right',
          labels: {
            font: { family: 'Pretendard', size: 11, weight: 'bold' },
            boxWidth: 12,
            padding: 8
          }
        },
        tooltip: {
          enabled: false
        }
      }
    }
  });
}

function renderSpendingCategoryChart(categories) {
  STATE.spendingCategoryDepth = 1;
  STATE.selectedCategoryItem = null;
  STATE.selected1DepthCategory = null;

  const ctx = document.getElementById('chartCategoryDonut');
  if (!ctx) return;
  if (STATE.spendingCategoryChart) STATE.spendingCategoryChart.destroy();

  // Reset Header & Badges to 1Depth
  const titleEl = document.getElementById('categoryChartTitle');
  if (titleEl) {
    titleEl.innerHTML = '<span>🍩 카테고리별 소비 점유율</span>';
  }
  const backBtn = document.getElementById('btnCategoryChartBack');
  if (backBtn) {
    backBtn.classList.add('hidden');
    backBtn.classList.remove('inline-flex');
  }
  const modeToggle = document.getElementById('categoryChartModeToggle');
  if (modeToggle) {
    modeToggle.classList.add('hidden');
    modeToggle.classList.remove('inline-flex');
  }
  const badgeEl = document.getElementById('categoryChartSubBadge');
  if (badgeEl) {
    badgeEl.textContent = '지출 비중(%)';
  }
  const btnDrilldown = document.getElementById('btnExecuteDrilldown');
  if (btnDrilldown) {
    btnDrilldown.classList.add('hidden');
    btnDrilldown.classList.remove('inline-flex');
  }
  const btnFooterBack = document.getElementById('btnFooterBack');
  if (btnFooterBack) {
    btnFooterBack.classList.add('hidden');
    btnFooterBack.classList.remove('inline-flex');
  }
  const hintEl = document.getElementById('categoryChartHintText');
  if (hintEl) {
    hintEl.textContent = '💡 파이 조각을 탭하여 상세 정보를 확인하고, 세부 내역을 조회할 수 있습니다.';
  }

  const validCats = (categories || []).filter(c => c.amount > 0);
  const totalSpendSum = validCats.reduce((acc, c) => acc + c.amount, 0);

  // Set default center info for 1Depth
  updateCategoryCenterInfo('당월 총 지출', totalSpendSum, '100%');

  if (validCats.length === 0) {
    STATE.spendingCategoryChart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['내역 없음'],
        datasets: [{ data: [1], backgroundColor: ['#E2E8F0'], borderWidth: 1 }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '68%',
        plugins: {
          legend: { position: 'bottom', labels: { font: { family: 'Pretendard', size: 11, weight: 'bold' } } },
          tooltip: { enabled: false }
        }
      }
    });
    return;
  }

  const labels = validCats.map(c => c.name);
  const data = validCats.map(c => c.amount);
  const colors = validCats.map(c => c.color_hex || '#94A3B8');

  let lastTapIndex = -1;
  let lastTapTime = 0;

  STATE.spendingCategoryChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: data,
        backgroundColor: colors,
        borderWidth: 2,
        borderColor: '#ffffff',
        hoverOffset: 10
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '68%',
      onClick: (event, elements) => {
        if (!elements || elements.length === 0) {
          // 배경 탭 시 선택 해제 및 전체 합계 복귀
          STATE.selected1DepthCategory = null;
          updateCategoryCenterInfo('당월 총 지출', totalSpendSum, '100%');
          if (btnDrilldown) {
            btnDrilldown.classList.add('hidden');
            btnDrilldown.classList.remove('inline-flex');
          }
          if (hintEl) hintEl.textContent = '💡 파이 조각을 탭하여 상세 정보를 확인하고, 세부 내역을 조회할 수 있습니다.';
          return;
        }

        const index = elements[0].index;
        const clickedCat = validCats[index];
        if (!clickedCat) return;

        const currentTime = new Date().getTime();
        const tapLength = currentTime - lastTapTime;
        const isDoubleTapOrSecondClick = (lastTapIndex === index && tapLength < 500) || (STATE.selected1DepthCategory && STATE.selected1DepthCategory.category_id === clickedCat.category_id);

        STATE.selected1DepthCategory = clickedCat;
        lastTapIndex = index;
        lastTapTime = currentTime;

        // 1) 중앙 인포머 즉시 업데이트 (모바일 손가락 가림 문제 완벽 해결)
        updateCategoryCenterInfo(clickedCat.name, clickedCat.amount, `${clickedCat.percentage}% (${clickedCat.count || 0}건)`);

        // 2) 하단에 명시적인 세부내역 보기 버튼 노출
        if (btnDrilldown) {
          btnDrilldown.classList.remove('hidden');
          btnDrilldown.classList.add('inline-flex');
          const btnText = document.getElementById('btnExecuteDrilldownText');
          if (btnText) {
            btnText.textContent = `🔍 '${clickedCat.name}' 세부 내역 보기`;
          }
        }
        if (hintEl) {
          hintEl.innerHTML = `💡 <strong>'${escapeHtml(clickedCat.name)}'</strong> 선택됨. 아래 [세부 내역 보기] 버튼을 누르거나 한 번 더 터치하면 진입합니다.`;
        }

        // 3) 더블 탭(또는 같은 슬라이스를 두 번 탭/클릭) 시 즉시 진입
        if (isDoubleTapOrSecondClick && tapLength > 50) {
          drilldownSpendingCategory(clickedCat);
        }
      },
      onHover: (event, elements) => {
        const canvas = event.chart.canvas;
        canvas.style.cursor = elements && elements.length > 0 ? 'pointer' : 'default';
        if (elements && elements.length > 0) {
          const index = elements[0].index;
          const hoveredCat = validCats[index];
          if (hoveredCat) {
            updateCategoryCenterInfo(hoveredCat.name, hoveredCat.amount, `${hoveredCat.percentage}% (${hoveredCat.count || 0}건)`);
          }
        } else if (!STATE.selected1DepthCategory) {
          updateCategoryCenterInfo('당월 총 지출', totalSpendSum, '100%');
        }
      },
      plugins: {
        legend: {
          position: 'right',
          labels: {
            font: { family: 'Pretendard', size: 11, weight: 'bold' },
            boxWidth: 12,
            padding: 10
          }
        },
        tooltip: {
          enabled: false
        }
      }
    }
  });
}

function renderSpendingPaymentChart(paymentMethods) {
  const ctx = document.getElementById('chartPaymentMethodPie');
  if (!ctx) return;
  if (STATE.spendingPaymentChart) STATE.spendingPaymentChart.destroy();

  const validPays = (paymentMethods || []).filter(p => p.amount > 0);
  if (validPays.length === 0) {
    STATE.spendingPaymentChart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['내역 없음'],
        datasets: [{ data: [1], backgroundColor: ['#E2E8F0'], borderWidth: 1 }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom', labels: { font: { family: 'Pretendard', size: 11, weight: 'bold' } } },
          tooltip: { enabled: false }
        }
      }
    });
    return;
  }

  const palette = ['#3B82F6', '#10B981', '#F59E0B', '#8B5CF6', '#EC4899', '#06B6D4', '#64748B', '#F97316', '#6366F1', '#14B8A6'];
  const labels = validPays.map(p => p.name);
  const data = validPays.map(p => p.amount);
  const colors = validPays.map((p, idx) => palette[idx % palette.length]);

  STATE.spendingPaymentChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: data,
        backgroundColor: colors,
        borderWidth: 2,
        borderColor: '#ffffff',
        hoverOffset: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '62%',
      plugins: {
        legend: {
          position: 'right',
          labels: {
            font: { family: 'Pretendard', size: 11, weight: 'bold' },
            boxWidth: 12,
            padding: 10
          }
        },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const label = ctx.label || '';
              const val = ctx.raw || 0;
              const pay = validPays[ctx.dataIndex];
              const pct = pay ? pay.percentage : 0;
              return ` ${label}: ${formatKRW(val)}원 (${pct}%)`;
            }
          }
        }
      }
    }
  });
}

function renderSpendingWeeklyChart(weeklyRhythm) {
  const ctx = document.getElementById('chartWeeklyBar');
  if (!ctx) return;
  if (STATE.spendingWeeklyChart) STATE.spendingWeeklyChart.destroy();

  const weeks = weeklyRhythm || [];
  const labels = weeks.map(w => w.week_label);
  const data = weeks.map(w => w.amount);

  STATE.spendingWeeklyChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: '주차별 소비액',
        data: data,
        backgroundColor: '#8B5CF6cc',
        borderColor: '#7C3AED',
        borderWidth: 1.5,
        borderRadius: 8
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => ` ${ctx.dataset.label}: ${formatKRW(ctx.raw)}원`
          }
        }
      },
      scales: {
        y: {
          ticks: {
            callback: (v) => v >= 10000 ? (v / 10000) + '만' : v,
            font: { family: 'Pretendard', size: 11, weight: 'bold' }
          },
          grid: { color: 'rgba(203, 213, 225, 0.4)' }
        },
        x: {
          grid: { display: false },
          ticks: { font: { family: 'Pretendard', size: 11, weight: 'bold' } }
        }
      }
    }
  });
}

function renderSpendingDayOfWeekChart(dayOfWeekRhythm) {
  const ctx = document.getElementById('chartDayOfWeekBar');
  if (!ctx) return;
  if (STATE.spendingDayOfWeekChart) STATE.spendingDayOfWeekChart.destroy();

  const days = dayOfWeekRhythm || [];
  const labels = days.map(d => d.day_name);
  const data = days.map(d => d.amount);
  const bgColors = days.map(d => (d.day_name === '토' || d.day_name === '일') ? '#EC4899cc' : '#6366F1cc');
  const borderColors = days.map(d => (d.day_name === '토' || d.day_name === '일') ? '#DB2777' : '#4F46E5');

  STATE.spendingDayOfWeekChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: '요일별 소비액',
        data: data,
        backgroundColor: bgColors,
        borderColor: borderColors,
        borderWidth: 1.5,
        borderRadius: 8
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const d = days[ctx.dataIndex];
              const kind = (d && (d.day_name === '토' || d.day_name === '일')) ? '주말' : '평일';
              return ` ${ctx.label}요일 (${kind}): ${formatKRW(ctx.raw)}원 (${d ? d.count : 0}건)`;
            }
          }
        }
      },
      scales: {
        y: {
          ticks: {
            callback: (v) => v >= 10000 ? (v / 10000) + '만' : v,
            font: { family: 'Pretendard', size: 11, weight: 'bold' }
          },
          grid: { color: 'rgba(203, 213, 225, 0.4)' }
        },
        x: {
          grid: { display: false },
          ticks: { font: { family: 'Pretendard', size: 11, weight: 'bold' } }
        }
      }
    }
  });
}

function renderSpendingGrids(data) {
  // 1) Category MoM Grid
  const catTbody = document.getElementById('spendCategoryTableBody');
  if (catTbody) {
    if (!data.categories || data.categories.length === 0) {
      catTbody.innerHTML = '<tr><td colspan="6" class="py-6 text-center text-slate-400 font-bold">당월 소비 내역이 없습니다.</td></tr>';
    } else {
      catTbody.innerHTML = data.categories.map(cat => {
        let momBadge = '<span class="text-slate-400 font-bold">-</span>';
        if (cat.diff_amount > 0) {
          momBadge = `<span class="text-rose-600 font-black">▲ +${formatKRW(cat.diff_amount)}원</span>`;
        } else if (cat.diff_amount < 0) {
          momBadge = `<span class="text-emerald-600 font-black">▼ ${formatKRW(cat.diff_amount)}원</span>`;
        }
        return `
          <tr class="hover:bg-indigo-50/70 transition border-b border-slate-100 cursor-pointer group" onclick="selectCategoryFromTable(${cat.category_id})" title="클릭하여 ${escapeHtml(cat.name)} 세부 점유율 파이그래프 보기">
            <td class="font-extrabold text-slate-900 flex items-center gap-2 py-2.5 px-3">
              <span class="w-3 h-3 rounded-full flex-shrink-0" style="background-color: ${cat.color_hex || '#94A3B8'}"></span>
              <span class="group-hover:text-indigo-600 transition-colors">${escapeHtml(cat.name)}</span>
              <i class="fas fa-chevron-right text-[10px] text-slate-300 group-hover:text-indigo-500 opacity-0 group-hover:opacity-100 transition-opacity ml-1"></i>
            </td>
            <td class="text-right font-extrabold text-rose-600 py-2.5 px-3 font-mono">${formatKRW(cat.amount)}</td>
            <td class="text-right font-bold text-slate-700 py-2.5 px-3">${cat.percentage}%</td>
            <td class="text-right font-semibold text-slate-500 py-2.5 px-3 font-mono">${formatKRW(cat.prev_amount)}</td>
            <td class="text-right py-2.5 px-3">${momBadge}</td>
            <td class="text-right font-bold text-slate-700 py-2.5 px-3">${cat.count}건</td>
          </tr>
        `;
      }).join('');
    }
  }

  // 2) Top 10 Merchants Ranking Grid
  const merchTbody = document.getElementById('spendTopMerchantsBody');
  if (merchTbody) {
    if (!data.top_merchants || data.top_merchants.length === 0) {
      merchTbody.innerHTML = '<tr><td colspan="5" class="py-6 text-center text-slate-400 font-bold">가맹점 지출 내역이 없습니다.</td></tr>';
    } else {
      merchTbody.innerHTML = data.top_merchants.map(m => {
        let rankBadge = `<span class="w-5 h-5 rounded-full inline-flex items-center justify-center font-black text-slate-600 bg-slate-100 text-[11px]">${m.rank}</span>`;
        if (m.rank === 1) rankBadge = '<span class="w-5 h-5 rounded-full inline-flex items-center justify-center font-black text-amber-900 bg-amber-200 text-[11px]">1</span>';
        else if (m.rank === 2) rankBadge = '<span class="w-5 h-5 rounded-full inline-flex items-center justify-center font-black text-slate-800 bg-slate-200 text-[11px]">2</span>';
        else if (m.rank === 3) rankBadge = '<span class="w-5 h-5 rounded-full inline-flex items-center justify-center font-black text-amber-800 bg-amber-100 text-[11px]">3</span>';

        return `
          <tr class="hover:bg-slate-50 transition border-b border-slate-100">
            <td class="text-center py-2.5 px-2">${rankBadge}</td>
            <td class="font-extrabold text-slate-900 py-2.5 px-3">${escapeHtml(m.merchant)}</td>
            <td class="text-right font-black text-rose-600 py-2.5 px-3 font-mono">${formatKRW(m.amount)}</td>
            <td class="text-right font-bold text-slate-700 py-2.5 px-3">${m.percentage}%</td>
            <td class="text-center font-bold text-slate-600 py-2.5 px-2">${m.count}건</td>
          </tr>
        `;
      }).join('');
    }
  }
}

// ====================================================================
// SECTION 5: CARD STATEMENT UPLOAD & DEDUPLICATION MODAL HANDLERS
// ====================================================================

function openCardUploadModal() {
  const modal = document.getElementById('modalCardUpload');
  if (!modal) return;

  // Month selector populate
  const mSelect = document.getElementById('cardTargetMonth');
  if (mSelect) {
    mSelect.innerHTML = '';
    for (let i = 1; i <= 12; i++) {
      const opt = document.createElement('option');
      opt.value = i;
      opt.textContent = `${i}월`;
      if (i === STATE.currentMonth) opt.selected = true;
      mSelect.appendChild(opt);
    }
  }

  const ySelect = document.getElementById('cardTargetYear');
  if (ySelect) ySelect.value = STATE.currentYear;

  // Reset file input & UI
  const fileInput = document.getElementById('cardStatementFileInput');
  if (fileInput) fileInput.value = '';
  STATE.cardUploadFile = null;
  STATE.cardPreviewItems = [];

  const promptText = document.getElementById('cardUploadFileNamePrompt');
  if (promptText) {
    promptText.textContent = '카드사 청구내역 엑셀 파일(.xlsx, .xls)을 선택하거나 드래그하세요';
  }

  const analyzeBtn = document.getElementById('btnAnalyzeCardFile');
  if (analyzeBtn) {
    analyzeBtn.disabled = true;
    analyzeBtn.classList.add('opacity-50', 'cursor-not-allowed');
    analyzeBtn.innerHTML = '<span>🔍 청구내역 분석 및 중복 검사 시작</span>';
  }

  // Show Step 1, hide Step 2
  document.getElementById('cardUploadStep1')?.classList.remove('hidden');
  document.getElementById('cardUploadStep2')?.classList.add('hidden');

  modal.classList.remove('hidden');
}

function closeCardUploadModal(e) {
  if (e && e.target && e.target.id !== 'modalCardUpload' && !e.target.closest('button[onclick="closeCardUploadModal()"]')) return;
  document.getElementById('modalCardUpload')?.classList.add('hidden');
}

function onCardFileSelected(event) {
  const file = event.target.files && event.target.files[0];
  if (!file) return;

  STATE.cardUploadFile = file;
  const promptText = document.getElementById('cardUploadFileNamePrompt');
  if (promptText) {
    const sizeKb = Math.round(file.size / 1024);
    promptText.innerHTML = `📄 <span class="text-blue-700 font-extrabold">${escapeHtml(file.name)}</span> (${sizeKb} KB)`;
  }

  const analyzeBtn = document.getElementById('btnAnalyzeCardFile');
  if (analyzeBtn) {
    analyzeBtn.disabled = false;
    analyzeBtn.classList.remove('opacity-50', 'cursor-not-allowed');
  }
}

function resetCardUploadStep() {
  document.getElementById('cardUploadStep1')?.classList.remove('hidden');
  document.getElementById('cardUploadStep2')?.classList.add('hidden');
}

async function analyzeCardFile() {
  if (!STATE.cardUploadFile) {
    alert('업로드할 카드사 청구서 파일을 선택해주세요.');
    return;
  }

  const btn = document.getElementById('btnAnalyzeCardFile');
  btn.disabled = true;
  btn.innerHTML = '<span>⏳ 청구내역 분석 및 중복 대조 중...</span>';

  try {
    const formData = new FormData();
    formData.append('file', STATE.cardUploadFile);
    formData.append('target_year', document.getElementById('cardTargetYear').value);
    formData.append('target_month', document.getElementById('cardTargetMonth').value);

    const res = await fetch('/api/cards/preview', {
      method: 'POST',
      body: formData
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || '파일 분석에 실패했습니다.');

    // Save to state
    STATE.cardPreviewItems = data.items;

    // Header info
    const badge = document.getElementById('cardPreviewIssuerBadge');
    if (badge) {
      const issuerLabel = data.issuer_name || data.issuer;
      badge.textContent = issuerLabel;
      if (issuerLabel.includes('삼성')) {
        badge.className = 'px-3 py-1 rounded-full text-xs font-black bg-blue-600 text-white shadow-xs';
      } else if (issuerLabel.includes('신한')) {
        badge.className = 'px-3 py-1 rounded-full text-xs font-black bg-indigo-600 text-white shadow-xs';
      } else if (issuerLabel.includes('현대')) {
        badge.className = 'px-3 py-1 rounded-full text-xs font-black bg-slate-900 text-white shadow-xs';
      } else {
        badge.className = 'px-3 py-1 rounded-full text-xs font-black bg-purple-600 text-white shadow-xs';
      }
    }

    const monthDisplay = data.statement_month ? `${data.statement_month} 청구내역` : `${document.getElementById('cardTargetYear').value}년 ${document.getElementById('cardTargetMonth').value}월 청구내역`;
    document.getElementById('cardPreviewMonthText').textContent = monthDisplay;
    document.getElementById('cardPreviewCountText').textContent = `(총 ${data.total_count}건)`;
    document.getElementById('cardPreviewTotalAmtText').textContent = `청구 총액: ${formatKRW(data.total_amount)}원`;

    // Duplicate alert banner
    const alertBanner = document.getElementById('cardDuplicateAlertBanner');
    const alertText = document.getElementById('cardDuplicateAlertText');
    if (data.duplicate_count > 0) {
      alertText.textContent = `기존 수기 내역과 일자·금액이 일치하는 중복 의심 항목 ${data.duplicate_count}건이 발견되었습니다.`;
      alertBanner.classList.remove('hidden');
    } else {
      alertBanner.classList.add('hidden');
    }

    // Render Preview Table
    renderCardPreviewTable();

    // Switch view to step 2
    document.getElementById('cardUploadStep1').classList.add('hidden');
    document.getElementById('cardUploadStep2').classList.remove('hidden');

    updateCardImportSummary();
  } catch (err) {
    alert('청구서 분석 오류: ' + err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span>🔍 청구내역 분석 및 중복 검사 시작</span>';
  }
}

function renderCardPreviewTable() {
  const tbody = document.getElementById('cardPreviewTableBody');
  if (!tbody) return;

  if (!STATE.cardPreviewItems || STATE.cardPreviewItems.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" class="py-6 text-center text-slate-400 font-bold">인식된 청구 내역이 없습니다.</td></tr>';
    return;
  }

  tbody.innerHTML = STATE.cardPreviewItems.map((item, idx) => {
    const isDup = item.is_duplicate;
    const isSkip = item.action === 'skip';

    // Status badge
    let statusBadge = isDup 
      ? '<span class="px-2 py-0.5 rounded-full text-[10px] font-black bg-amber-100 text-amber-800 border border-amber-300 whitespace-nowrap">⚠️ 중복의심</span>'
      : '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300 whitespace-nowrap">신규</span>';

    // Action select options
    let actionSelect = `
      <select class="glass-input text-xs py-1 px-1.5 font-bold ${isSkip ? 'text-slate-400 bg-slate-100' : 'text-slate-800'}" onchange="onCardItemActionChange(${idx}, this.value)">
        <option value="add_new" ${item.action === 'add_new' ? 'selected' : ''}>➕ 추가</option>
        <option value="merge" ${item.action === 'merge' ? 'selected' : ''} ${!item.existing_expense_id ? 'disabled' : ''}>🔄 덮어쓰기</option>
        <option value="skip" ${item.action === 'skip' ? 'selected' : ''}>⏭️ 건너뛰기</option>
      </select>
    `;

    // Category options
    let catSelect = `
      <select class="glass-input text-xs py-1 px-1.5 font-bold" onchange="onCardItemFieldChange(${idx}, 'category_id', Number(this.value))">
        ${STATE.categories.map(c => `
          <option value="${c.id}" ${c.id === item.category_id ? 'selected' : ''}>${escapeHtml(c.name)}</option>
        `).join('')}
      </select>
    `;

    const rowBgClass = isSkip ? 'bg-slate-50 opacity-60' : (isDup ? 'bg-amber-50/40' : 'hover:bg-slate-50/70');
    const amtColorClass = item.amount < 0 ? 'text-pink-600 font-black' : 'text-slate-900 font-black';

    return `
      <tr class="${rowBgClass} transition border-b border-slate-100" id="card-row-${idx}">
        <td class="py-2 px-3">${statusBadge}</td>
        <td class="py-2 px-2">${actionSelect}</td>
        <td class="py-2 px-2 font-mono text-[11px] font-bold text-slate-600 whitespace-nowrap">${item.transaction_date}</td>
        <td class="py-2 px-3 font-extrabold text-slate-900 max-w-[150px] truncate" title="${escapeHtml(item.title)}">
          <input type="text" class="glass-input text-xs py-1 px-1.5 w-full font-bold" value="${escapeHtml(item.title)}" onchange="onCardItemFieldChange(${idx}, 'title', this.value)">
        </td>
        <td class="py-2 px-3">${catSelect}</td>
        <td class="py-2 px-3 text-right ${amtColorClass} font-mono whitespace-nowrap">${formatKRW(item.amount)}원</td>
        <td class="py-2 px-2 text-slate-700 font-bold whitespace-nowrap">${escapeHtml(item.payment_method_name)}</td>
        <td class="py-2 px-3 text-slate-500 text-[11px] max-w-[200px] truncate" title="${escapeHtml((item.memo || '') + (item.duplicate_reason ? ' | ' + item.duplicate_reason : ''))}">
          ${item.duplicate_reason ? `<span class="text-amber-800 font-bold block">${escapeHtml(item.duplicate_reason)}</span>` : ''}
          <span class="text-slate-500">${escapeHtml(item.memo || '-')}</span>
        </td>
      </tr>
    `;
  }).join('');
}

function onCardItemActionChange(idx, action) {
  if (!STATE.cardPreviewItems[idx]) return;
  STATE.cardPreviewItems[idx].action = action;
  const row = document.getElementById(`card-row-${idx}`);
  if (row) {
    if (action === 'skip') {
      row.className = 'bg-slate-50 opacity-60 transition border-b border-slate-100';
    } else if (STATE.cardPreviewItems[idx].is_duplicate) {
      row.className = 'bg-amber-50/40 transition border-b border-slate-100';
    } else {
      row.className = 'hover:bg-slate-50/70 transition border-b border-slate-100';
    }
  }
  updateCardImportSummary();
}

function onCardItemFieldChange(idx, field, value) {
  if (!STATE.cardPreviewItems[idx]) return;
  STATE.cardPreviewItems[idx][field] = value;
}

function setAllDuplicateActions(action) {
  let count = 0;
  STATE.cardPreviewItems.forEach((item) => {
    if (item.is_duplicate) {
      item.action = action;
      count++;
    }
  });
  if (count === 0) {
    alert('중복 의심 항목이 없습니다.');
    return;
  }
  renderCardPreviewTable();
  updateCardImportSummary();
}

function updateCardImportSummary() {
  let addCount = 0;
  let mergeCount = 0;
  let skipCount = 0;

  STATE.cardPreviewItems.forEach(item => {
    if (item.action === 'add_new') addCount++;
    else if (item.action === 'merge') mergeCount++;
    else if (item.action === 'skip') skipCount++;
  });

  const totalImport = addCount + mergeCount;
  const summaryEl = document.getElementById('cardImportSelectedSummary');
  if (summaryEl) {
    summaryEl.innerHTML = `신규 추가: <span class="text-emerald-700 font-black">${addCount}건</span>, 병합/수정: <span class="text-amber-800 font-black">${mergeCount}건</span>, 제외: <span class="text-slate-500 font-bold">${skipCount}건</span> (총 <span class="text-blue-700 font-black">${totalImport}건</span> 반영)`;
  }

  const confirmBtn = document.getElementById('btnConfirmCardImport');
  if (confirmBtn) {
    if (totalImport === 0) {
      confirmBtn.disabled = true;
      confirmBtn.classList.add('opacity-50', 'cursor-not-allowed');
    } else {
      confirmBtn.disabled = false;
      confirmBtn.classList.remove('opacity-50', 'cursor-not-allowed');
    }
  }
}

async function confirmCardImport() {
  const itemsToConfirm = STATE.cardPreviewItems.filter(item => item.action !== 'skip');
  if (itemsToConfirm.length === 0) {
    alert('가계부에 반영할 항목이 없습니다. (모두 건너뛰기 됨)');
    return;
  }

  const confirmBtn = document.getElementById('btnConfirmCardImport');
  confirmBtn.disabled = true;
  confirmBtn.innerHTML = '<span>⏳ 가계부 반영 중...</span>';

  try {
    const payload = {
      items: itemsToConfirm.map(item => ({
        transaction_date: item.transaction_date,
        title: item.title,
        amount: item.amount,
        category_id: item.category_id,
        payment_method_id: item.payment_method_id,
        memo: item.memo || '',
        action: item.action,
        existing_expense_id: item.existing_expense_id || null
      }))
    };

    const res = await fetch('/api/cards/confirm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const result = await res.json();
    if (!res.ok) throw new Error(result.detail || '가계부 반영에 실패했습니다.');

    alert(`🎉 카드 청구내역이 가계부에 성공적으로 반영되었습니다!\n\n• 신규 추가: ${result.added}건\n• 기존내역 병합/수정: ${result.merged}건\n• 건너뜀: ${result.skipped}건`);

    closeCardUploadModal();

    // Set month and switch view
    const targetY = Number(document.getElementById('cardTargetYear').value);
    const targetM = Number(document.getElementById('cardTargetMonth').value);
    STATE.currentYear = targetY;
    STATE.currentMonth = targetM;
    updateHeaderMonthLabel();
    renderMonthTabs();

    if (STATE.currentTab === 'spending') {
      await loadSpendingPatterns();
    } else {
      switchTab(STATE.currentMonth);
    }
  } catch (err) {
    alert('가계부 반영 실패: ' + err.message);
  } finally {
    confirmBtn.disabled = false;
    confirmBtn.innerHTML = '<span>✨ 가계부에 최종 반영하기</span>';
  }
}
function openSettingsModal() {
  const modal = document.getElementById('modalSettings');
  const img = document.getElementById('modalQRImage');
  const urlSpan = document.getElementById('modalQRUrl');

  if (STATE.networkInfo) {
    if (img) img.src = STATE.networkInfo.qr_code;
    if (urlSpan) urlSpan.textContent = STATE.networkInfo.mobile_url;
  }
  if (modal) modal.classList.remove('hidden');
}

function closeSettingsModal() {
  const modal = document.getElementById('modalSettings');
  if (modal) modal.classList.add('hidden');
}

// Backwards compatibility aliases
function openQRModal() {
  openSettingsModal();
}

function closeQRModal() {
  closeSettingsModal();
}

async function loadGdriveStatus() {
  try {
    const res = await fetch('/api/gdrive/status');
    const data = await res.json();
    const badge = document.getElementById('gdriveStatusBadge');
    const email = document.getElementById('gdriveEmailText');
    const lastBackup = document.getElementById('gdriveLastBackupText');
    const schedSelect = document.getElementById('gdriveScheduleSelect');
    const warningBox = document.getElementById('gdriveWarningBox');
    const warningText = document.getElementById('gdriveWarningText');
    const disconnectBtn = document.getElementById('btnGdriveDisconnect');
    const folderIdInput = document.getElementById('gdriveFolderIdInput');
    const oauthStatusText = document.getElementById('gdriveOAuthClientStatus');
    const redirectCode = document.getElementById('oauthRedirectUriCode');

    // Update displayed redirect URI to current origin
    if (redirectCode) {
      redirectCode.textContent = window.location.origin + '/api/gdrive/oauth/callback';
    }

    if (oauthStatusText) {
      if (data.has_client_secret) {
        oauthStatusText.textContent = '✅ OAuth 키 등록됨';
        oauthStatusText.className = 'text-[11px] font-bold text-emerald-700';
      } else {
        oauthStatusText.textContent = '⚠️ OAuth 키 미등록 (아래 설정 필요)';
        oauthStatusText.className = 'text-[11px] font-bold text-amber-700';
      }
    }

    if (folderIdInput && data.folder_id) {
      folderIdInput.value = data.folder_id;
    }

    if (data.connected) {
      if (disconnectBtn) disconnectBtn.classList.remove('hidden');
      if (badge) {
        if (data.warning) {
          badge.textContent = '주의 (용량 제한)';
          badge.className = 'text-[11px] font-bold px-2 py-0.5 rounded-full bg-rose-100 text-rose-800';
        } else {
          badge.textContent = data.auth_type === 'oauth' ? '연동 완료 (OAuth)' : '연동 완료 (서비스 계정)';
          badge.className = 'text-[11px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800';
        }
      }
      if (email) {
        const typeLabel = data.auth_type === 'oauth' ? '개인 계정' : '서비스 계정';
        email.textContent = `${data.account_email || 'Google Drive 계정'} [${typeLabel}] (${data.folder_name})`;
      }
    } else {
      if (disconnectBtn) disconnectBtn.classList.add('hidden');
      if (badge) {
        badge.textContent = data.has_credentials ? '연결 확인 필요' : '미연동';
        badge.className = 'text-[11px] font-bold px-2 py-0.5 rounded-full bg-slate-200 text-slate-700';
      }
      if (email) {
        email.textContent = data.has_credentials ? '인증 키 등록됨 (연결 테스트 필요)' : '미연동 (Google 로그인 필요)';
      }
    }

    // Display warning banner if present
    if (warningBox && warningText) {
      if (data.warning) {
        warningText.textContent = data.warning;
        warningBox.classList.remove('hidden');
      } else {
        warningBox.classList.add('hidden');
      }
    }

    if (lastBackup) {
      lastBackup.textContent = data.last_backup_time ? `${data.last_backup_time} (${data.last_backup_status || '성공'})` : '없음';
    }

    if (schedSelect && data.schedule) {
      schedSelect.value = data.schedule;
    }
  } catch (err) {
    console.error('Failed to load gdrive status', err);
  }
}

async function triggerGdriveBackup() {
  const btn = document.getElementById('btnTriggerGdriveBackup');
  if (btn) {
    btn.disabled = true;
    btn.textContent = '☁️ 백업 업로드 중...';
  }

  try {
    const res = await fetch('/api/gdrive/backup', { method: 'POST' });
    const result = await res.json();
    if (!res.ok) throw new Error(result.detail || '백업 실패');

    alert(result.message || 'Google Drive에 백업이 완료되었습니다!');
    loadGdriveStatus();
    loadGdriveBackupsList();
  } catch (err) {
    alert('구글 드라이브 백업 실패:\n\n' + err.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = '☁️ 지금 구글 드라이브 백업';
    }
  }
}

async function testGdriveConnection() {
  try {
    const res = await fetch('/api/gdrive/test', { method: 'POST' });
    const data = await res.json();
    alert(data.message || (data.connected ? '연결 성공!' : '연결 실패'));
    loadGdriveStatus();
  } catch (err) {
    alert('연결 테스트 실패: ' + err.message);
  }
}

async function startGdriveOAuthLogin() {
  try {
    const redirectUri = window.location.origin + '/api/gdrive/oauth/callback';
    const res = await fetch(`/api/gdrive/oauth/url?redirect_uri=${encodeURIComponent(redirectUri)}`);
    const data = await res.json();

    if (!res.ok) {
      if (res.status === 400 && data.detail && data.detail.includes('클라이언트 정보')) {
        alert('OAuth 클라이언트 키 설정이 필요합니다.\n\n먼저 [클라이언트 키 설정]을 열어 Google Cloud Console에서 발급받은 client_secret.json 파일을 등록하거나 Client ID와 Secret을 입력해주세요.');
        const el = document.getElementById('gdriveOAuthSettingsBox');
        if (el) el.classList.remove('hidden');
        return;
      }
      throw new Error(data.detail || 'OAuth URL 요청 실패');
    }

    const width = 520, height = 650;
    const left = Math.max(0, (window.innerWidth - width) / 2 + window.screenX);
    const top = Math.max(0, (window.innerHeight - height) / 2 + window.screenY);
    const popup = window.open(data.url, 'google_oauth_popup', `width=${width},height=${height},top=${top},left=${left}`);

    if (!popup || popup.closed || typeof popup.closed === 'undefined') {
      // If popup blocked, redirect directly
      window.location.href = data.url;
    }
  } catch (err) {
    alert('구글 로그인 시작 실패:\n' + err.message);
  }
}

async function saveGdriveOAuthManual() {
  const cidInput = document.getElementById('gdriveClientIdInput');
  const csecInput = document.getElementById('gdriveClientSecretInput');
  const clientId = cidInput ? cidInput.value.trim() : '';
  const clientSecret = csecInput ? csecInput.value.trim() : '';

  if (!clientId || !clientSecret) {
    alert('Google Client ID와 Client Secret을 모두 입력해주세요.');
    return;
  }

  try {
    const res = await fetch('/api/gdrive/oauth/client-secrets', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ client_id: clientId, client_secret: clientSecret })
    });
    const result = await res.json();
    if (!res.ok) throw new Error(result.detail || '저장 실패');
    alert('OAuth 2.0 클라이언트 정보가 저장되었습니다.\n\n이제 [Google 계정으로 로그인하여 연동] 버튼을 눌러 연동을 진행하세요!');
    loadGdriveStatus();
  } catch (err) {
    alert('설정 저장 실패: ' + err.message);
  }
}

function copyRedirectUri() {
  const uri = window.location.origin + '/api/gdrive/oauth/callback';
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(uri).then(() => {
      alert('승인된 리디렉션 URI가 복사되었습니다:\n' + uri);
    }).catch(() => {
      prompt('아래 URI를 복사하여 Google Cloud Console에 등록하세요:', uri);
    });
  } else {
    prompt('아래 URI를 복사하여 Google Cloud Console에 등록하세요:', uri);
  }
}

function toggleGdriveOAuthSettings() {
  const el = document.getElementById('gdriveOAuthSettingsBox');
  if (el) el.classList.toggle('hidden');
}

function toggleGdriveOAuthHelp() {
  const el = document.getElementById('gdriveOAuthSettingsBox');
  if (el) el.classList.remove('hidden');
}

function toggleGdriveSaSection() {
  const el = document.getElementById('gdriveSaSectionBox');
  const arrow = document.getElementById('gdriveSaArrow');
  if (el) {
    el.classList.toggle('hidden');
    if (arrow) arrow.textContent = el.classList.contains('hidden') ? '▼' : '▲';
  }
}

async function disconnectGdrive() {
  if (!confirm('현재 구글 드라이브 연동을 해제하시겠습니까?\n\n※ 로컬 가계부 데이터 및 이미 드라이브에 저장된 백업 파일은 삭제되지 않습니다.')) {
    return;
  }
  try {
    const res = await fetch('/api/gdrive/disconnect', { method: 'POST' });
    const result = await res.json();
    if (!res.ok) throw new Error(result.detail || '연동 해제 실패');
    alert(result.message || 'Google Drive 연동이 해제되었습니다.');
    loadGdriveStatus();
    loadGdriveBackupsList();
  } catch (err) {
    alert('연동 해제 실패: ' + err.message);
  }
}

async function saveGdriveFolderId() {
  const input = document.getElementById('gdriveFolderIdInput');
  const val = input ? input.value.trim() : '';
  try {
    const res = await fetch('/api/gdrive/folder-id', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ folder_id: val })
    });
    const result = await res.json();
    if (!res.ok) throw new Error(result.detail || '폴더 ID 저장 실패');
    alert(result.message || '폴더 ID가 저장되었습니다.');
    loadGdriveStatus();
  } catch (err) {
    alert('폴더 ID 저장 실패: ' + err.message);
  }
}

async function saveGdriveSchedule() {
  const select = document.getElementById('gdriveScheduleSelect');
  const val = select.value;
  try {
    const res = await fetch('/api/gdrive/schedule', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ schedule: val })
    });
    const result = await res.json();
    if (!res.ok) throw new Error(result.detail || '설정 저장 실패');
    alert(result.message || '자동 백업 주기가 저장되었습니다.');
  } catch (err) {
    alert('스케줄 저장 실패: ' + err.message);
  }
}

async function handleGdriveCredsUpload(e) {
  const file = e.target.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch('/api/gdrive/credentials', {
      method: 'POST',
      body: formData
    });
    const result = await res.json();
    if (!res.ok) throw new Error(result.detail || '키 등록 실패');

    alert(result.message || '인증 파일이 등록되었습니다!');
    loadGdriveStatus();
    loadGdriveBackupsList();
  } catch (err) {
    alert('인증 키 등록 실패:\n' + err.message);
  } finally {
    e.target.value = '';
  }
}

function toggleGdriveHelp() {
  toggleGdriveOAuthHelp();
}

async function loadGdriveBackupsList() {
  const container = document.getElementById('gdriveBackupsContainer');
  if (!container) return;

  try {
    const res = await fetch('/api/gdrive/backups');
    const data = await res.json();
    const backups = data.backups || [];

    if (backups.length === 0) {
      container.innerHTML = '<div class="text-center py-3 text-slate-400 text-xs">구글 드라이브에 저장된 백업 파일이 없습니다.</div>';
      return;
    }

    container.innerHTML = backups.map(b => {
      const sizeKb = Math.round((b.size || 0) / 1024);
      const dateStr = b.created_time ? b.created_time.slice(0, 19).replace('T', ' ') : '';
      return `
        <div class="flex items-center justify-between p-2 rounded-lg bg-slate-50 hover:bg-indigo-50/50 border border-slate-200">
          <div class="min-w-0 pr-2">
            <span class="font-bold text-slate-800 block truncate text-xs">${escapeHtml(b.name)}</span>
            <span class="text-[10px] text-slate-500">${dateStr} (${sizeKb} KB)</span>
          </div>
          <div class="flex items-center gap-1 flex-shrink-0">
            <button type="button" onclick="restoreFromGdrive('${b.id}', '${escapeHtml(b.name)}')" class="btn-pastel btn-ghost btn-sm text-indigo-700 border-indigo-200 hover:bg-indigo-100 font-bold py-1 px-2 text-[11px]">
              복구
            </button>
            <button type="button" onclick="deleteFromGdrive('${b.id}', '${escapeHtml(b.name)}')" class="btn-pastel btn-ghost btn-sm text-rose-600 border-rose-200 hover:bg-rose-50 font-bold py-1 px-1.5 text-[11px]" title="삭제">
              🗑️
            </button>
          </div>
        </div>
      `;
    }).join('');
  } catch (err) {
    container.innerHTML = '<div class="text-center py-2 text-rose-500 text-xs">목록을 가져올 수 없습니다.</div>';
  }
}

async function restoreFromGdrive(fileId, fileName) {
  if (!confirm(`'${fileName}' 백업 파일로 가계부 데이터를 복원하시겠습니까?\n\n※ 안전을 위해 현재 데이터베이스는 backups/ 폴더에 자동 백업됩니다.`)) {
    return;
  }

  try {
    const res = await fetch(`/api/gdrive/restore/${fileId}`, { method: 'POST' });
    const result = await res.json();
    if (!res.ok) throw new Error(result.detail || '복원 실패');

    alert(result.message || '데이터가 성공적으로 복원되었습니다.');
    closeSettingsModal();
    window.location.reload();
  } catch (err) {
    alert('복원 실패: ' + err.message);
  }
}

async function deleteFromGdrive(fileId, fileName) {
  if (!confirm(`'${fileName}' 백업 파일을 구글 드라이브에서 삭제하시겠습니까?`)) {
    return;
  }

  try {
    const res = await fetch(`/api/gdrive/backups/${fileId}`, { method: 'DELETE' });
    const result = await res.json();
    if (!res.ok) throw new Error(result.detail || '삭제 실패');

    alert(result.message || '백업 파일이 성공적으로 삭제되었습니다.');
    loadGdriveBackupsList();
  } catch (err) {
    alert('삭제 실패: ' + err.message);
  }
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

async function loadSampleSpreadsheetData() {
  if (!confirm('구글 스프레드시트 예시 데이터를 로드하시겠습니까?\n(기존 데이터에 추가/갱신됩니다)')) return;
  try {
    const res = await fetch('/api/spreadsheet/load-sample', { method: 'POST' });
    const result = await res.json();
    if (!res.ok) throw new Error(result.detail || '로드 실패');
    alert(`예시 데이터가 로드되었습니다!\n- 변동 지출: ${result.imported.variable_expenses}건\n- 고정 수입: ${result.imported.fixed_incomes}건\n- 고정 지출: ${result.imported.fixed_expenses}건\n- 저축/투자: ${result.imported.savings}건`);
    closeBackupModal();
    refreshData();
  } catch (err) {
    alert('로드 실패: ' + err.message);
  }
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

// --- Data Reset Handlers ---
function openResetConfirmModal() {
  const modal = document.getElementById('modalResetConfirm');
  const input = document.getElementById('inputResetConfirm');
  const btn = document.getElementById('btnExecuteReset');
  input.value = '';
  btn.disabled = true;
  btn.classList.add('opacity-50', 'cursor-not-allowed');
  modal.classList.remove('hidden');
  setTimeout(() => input.focus(), 100);
}

function closeResetConfirmModal() {
  document.getElementById('modalResetConfirm').classList.add('hidden');
}

function checkResetConfirmInput(e) {
  const val = e.target.value.trim();
  const btn = document.getElementById('btnExecuteReset');
  if (val === '초기화') {
    btn.disabled = false;
    btn.classList.remove('opacity-50', 'cursor-not-allowed');
  } else {
    btn.disabled = true;
    btn.classList.add('opacity-50', 'cursor-not-allowed');
  }
}

async function executeDataReset() {
  const btn = document.getElementById('btnExecuteReset');
  btn.disabled = true;
  btn.textContent = '초기화 진행 중...';

  try {
    const res = await fetch('/api/spreadsheet/reset', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ confirm_text: '초기화' })
    });
    const result = await res.json();
    if (!res.ok) throw new Error(result.detail || '초기화 실패');

    alert(`데이터가 깨끗하게 초기화되었습니다.\n(안전 백업 파일: ${result.backup_file})`);
    closeResetConfirmModal();
    closeBackupModal();
    switchTab('today');
    await refreshData();
  } catch (err) {
    alert('초기화 실패: ' + err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = '초기화 실행';
  }
}

// Global keyboard shortcuts (ESC to return from 2Depth to 1Depth)
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' || e.key === 'Esc') {
    if (STATE.spendingCategoryDepth === 2) {
      resetCategoryChartToDepth1();
    }
  }
});
