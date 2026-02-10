<template>
  <div class="accounts-page">
    <!-- Type Tabs + Actions -->
    <div class="type-bar">
      <div class="type-tabs">
        <button
          v-for="t in types"
          :key="t"
          class="type-tab"
          :class="{ active: currentType === t }"
          @click="switchType(t)"
        >
          {{ t }}
          <span class="type-count">{{ typeCounts[t] ?? 0 }}</span>
        </button>
      </div>
      <div class="type-actions">
        <button class="btn btn-ghost btn-sm" @click="showAddType = true" v-if="!showAddType">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"
            stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          添加类型
        </button>
        <form v-else class="add-type-form" @submit.prevent="addType">
          <input
            ref="typeInputRef"
            class="input input-sm"
            v-model="newTypeName"
            placeholder="类型名称..."
            @keydown.esc="showAddType = false"
          />
          <button class="btn btn-primary btn-sm" type="submit" :disabled="!newTypeName.trim()">确定</button>
          <button class="btn btn-ghost btn-sm" type="button" @click="showAddType = false">取消</button>
        </form>
        <button
          v-if="currentType && !showAddType"
          class="btn btn-ghost btn-sm btn-danger-text"
          @click="showDeleteTypeConfirm = true"
        >
          删除类型
        </button>
      </div>
    </div>

    <!-- Content -->
    <template v-if="currentType">
      <!-- Toolbar -->
      <div class="toolbar">
        <button class="btn btn-primary btn-sm" @click="showBatchDialog = true">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"
            stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          批量添加
        </button>
        <button
          v-if="accounts.length > 0"
          class="btn btn-sm btn-danger-text"
          @click="showClearConfirm = true"
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
            stroke-linecap="round" stroke-linejoin="round">
            <polyline points="3 6 5 6 21 6" />
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
          </svg>
          全部删除
        </button>
        <span class="toolbar-sep"></span>
        <span class="toolbar-count">{{ accounts.length }} 个账号</span>
        <span class="toolbar-spacer"></span>
        <div class="page-size-selector">
          <span class="page-size-label">每页</span>
          <select class="page-size-select" v-model.number="pageSize">
            <option v-for="s in pageSizeOptions" :key="s" :value="s">{{ s }}</option>
          </select>
          <span class="page-size-label">条</span>
        </div>
      </div>

      <!-- Account List (flat, no card) -->
      <div v-if="accounts.length === 0" class="empty-state">
        <p class="empty-text">暂无账号，点击「批量添加」开始</p>
      </div>
      <template v-else>
        <ul class="account-list">
          <li v-for="(account, idx) in pagedAccounts" :key="idx" class="account-item">
            <div class="account-left">
              <span class="account-index">{{ (currentPage - 1) * pageSize + idx + 1 }}</span>
              <div class="account-avatar" :style="{ background: getAvatarColor((currentPage - 1) * pageSize + idx) }">
                {{ account.charAt(0).toUpperCase() }}
              </div>
              <a class="account-name" :href="getAccountUrl(account)" @click.prevent="openAccount(account)" :title="account">{{ displayName(account) }}</a>
            </div>
            <div class="account-actions">
              <button class="action-btn action-open" @click="openAccount(account)" title="在浏览器中打开">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                  stroke-linecap="round" stroke-linejoin="round">
                  <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                  <polyline points="15 3 21 3 21 9" />
                  <line x1="10" y1="14" x2="21" y2="3" />
                </svg>
                打开
              </button>
              <button class="action-btn action-delete" @click="removeAccount(account)" title="删除该账号">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                  stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="3 6 5 6 21 6" />
                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                </svg>
                删除
              </button>
            </div>
          </li>
        </ul>

        <!-- Pagination -->
        <div v-if="totalPages > 1" class="pagination">
          <button class="page-btn" :disabled="currentPage <= 1" @click="currentPage = 1" title="首页">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
              stroke-linecap="round" stroke-linejoin="round">
              <polyline points="11 17 6 12 11 7" />
              <polyline points="18 17 13 12 18 7" />
            </svg>
          </button>
          <button class="page-btn" :disabled="currentPage <= 1" @click="currentPage--" title="上一页">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
              stroke-linecap="round" stroke-linejoin="round">
              <polyline points="15 18 9 12 15 6" />
            </svg>
          </button>

          <template v-for="p in visiblePages" :key="p">
            <span v-if="p === '...'" class="page-ellipsis">...</span>
            <button v-else class="page-btn page-num" :class="{ active: currentPage === p }" @click="currentPage = p">
              {{ p }}
            </button>
          </template>

          <button class="page-btn" :disabled="currentPage >= totalPages" @click="currentPage++" title="下一页">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
              stroke-linecap="round" stroke-linejoin="round">
              <polyline points="9 18 15 12 9 6" />
            </svg>
          </button>
          <button class="page-btn" :disabled="currentPage >= totalPages" @click="currentPage = totalPages" title="末页">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
              stroke-linecap="round" stroke-linejoin="round">
              <polyline points="13 17 18 12 13 7" />
              <polyline points="6 17 11 12 6 7" />
            </svg>
          </button>
          <span class="page-info">{{ currentPage }} / {{ totalPages }}</span>
        </div>
      </template>
    </template>

    <!-- No type -->
    <div v-else class="empty-state">
      <p class="empty-text">请先添加一个类型</p>
    </div>

    <!-- Batch Add Dialog -->
    <Teleport to="body">
      <transition name="backdrop">
        <div v-if="showBatchDialog" class="dialog-backdrop" @click="closeBatchDialog"></div>
      </transition>
      <transition name="dialog">
        <div v-if="showBatchDialog" class="dialog">
          <div class="dialog-header">
            <h3>批量添加账号 — {{ currentType }}</h3>
            <button class="btn-icon" @click="closeBatchDialog">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
          <div class="dialog-body">
            <textarea
              ref="textareaRef"
              class="textarea"
              v-model="newAccountText"
              placeholder="每行一个账号链接，仅支持以下格式：&#10;https://www.toutiao.com/c/user/token/xxxxx&#10;&#10;不符合格式的链接将被自动过滤"
              rows="10"
            ></textarea>
          </div>
          <div class="dialog-footer">
            <span class="batch-hint">{{ batchCount }} 个账号待添加</span>
            <div class="dialog-footer-actions">
              <button class="btn btn-sm" @click="closeBatchDialog">取消</button>
              <button class="btn btn-primary btn-sm" @click="addAccounts" :disabled="!newAccountText.trim() || loading">
                确认添加
              </button>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>

    <!-- Delete Type Confirm Dialog -->
    <Teleport to="body">
      <transition name="backdrop">
        <div v-if="showDeleteTypeConfirm" class="dialog-backdrop" @click="showDeleteTypeConfirm = false"></div>
      </transition>
      <transition name="dialog">
        <div v-if="showDeleteTypeConfirm" class="dialog dialog-sm">
          <div class="dialog-header">
            <h3>确认删除</h3>
            <button class="btn-icon" @click="showDeleteTypeConfirm = false">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
          <div class="dialog-body confirm-body">
            <p>确定要删除类型「<strong>{{ currentType }}</strong>」吗？</p>
            <p class="confirm-hint">该类型下的所有账号数据将被永久删除，此操作不可恢复。</p>
          </div>
          <div class="dialog-footer">
            <span></span>
            <div class="dialog-footer-actions">
              <button class="btn btn-sm" @click="showDeleteTypeConfirm = false">取消</button>
              <button class="btn btn-sm btn-danger" @click="confirmRemoveType">确认删除</button>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>

    <!-- Clear All Confirm Dialog -->
    <Teleport to="body">
      <transition name="backdrop">
        <div v-if="showClearConfirm" class="dialog-backdrop" @click="showClearConfirm = false"></div>
      </transition>
      <transition name="dialog">
        <div v-if="showClearConfirm" class="dialog dialog-sm">
          <div class="dialog-header">
            <h3>确认清空</h3>
            <button class="btn-icon" @click="showClearConfirm = false">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
          <div class="dialog-body confirm-body">
            <p>确定要清空「<strong>{{ currentType }}</strong>」下的全部 <strong>{{ accounts.length }}</strong> 个账号吗？</p>
            <p class="confirm-hint">此操作不可恢复。</p>
          </div>
          <div class="dialog-footer">
            <span></span>
            <div class="dialog-footer-actions">
              <button class="btn btn-sm" @click="showClearConfirm = false">取消</button>
              <button class="btn btn-sm btn-danger" @click="clearAllAccounts">确认清空</button>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { useAppStore } from '../stores/app'
import { useToast } from '../composables/useToast'

const appStore = useAppStore()
const { toast } = useToast()

// Types
const types = ref([])
const currentType = ref('')
const typeCounts = ref({})
const showAddType = ref(false)
const newTypeName = ref('')
const typeInputRef = ref(null)

// Accounts
const accounts = ref([])
const loading = ref(false)

// Pagination
const currentPage = ref(1)
const pageSize = ref(20)
const pageSizeOptions = [10, 20, 50, 100]

const totalPages = computed(() => {
  if (accounts.value.length === 0) return 1
  return Math.ceil(accounts.value.length / pageSize.value)
})

const pagedAccounts = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return accounts.value.slice(start, start + pageSize.value)
})

const visiblePages = computed(() => {
  const total = totalPages.value
  const cur = currentPage.value
  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i + 1)
  }
  const pages = []
  pages.push(1)
  if (cur > 3) pages.push('...')
  const start = Math.max(2, cur - 1)
  const end = Math.min(total - 1, cur + 1)
  for (let i = start; i <= end; i++) pages.push(i)
  if (cur < total - 2) pages.push('...')
  pages.push(total)
  return pages
})

// Reset page when switching type or changing page size
watch(pageSize, () => { currentPage.value = 1 })

// Dialogs
const showBatchDialog = ref(false)
const showDeleteTypeConfirm = ref(false)
const showClearConfirm = ref(false)
const newAccountText = ref('')
const textareaRef = ref(null)

const avatarColors = [
  'linear-gradient(135deg, #6366f1, #8b5cf6)',
  'linear-gradient(135deg, #3b82f6, #06b6d4)',
  'linear-gradient(135deg, #f59e0b, #ef4444)',
  'linear-gradient(135deg, #22c55e, #14b8a6)',
  'linear-gradient(135deg, #ec4899, #8b5cf6)',
  'linear-gradient(135deg, #f97316, #eab308)',
]

function getAvatarColor(index) {
  return avatarColors[index % avatarColors.length]
}

const batchCount = computed(() => {
  if (!newAccountText.value.trim()) return 0
  return newAccountText.value.trim().split('\n').filter(l => l.trim()).length
})

watch(showAddType, (val) => {
  if (val) nextTick(() => typeInputRef.value?.focus())
})

watch(showBatchDialog, (val) => {
  if (val) {
    nextTick(() => textareaRef.value?.focus())
  }
})

onMounted(() => {
  loadTypes()
})

async function loadTypes() {
  const result = await appStore.callApi('get_account_types')
  if (result && result.success) {
    types.value = result.types
    for (const t of result.types) {
      const r = await appStore.callApi('get_accounts', t)
      if (r && r.success) {
        typeCounts.value[t] = r.accounts.length
      }
    }
    if (types.value.length > 0 && !currentType.value) {
      switchType(types.value[0])
    }
  }
}

async function addType() {
  const name = newTypeName.value.trim()
  if (!name) return
  const result = await appStore.callApi('add_account_type', name)
  if (result && result.success) {
    types.value.push(name)
    typeCounts.value[name] = 0
    newTypeName.value = ''
    showAddType.value = false
    switchType(name)
    toast.success(`类型「${name}」创建成功`)
  } else if (result) {
    toast.error(result.message)
  }
}

async function confirmRemoveType() {
  if (!currentType.value) return
  const name = currentType.value
  showDeleteTypeConfirm.value = false
  const result = await appStore.callApi('remove_account_type', name)
  if (result && result.success) {
    types.value = types.value.filter(t => t !== name)
    delete typeCounts.value[name]
    currentType.value = types.value.length > 0 ? types.value[0] : ''
    if (currentType.value) {
      await loadAccounts()
    } else {
      accounts.value = []
    }
    toast.success(`类型「${name}」已删除`)
  }
}

async function switchType(t) {
  currentType.value = t
  currentPage.value = 1
  await loadAccounts()
}

async function loadAccounts() {
  if (!currentType.value) return
  loading.value = true
  const result = await appStore.callApi('get_accounts', currentType.value)
  if (result && result.success) {
    accounts.value = result.accounts
    typeCounts.value[currentType.value] = result.accounts.length
  }
  loading.value = false
}

async function addAccounts() {
  const text = newAccountText.value.trim()
  if (!text || !currentType.value) return

  loading.value = true
  const result = await appStore.callApi('add_accounts', currentType.value, text)
  loading.value = false

  if (result) {
    accounts.value = result.accounts
    typeCounts.value[currentType.value] = result.accounts.length

    // Show result via toast
    if (result.added > 0) {
      toast.success(result.message)
    } else if (result.invalid > 0) {
      toast.warning(result.message)
    } else {
      toast.warning(result.message)
    }

    if (result.added > 0 || result.invalid > 0) {
      newAccountText.value = ''
      showBatchDialog.value = false
    }
  }
}

async function clearAllAccounts() {
  if (!currentType.value) return
  showClearConfirm.value = false
  loading.value = true
  const result = await appStore.callApi('clear_accounts', currentType.value)
  loading.value = false

  if (result && result.success) {
    accounts.value = []
    typeCounts.value[currentType.value] = 0
    toast.success('已清空全部账号')
  } else if (result) {
    toast.error(result.message)
  }
}

function closeBatchDialog() {
  showBatchDialog.value = false
  newAccountText.value = ''
}

function displayName(account) {
  // 从 URL 中提取 token 部分作为展示名
  const prefix = 'https://www.toutiao.com/c/user/token/'
  if (account.startsWith(prefix)) {
    let token = account.slice(prefix.length)
    // 去掉尾部参数
    const qIdx = token.indexOf('?')
    if (qIdx !== -1) token = token.substring(0, qIdx)
    // 去掉尾部斜杠
    token = token.replace(/\/+$/, '')
    return token || account
  }
  return account
}

function getAccountUrl(account) {
  return account
}

async function openAccount(account) {
  await appStore.callApi('open_in_browser', account)
  toast.info('已在浏览器中打开')
}

async function removeAccount(account) {
  loading.value = true
  const result = await appStore.callApi('remove_account', currentType.value, account)
  loading.value = false

  if (result && result.success) {
    accounts.value = result.accounts
    typeCounts.value[currentType.value] = result.accounts.length
    toast.success('已删除')
  } else if (result) {
    toast.error(result.message)
  }
}
</script>

<style scoped>
.accounts-page {
  max-width: 100%;
}

.page-header-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}

/* ---- Type Bar ---- */
.type-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  margin-bottom: var(--space-5);
  flex-wrap: wrap;
}

.type-tabs {
  display: flex;
  gap: var(--space-1);
  flex-wrap: wrap;
}

.type-tab {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  font-size: var(--text-sm);
  font-weight: 450;
  font-family: var(--font-sans);
  color: var(--text-secondary);
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
  white-space: nowrap;
}

.type-tab:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.type-tab.active {
  background: var(--bg-active);
  color: var(--text-primary);
  border-color: var(--surface-border);
}

.type-count {
  font-size: var(--text-xs);
  color: var(--text-muted);
  background: var(--bg-hover);
  padding: 0 6px;
  border-radius: 9999px;
  min-width: 18px;
  text-align: center;
}

.type-tab.active .type-count {
  background: var(--surface-border);
  color: var(--text-secondary);
}

.type-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.add-type-form {
  display: flex;
  gap: var(--space-2);
  align-items: center;
}

.input-sm {
  height: 28px;
  font-size: var(--text-xs);
  padding: var(--space-1) var(--space-3);
  width: 120px;
}

.btn-danger-text {
  color: var(--text-muted);
}
.btn-danger-text:hover {
  color: var(--error) !important;
  background: rgba(239, 68, 68, 0.1) !important;
}

/* ---- Toolbar ---- */
.toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
  flex-wrap: wrap;
}

.toolbar-sep {
  width: 1px;
  height: 16px;
  background: var(--surface-border);
}

.toolbar-count {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.toolbar-spacer {
  flex: 1;
}

/* Page size selector */
.page-size-selector {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.page-size-label {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.page-size-select {
  height: 26px;
  padding: 0 var(--space-2);
  font-size: var(--text-xs);
  font-family: var(--font-sans);
  background: var(--bg-secondary);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  outline: none;
  cursor: pointer;
  transition: border-color var(--transition-fast);
  -webkit-appearance: none;
  appearance: none;
  padding-right: 20px;
  background-image: url("data:image/svg+xml,%3Csvg width='10' height='6' viewBox='0 0 10 6' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%2371717a' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 6px center;
}

.page-size-select:focus {
  border-color: var(--accent-primary);
}

.page-size-select option {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

/* ---- Empty ---- */
.empty-state {
  padding: var(--space-10) 0;
}

.empty-text {
  font-size: var(--text-sm);
  color: var(--text-muted);
}

/* ---- Account List (flat) ---- */
.account-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.account-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-2) var(--space-1);
  border-radius: var(--radius-md);
  transition: background var(--transition-fast);
}

.account-item:hover {
  background: var(--bg-hover);
}

.account-left {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  min-width: 0;
}

.account-avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-xs);
  font-weight: 600;
  flex-shrink: 0;
}

.account-name {
  font-size: var(--text-sm);
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-decoration: none;
  cursor: pointer;
  transition: color var(--transition-fast);
}

.account-name:hover {
  color: var(--accent-primary-hover);
}

.account-index {
  font-size: var(--text-xs);
  color: var(--text-muted);
  min-width: 28px;
  text-align: right;
  flex-shrink: 0;
  font-family: var(--font-mono);
}

/* Action buttons */
.account-actions {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  flex-shrink: 0;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  font-size: var(--text-xs);
  font-weight: 450;
  font-family: var(--font-sans);
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
  background: transparent;
  white-space: nowrap;
}

.action-open {
  color: var(--text-muted);
}

.action-open:hover {
  color: var(--accent-primary);
  background: var(--accent-glow);
}

.action-delete {
  color: var(--text-muted);
}

.action-delete:hover {
  color: var(--error);
  background: rgba(239, 68, 68, 0.1);
}

/* ---- Pagination ---- */
.pagination {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  margin-top: var(--space-5);
  padding-top: var(--space-4);
  border-top: 1px solid var(--surface-border);
}

.page-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 30px;
  height: 30px;
  padding: 0 var(--space-2);
  font-size: var(--text-xs);
  font-weight: 450;
  font-family: var(--font-sans);
  color: var(--text-secondary);
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.page-btn:hover:not(:disabled) {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.page-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.page-btn.active {
  background: var(--bg-active);
  color: var(--text-primary);
  border-color: var(--surface-border);
}

.page-ellipsis {
  font-size: var(--text-xs);
  color: var(--text-muted);
  padding: 0 4px;
  user-select: none;
}

.page-info {
  font-size: var(--text-xs);
  color: var(--text-muted);
  margin-left: var(--space-3);
}

/* Dialog close btn-icon */
.btn-icon {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  color: var(--text-tertiary);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
  flex-shrink: 0;
}

.btn-icon:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

/* ---- Dialog ---- */
.dialog-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  z-index: 999;
}

.dialog {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 480px;
  max-width: 90vw;
  background: var(--bg-secondary);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-xl);
  z-index: 1000;
  box-shadow: var(--shadow-lg);
  display: flex;
  flex-direction: column;
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-5) var(--space-5) var(--space-3);
}

.dialog-header h3 {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--text-primary);
}

.dialog-header .btn-icon {
  opacity: 1;
  color: var(--text-muted);
}

.dialog-body {
  padding: 0 var(--space-5);
}

.textarea {
  width: 100%;
  padding: var(--space-3) var(--space-4);
  font-size: var(--text-sm);
  font-family: var(--font-sans);
  background: var(--bg-primary);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  outline: none;
  resize: vertical;
  min-height: 200px;
  line-height: 1.7;
  transition: border-color var(--transition-fast);
}

.textarea:focus {
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 3px var(--accent-glow);
}

.textarea::placeholder {
  color: var(--text-muted);
}

.dialog-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4) var(--space-5);
}

.dialog-footer-actions {
  display: flex;
  gap: var(--space-2);
}

.batch-hint {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.dialog-sm {
  width: 400px;
}

.confirm-body {
  padding-bottom: var(--space-2);
}

.confirm-body p {
  font-size: var(--text-sm);
  color: var(--text-primary);
  line-height: 1.5;
}

.confirm-body strong {
  color: var(--text-primary);
}

.confirm-hint {
  margin-top: var(--space-2);
  font-size: var(--text-xs) !important;
  color: var(--text-muted) !important;
}

.btn-danger {
  background: var(--error);
  border: 1px solid var(--error);
  color: #fff;
}

.btn-danger:hover {
  background: #dc2626;
  border-color: #dc2626;
}

/* ---- Transitions ---- */
.backdrop-enter-active,
.backdrop-leave-active {
  transition: opacity 0.2s ease;
}
.backdrop-enter-from,
.backdrop-leave-to {
  opacity: 0;
}

.dialog-enter-active,
.dialog-leave-active {
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}
.dialog-enter-from,
.dialog-leave-to {
  opacity: 0;
  transform: translate(-50%, -48%) scale(0.96);
}
</style>
