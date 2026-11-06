/* ==========================================================================
   FinTrack Pro - Application Logic & State Management
   ========================================================================== */

const state = {
  currency: localStorage.getItem('fintrack_currency') || '$',
  theme: localStorage.getItem('fintrack_theme') || 'dark',
  currentYear: new Date().getFullYear(),
  currentMonth: new Date().getMonth() + 1,
  overview: null,
  transactions: [],
  budgets: [],
  subscriptions: [],
  editingTransactionId: null,
};

// --------------------------------------------------------------------------
// Initialization & Theme Handling
// --------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
  // Apply initial theme
  document.documentElement.setAttribute('data-theme', state.theme);
  updateThemeIcon();

  // Populate Month Selector
  setupMonthSelector();

  // Set Currency selector
  const currSelect = document.getElementById('currencySelector');
  if (currSelect) {
    currSelect.value = state.currency;
    currSelect.addEventListener('change', (e) => {
      state.currency = e.target.value;
      localStorage.setItem('fintrack_currency', state.currency);
      refreshDashboard();
      showToast(`Currency changed to ${state.currency}`);
    });
  }

  // Set default date in Transaction modal to today
  const transDate = document.getElementById('transDate');
  if (transDate) {
    transDate.valueAsDate = new Date();
  }

  // Attach event listeners
  setupEventListeners();

  // Initial load
  refreshDashboard();
});

function toggleTheme() {
  state.theme = state.theme === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', state.theme);
  localStorage.setItem('fintrack_theme', state.theme);
  updateThemeIcon();
  if (window.refreshAllCharts && state.overview) {
    window.refreshAllCharts(state.overview, state.currency);
  }
}

function updateThemeIcon() {
  const icon = document.getElementById('themeIcon');
  if (icon) {
    icon.textContent = state.theme === 'dark' ? '☀️' : '🌙';
  }
}

function setupMonthSelector() {
  const selector = document.getElementById('monthSelector');
  if (!selector) return;

  selector.innerHTML = '';
  const now = new Date();
  // Show past 12 months
  for (let i = 0; i < 12; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    const y = d.getFullYear();
    const m = d.getMonth() + 1;
    const label = d.toLocaleString('default', { month: 'long', year: 'numeric' });
    const opt = document.createElement('option');
    opt.value = `${y}-${m}`;
    opt.textContent = label;
    if (y === state.currentYear && m === state.currentMonth) {
      opt.selected = true;
    }
    selector.appendChild(opt);
  }

  selector.addEventListener('change', (e) => {
    const [y, m] = e.target.value.split('-');
    state.currentYear = parseInt(y);
    state.currentMonth = parseInt(m);
    refreshDashboard();
  });
}

// --------------------------------------------------------------------------
// API Helpers
// --------------------------------------------------------------------------
async function api(endpoint, options = {}) {
  try {
    const res = await fetch(endpoint, {
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {})
      },
      ...options
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Server Error' }));
      throw new Error(err.detail || 'Request failed');
    }
    return await res.json();
  } catch (error) {
    showToast(error.message, 'error');
    throw error;
  }
}

// --------------------------------------------------------------------------
// Data Refresh & Render
// --------------------------------------------------------------------------
async function refreshDashboard() {
  await Promise.all([
    loadOverview(),
    loadBudgets(),
    loadSubscriptions(),
    loadTransactions()
  ]);
}

async function loadOverview() {
  try {
    const data = await api(`/api/analytics/overview?year=${state.currentYear}&month=${state.currentMonth}`);
    state.overview = data;
    renderMetrics(data);
    renderAlerts(data.budget_alerts);
    if (window.refreshAllCharts) {
      window.refreshAllCharts(data, state.currency);
    }
  } catch (e) {
    console.error('Failed to load overview:', e);
  }
}

function renderMetrics(data) {
  const fmt = (val) => `${state.currency}${Number(val).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  
  const totalBalance = document.getElementById('metricTotalBalance');
  if (totalBalance) totalBalance.textContent = fmt(data.total_balance);

  const monthIncome = document.getElementById('metricMonthIncome');
  if (monthIncome) monthIncome.textContent = fmt(data.total_income_month);

  const monthExpense = document.getElementById('metricMonthExpense');
  if (monthExpense) monthExpense.textContent = fmt(data.total_expense_month);

  const netSavings = document.getElementById('metricNetSavings');
  if (netSavings) netSavings.textContent = fmt(data.net_savings_month);

  const savingsRate = document.getElementById('metricSavingsRate');
  if (savingsRate) {
    savingsRate.textContent = `${data.savings_rate_month.toFixed(1)}%`;
    savingsRate.className = data.savings_rate_month >= 20 ? 'trend-positive' : 'trend-negative';
  }

  const burnRate = document.getElementById('metricBurnRate');
  if (burnRate) burnRate.textContent = `${fmt(data.daily_average_expense_month)} / day`;

  const activeSubs = document.getElementById('metricActiveSubs');
  if (activeSubs) activeSubs.textContent = `${fmt(data.active_subscriptions_cost_monthly)} / mo`;
}

function renderAlerts(alerts) {
  const container = document.getElementById('alertContainer');
  if (!container) return;

  if (!alerts || alerts.length === 0) {
    container.innerHTML = '';
    return;
  }

  container.innerHTML = alerts.map(msg => `
    <div class="alert alert-warning">
      <span>${msg}</span>
    </div>
  `).join('');
}

// --------------------------------------------------------------------------
// Budgets Management
// --------------------------------------------------------------------------
async function loadBudgets() {
  try {
    const data = await api(`/api/budgets/status?year=${state.currentYear}&month=${state.currentMonth}`);
    state.budgets = data;
    renderBudgetsList(data);
  } catch (e) {
    console.error('Failed to load budgets:', e);
  }
}

function renderBudgetsList(budgets) {
  const container = document.getElementById('budgetList');
  if (!container) return;

  if (!budgets || budgets.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <p>No budgets configured for this month.</p>
        <button class="btn btn-sm btn-outline" style="margin-top: 10px;" onclick="openBudgetModal()">+ Set Category Budget</button>
      </div>
    `;
    return;
  }

  const fmt = (v) => `${state.currency}${Number(v).toFixed(2)}`;

  container.innerHTML = budgets.map(b => {
    let progressClass = 'progress-normal';
    if (b.status === 'warning') progressClass = 'progress-warning';
    if (b.status === 'exceeded') progressClass = 'progress-exceeded';

    const barWidth = Math.min(b.percentage_used, 100);

    return `
      <div class="budget-item">
        <div class="budget-item-header">
          <div style="display:flex; align-items:center; gap:8px;">
            <span style="display:inline-block; width:10px; height:10px; border-radius:50%; background-color:${b.color};"></span>
            <span>${b.category}</span>
          </div>
          <div style="display:flex; align-items:center; gap:10px;">
            <span>${fmt(b.current_spent)} / ${fmt(b.monthly_limit)}</span>
            <button class="btn-icon btn-sm" onclick="deleteBudget(${b.id})" title="Delete Budget" style="width:24px; height:24px; font-size:12px;">🗑️</button>
          </div>
        </div>
        <div class="budget-progress-track">
          <div class="budget-progress-bar ${progressClass}" style="width: ${barWidth}%;"></div>
        </div>
        <div class="budget-item-footer">
          <span>${b.percentage_used.toFixed(1)}% used</span>
          <span>${b.remaining >= 0 ? `${fmt(b.remaining)} remaining` : `Exceeded by ${fmt(Math.abs(b.remaining))}`}</span>
        </div>
      </div>
    `;
  }).join('');
}

async function deleteBudget(id) {
  if (!confirm('Are you sure you want to remove this budget limit?')) return;
  try {
    await api(`/api/budgets/${id}`, { method: 'DELETE' });
    showToast('Budget deleted');
    refreshDashboard();
  } catch (e) {
    console.error(e);
  }
}

// --------------------------------------------------------------------------
// Subscriptions Management
// --------------------------------------------------------------------------
async function loadSubscriptions() {
  try {
    const data = await api('/api/subscriptions');
    state.subscriptions = data;
    renderSubscriptionsList(data);
  } catch (e) {
    console.error('Failed to load subscriptions:', e);
  }
}

function renderSubscriptionsList(subscriptions) {
  const container = document.getElementById('subscriptionList');
  if (!container) return;

  if (!subscriptions || subscriptions.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <p>No recurring subscriptions added yet.</p>
        <button class="btn btn-sm btn-outline" style="margin-top: 10px;" onclick="openSubscriptionModal()">+ Add Subscription</button>
      </div>
    `;
    return;
  }

  const fmt = (v) => `${state.currency}${Number(v).toFixed(2)}`;

  container.innerHTML = subscriptions.map(s => `
    <div class="subscription-item">
      <div class="sub-meta">
        <div class="sub-name">${s.name}</div>
        <div class="sub-details">
          <span>${s.category}</span> • 
          <span>Renews: ${s.next_billing_date}</span> • 
          <span>Cycle: ${s.billing_cycle}</span>
        </div>
      </div>
      <div class="sub-actions">
        <div class="sub-price">
          ${fmt(s.amount)}
          <div style="font-size:0.7rem; font-weight:normal; color:var(--text-muted);">${fmt(s.monthly_equivalent)}/mo</div>
        </div>
        <button class="btn btn-sm btn-primary" onclick="logSubscriptionPayment(${s.id})" title="Log payment for today">Pay</button>
        <button class="btn-icon btn-sm" onclick="deleteSubscription(${s.id})" title="Delete Subscription" style="width:28px; height:28px; font-size:12px;">🗑️</button>
      </div>
    </div>
  `).join('');
}

async function logSubscriptionPayment(id) {
  try {
    await api(`/api/subscriptions/${id}/pay`, { method: 'POST' });
    showToast('Payment logged as an expense transaction for today!');
    refreshDashboard();
  } catch (e) {
    console.error(e);
  }
}

async function deleteSubscription(id) {
  if (!confirm('Are you sure you want to remove this subscription?')) return;
  try {
    await api(`/api/subscriptions/${id}`, { method: 'DELETE' });
    showToast('Subscription removed');
    refreshDashboard();
  } catch (e) {
    console.error(e);
  }
}

// --------------------------------------------------------------------------
// Transactions Management
// --------------------------------------------------------------------------
async function loadTransactions() {
  try {
    const search = document.getElementById('transSearch')?.value || '';
    const type = document.getElementById('transTypeFilter')?.value || '';
    const category = document.getElementById('transCategoryFilter')?.value || '';

    let url = `/api/transactions?limit=100`;
    if (search) url += `&search=${encodeURIComponent(search)}`;
    if (type) url += `&trans_type=${encodeURIComponent(type)}`;
    if (category) url += `&category=${encodeURIComponent(category)}`;

    const data = await api(url);
    state.transactions = data;
    renderTransactionsTable(data);
  } catch (e) {
    console.error('Failed to load transactions:', e);
  }
}

function renderTransactionsTable(transactions) {
  const tbody = document.getElementById('transactionsTableBody');
  if (!tbody) return;

  if (!transactions || transactions.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" class="empty-state">No transactions matching your criteria.</td>
      </tr>
    `;
    return;
  }

  const fmt = (v) => `${state.currency}${Number(v).toFixed(2)}`;

  tbody.innerHTML = transactions.map(t => {
    const isIncome = t.type === 'income';
    const amountClass = isIncome ? 'amount-income' : 'amount-expense';
    const sign = isIncome ? '+' : '-';

    return `
      <tr>
        <td>${t.date}</td>
        <td>
          <div style="font-weight:600;">${t.title}</div>
          ${t.notes ? `<div style="font-size:0.75rem; color:var(--text-muted);">${t.notes}</div>` : ''}
        </td>
        <td><span class="badge badge-category">${t.category}</span></td>
        <td><span class="badge ${isIncome ? 'badge-income' : 'badge-expense'}">${t.type.toUpperCase()}</span></td>
        <td><span style="font-size:0.8rem; color:var(--text-secondary);">${t.payment_method}</span></td>
        <td class="${amountClass}">${sign} ${fmt(t.amount)}</td>
        <td style="text-align:right;">
          <button class="btn-icon btn-sm" onclick="openEditTransactionModal(${t.id})" title="Edit" style="width:28px; height:28px; font-size:12px;">✏️</button>
          <button class="btn-icon btn-sm" onclick="deleteTransaction(${t.id})" title="Delete" style="width:28px; height:28px; font-size:12px;">🗑️</button>
        </td>
      </tr>
    `;
  }).join('');
}

async function deleteTransaction(id) {
  if (!confirm('Are you sure you want to delete this transaction?')) return;
  try {
    await api(`/api/transactions/${id}`, { method: 'DELETE' });
    showToast('Transaction deleted');
    refreshDashboard();
  } catch (e) {
    console.error(e);
  }
}

// --------------------------------------------------------------------------
// Modal Controls & Form Submissions
// --------------------------------------------------------------------------
function openTransactionModal() {
  state.editingTransactionId = null;
  document.getElementById('transModalTitle').textContent = 'Add Transaction';
  document.getElementById('transForm').reset();
  document.getElementById('transDate').valueAsDate = new Date();
  document.getElementById('transactionModal').classList.add('active');
}

function openEditTransactionModal(id) {
  const t = state.transactions.find(item => item.id === id);
  if (!t) return;

  state.editingTransactionId = id;
  document.getElementById('transModalTitle').textContent = 'Edit Transaction';
  document.getElementById('transTitle').value = t.title;
  document.getElementById('transAmount').value = t.amount;
  document.getElementById('transType').value = t.type;
  document.getElementById('transCategory').value = t.category;
  document.getElementById('transDate').value = t.date;
  document.getElementById('transMethod').value = t.payment_method;
  document.getElementById('transNotes').value = t.notes || '';
  document.getElementById('transTags').value = t.tags || '';

  document.getElementById('transactionModal').classList.add('active');
}

function closeTransactionModal() {
  document.getElementById('transactionModal').classList.remove('active');
}

function openBudgetModal() {
  document.getElementById('budgetForm').reset();
  document.getElementById('budgetModal').classList.add('active');
}

function closeBudgetModal() {
  document.getElementById('budgetModal').classList.remove('active');
}

function openSubscriptionModal() {
  document.getElementById('subForm').reset();
  document.getElementById('subNextDate').valueAsDate = new Date();
  document.getElementById('subscriptionModal').classList.add('active');
}

function closeSubscriptionModal() {
  document.getElementById('subscriptionModal').classList.remove('active');
}

function setupEventListeners() {
  // Transaction Form Submit
  const transForm = document.getElementById('transForm');
  if (transForm) {
    transForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const payload = {
        title: document.getElementById('transTitle').value,
        amount: parseFloat(document.getElementById('transAmount').value),
        type: document.getElementById('transType').value,
        category: document.getElementById('transCategory').value,
        date: document.getElementById('transDate').value,
        payment_method: document.getElementById('transMethod').value,
        notes: document.getElementById('transNotes').value || null,
        tags: document.getElementById('transTags').value || null,
      };

      try {
        if (state.editingTransactionId) {
          await api(`/api/transactions/${state.editingTransactionId}`, {
            method: 'PUT',
            body: JSON.stringify(payload)
          });
          showToast('Transaction updated successfully!');
        } else {
          await api('/api/transactions', {
            method: 'POST',
            body: JSON.stringify(payload)
          });
          showToast('Transaction added successfully!');
        }
        closeTransactionModal();
        refreshDashboard();
      } catch (err) {
        console.error(err);
      }
    });
  }

  // Budget Form Submit
  const budgetForm = document.getElementById('budgetForm');
  if (budgetForm) {
    budgetForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const payload = {
        category: document.getElementById('budgetCategory').value,
        monthly_limit: parseFloat(document.getElementById('budgetLimit').value),
        color: document.getElementById('budgetColor').value || '#6366f1',
      };

      try {
        await api('/api/budgets', {
          method: 'POST',
          body: JSON.stringify(payload)
        });
        showToast('Budget saved successfully!');
        closeBudgetModal();
        refreshDashboard();
      } catch (err) {
        console.error(err);
      }
    });
  }

  // Subscription Form Submit
  const subForm = document.getElementById('subForm');
  if (subForm) {
    subForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const payload = {
        name: document.getElementById('subName').value,
        amount: parseFloat(document.getElementById('subAmount').value),
        billing_cycle: document.getElementById('subCycle').value,
        category: document.getElementById('subCategory').value,
        next_billing_date: document.getElementById('subNextDate').value,
        payment_method: document.getElementById('subMethod').value,
        notes: document.getElementById('subNotes').value || null,
      };

      try {
        await api('/api/subscriptions', {
          method: 'POST',
          body: JSON.stringify(payload)
        });
        showToast('Subscription added successfully!');
        closeSubscriptionModal();
        refreshDashboard();
      } catch (err) {
        console.error(err);
      }
    });
  }

  // Filter input listeners
  const searchInput = document.getElementById('transSearch');
  if (searchInput) {
    let debounceTimer;
    searchInput.addEventListener('input', () => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(loadTransactions, 300);
    });
  }

  document.getElementById('transTypeFilter')?.addEventListener('change', loadTransactions);
  document.getElementById('transCategoryFilter')?.addEventListener('change', loadTransactions);
}

// --------------------------------------------------------------------------
// Seed Demo Data
// --------------------------------------------------------------------------
async function seedDemoData() {
  if (!confirm('This will load 3 months of realistic transactions, budgets, and subscriptions for testing. Continue?')) {
    return;
  }
  try {
    const res = await api('/api/analytics/seed-demo', { method: 'POST' });
    showToast(res.message);
    refreshDashboard();
  } catch (e) {
    console.error(e);
  }
}

// --------------------------------------------------------------------------
// Toast Feedback
// --------------------------------------------------------------------------
function showToast(message, type = 'success') {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = 'toast';
  const icon = type === 'error' ? '❌' : '✅';
  toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}
