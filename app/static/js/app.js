/**
 * 🌸 HouseholdAccountBook - Mobile-First Client Application
 */

const STATE = {
  currentYear: 2026,
  currentMonth: new Date().getMonth() + 1,
  currentTab: 'today', // 'today' | 'annual' | 1..12
  categories: [],
  paymentMethods: [],
  networkInfo: null,
  trendChart: null,
  donutChart: null,
  isEditingFixed: { income: false, expense: false, savings: false },
  isEditingVarExpense: false,
  cachedPlans: { incomes: [], expenses: [], savings: [] },
  cachedVarExpenses: []
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
  renderMonthTabs();
  switchTab(m);
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
  renderMonthTabs();
  switchTab(m);
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
    btn.className = `category-chip text-xs px-3 py-1.5 font-bold ${m === STATE.currentMonth ? 'border-purple-500 bg-white text-purple-900 shadow-sm' : ''}`;
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
    updateHeaderMonthLabel();
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
    updateHeaderMonthLabel();
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
        <td class="py-1.5 text-right"><input type="number" value="${item.amount}" class="glass-input text-xs py-1.5 px-2 rounded-lg text-right item-amt font-extrabold text-slate-800" style="width: 90px"></td>
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
    <td class="py-1.5 text-right"><input type="number" value="0" class="glass-input text-xs py-1.5 px-2 rounded-lg text-right item-amt font-extrabold text-slate-800" style="width: 90px"></td>
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

    // 1. Render Mobile Timeline Cards (3-column, 2-row layout)
    renderMonthVariableExpensesMobile(items);

    // 2. Render Desktop Spreadsheet Table (with '09/18' date format)
    const tbody = document.getElementById('monthVarExpenseBody');
    if (tbody) {
      if (!items || items.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center py-6 text-slate-400 font-medium">등록된 변동 지출 내역이 없습니다.</td></tr>';
      } else {
        tbody.innerHTML = items.map(item => `
          <tr>
            <td class="text-center font-mono font-bold text-slate-700">${formatShortSlashDate(item.transaction_date)}</td>
            <td class="text-center">
              <span class="badge-category" style="background-color: ${item.category_color || '#A8E6CF'}25; color: #0F172A;">${escapeHtml(item.category_name || '기타')}</span>
            </td>
            <td class="font-bold text-slate-900">${escapeHtml(item.title)}</td>
            <td class="text-center"><span class="badge-pay">${escapeHtml(item.payment_method_name || '현금')}</span></td>
            <td class="text-right font-black text-rose-600">${formatKRW(item.amount)}원</td>
            <td class="text-slate-500 text-xs">${escapeHtml(item.memo || '')}</td>
            <td class="text-center d-edit-actions">
              <button onclick="openEditTransactionModal(${item.id})" class="btn-tx-edit">수정</button>
            </td>
            <td class="text-center d-edit-actions">
              <button onclick="deleteTransaction(${item.id})" class="btn-tx-del">삭제</button>
            </td>
          </tr>
        `).join('');
      }
    }
  } catch (err) {
    console.error('Failed to load month variable expenses', err);
  }
}

// Render Mobile-First Variable Expenses in 3-Column, 2-Row layout:
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

  const html = items.map(item => `
    <div class="mobile-tx-card-grid" data-id="${item.id}">
      <!-- Col 1: 일자 (Spans 2 rows, Vertically centered) -->
      <div class="mobile-tx-col-date">
        <span>${formatShortSlashDate(item.transaction_date)}</span>
      </div>

      <!-- Col 2, Row 1: 분류 + 지출내용 -->
      <div class="mobile-tx-col-top">
        <span class="badge-category flex-shrink-0" style="background-color: ${item.category_color || '#A8E6CF'}30; color: #0F172A;">
          ${escapeHtml(item.category_name || '기타')}
        </span>
        <span class="font-bold text-slate-900 truncate text-sm">
          ${escapeHtml(item.title)}
        </span>
      </div>

      <!-- Col 3, Row 1: 수정 버튼 -->
      <div class="mobile-tx-col-edit d-edit-actions">
        <button type="button" onclick="openEditTransactionModal(${item.id})" class="btn-tx-edit">
          수정
        </button>
      </div>

      <!-- Col 2, Row 2: 결제수단 + 금액 -->
      <div class="mobile-tx-col-bottom">
        <span class="badge-pay text-[11px] py-0.5 px-1.5 flex-shrink-0">
          ${escapeHtml(item.payment_method_name || '현금')}
        </span>
        <span class="font-black text-rose-600 text-sm whitespace-nowrap">
          -${formatKRW(item.amount)}원
        </span>
        ${item.memo ? `<span class="text-[11px] text-slate-400 truncate max-w-[80px]">(${escapeHtml(item.memo)})</span>` : ''}
      </div>

      <!-- Col 3, Row 2: 삭제 버튼 -->
      <div class="mobile-tx-col-del d-edit-actions">
        <button type="button" onclick="deleteTransaction(${item.id})" class="btn-tx-del">
          삭제
        </button>
      </div>
    </div>
  `).join('');

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

// --- Settings & Google Drive Cloud Backup Handlers ---
function openSettingsModal() {
  const modal = document.getElementById('modalSettings');
  const img = document.getElementById('modalQRImage');
  const urlSpan = document.getElementById('modalQRUrl');

  if (STATE.networkInfo) {
    if (img) img.src = STATE.networkInfo.qr_code;
    if (urlSpan) urlSpan.textContent = STATE.networkInfo.mobile_url;
  }
  if (modal) modal.classList.remove('hidden');

  // Load Google Drive Status & Backups
  loadGdriveStatus();
  loadGdriveBackupsList();
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

    if (data.connected) {
      if (badge) {
        badge.textContent = '연동 완료';
        badge.className = 'text-[11px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800';
      }
      if (email) email.textContent = `${data.account_email || 'Google Drive 계정'} (${data.folder_name})`;
    } else {
      if (badge) {
        badge.textContent = data.has_credentials ? '연결 확인 필요' : '미연동';
        badge.className = 'text-[11px] font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800';
      }
      if (email) email.textContent = data.has_credentials ? '인증 키 등록됨 (연결 테스트 필요)' : '미연동 (서비스 계정 키 등록 필요)';
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
    alert('구글 드라이브 백업 실패: ' + err.message);
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

    alert('서비스 계정 키가 등록되었습니다!\n' + (result.test_result?.message || '연동 성공'));
    loadGdriveStatus();
    loadGdriveBackupsList();
  } catch (err) {
    alert('인증 키 등록 실패: ' + err.message);
  } finally {
    e.target.value = '';
  }
}

function toggleGdriveHelp() {
  const el = document.getElementById('gdriveHelpBox');
  if (el) el.classList.toggle('hidden');
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
          <button type="button" onclick="restoreFromGdrive('${b.id}', '${escapeHtml(b.name)}')" class="btn-pastel btn-ghost btn-sm text-indigo-700 border-indigo-200 hover:bg-indigo-100 font-bold py-1 px-2.5 text-[11px]">
            복구
          </button>
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
