<template>
  <div class="accounts-page">
    <div class="toolbar">
      <button class="btn btn-primary btn-sm" @click="triggerImport">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
          <polyline points="17 8 12 3 7 8"/>
          <line x1="12" y1="3" x2="12" y2="15"/>
        </svg>
        导入JSON
      </button>
      <input ref="fileInput" type="file" accept=".json" @change="handleImport" style="display: none">

      <button class="btn btn-sm" @click="exportAccounts">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
          <polyline points="7 10 12 15 17 10"/>
          <line x1="12" y1="15" x2="12" y2="3"/>
        </svg>
        导出全部
      </button>

      <button class="btn btn-sm" @click="loadAccounts">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="23 4 23 10 17 10"/>
          <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
        </svg>
        刷新
      </button>

      <button v-if="accounts.length > 0" class="btn btn-sm btn-danger-text" @click="showDeleteConfirm = true">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="3 6 5 6 21 6"/>
          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
        </svg>
        删除全部
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

    <div v-if="accounts.length === 0" class="empty-state">
      <p class="empty-text">暂无对标账号数据</p>
    </div>

    <template v-else>
      <table class="accounts-table">
        <thead>
          <tr>
            <th width="50">#</th>
            <th width="80">头像</th>
            <th>昵称</th>
            <th width="120">粉丝数</th>
            <th width="120">获赞数</th>
            <th width="120">关注数</th>
            <th>认证信息</th>
            <th width="180">更新时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(acc, idx) in pagedAccounts" :key="acc.id">
            <td>{{ (currentPage - 1) * pageSize + idx + 1 }}</td>
            <td>
              <img v-if="acc.avatar" :src="acc.avatar" class="avatar-img" alt="">
              <div v-else class="avatar-placeholder">?</div>
            </td>
            <td>{{ acc.name || '-' }}</td>
            <td>{{ acc.fans_count || '-' }}</td>
            <td>{{ acc.like_count || '-' }}</td>
            <td>{{ acc.follow_count || '-' }}</td>
            <td>{{ acc.auth_info || '-' }}</td>
            <td>{{ acc.updated_at }}</td>
          </tr>
        </tbody>
      </table>

      <div v-if="totalPages > 1" class="pagination">
        <button class="page-btn" :disabled="currentPage <= 1" @click="currentPage = 1">首页</button>
        <button class="page-btn" :disabled="currentPage <= 1" @click="currentPage--">上一页</button>
        <span class="page-info">{{ currentPage }} / {{ totalPages }}</span>
        <button class="page-btn" :disabled="currentPage >= totalPages" @click="currentPage++">下一页</button>
        <button class="page-btn" :disabled="currentPage >= totalPages" @click="currentPage = totalPages">末页</button>
      </div>
    </template>

    <!-- Delete Confirm Dialog -->
    <Teleport to="body">
      <transition name="backdrop">
        <div v-if="showDeleteConfirm" class="dialog-backdrop" @click="showDeleteConfirm = false"></div>
      </transition>
      <transition name="dialog">
        <div v-if="showDeleteConfirm" class="dialog dialog-sm">
          <div class="dialog-header">
            <h3>确认删除</h3>
          </div>
          <div class="dialog-body">
            <p>确定要删除全部 <strong>{{ accounts.length }}</strong> 个账号吗？</p>
            <p class="confirm-hint">此操作不可恢复。</p>
          </div>
          <div class="dialog-footer">
            <button class="btn btn-sm" @click="showDeleteConfirm = false">取消</button>
            <button class="btn btn-sm btn-danger" @click="deleteAll">确认删除</button>
          </div>
        </div>
      </transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useAppStore } from '../stores/app'
import { useToast } from '../composables/useToast'

const appStore = useAppStore()
const { toast } = useToast()

const accounts = ref([])
const fileInput = ref(null)
const showDeleteConfirm = ref(false)

// 分页
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

watch(pageSize, () => { currentPage.value = 1 })

onMounted(() => {
  loadAccounts()
})

async function loadAccounts() {
  const result = await appStore.callApi('get_account_profiles')
  if (result && result.success) {
    accounts.value = result.profiles
  }
}

function triggerImport() {
  fileInput.value?.click()
}

async function handleImport(e) {
  const file = e.target.files[0]
  if (!file) return

  const reader = new FileReader()
  reader.onload = async (event) => {
    try {
      const data = JSON.parse(event.target.result)
      const result = await appStore.callApi('import_accounts', data)
      if (result && result.success) {
        toast.success(result.message)
        loadAccounts()
      } else {
        toast.error(result?.message || '导入失败')
      }
    } catch (err) {
      toast.error('JSON格式错误')
    }
  }
  reader.readAsText(file)
  e.target.value = ''
}

async function exportAccounts() {
  if (accounts.value.length === 0) {
    toast.warning('没有数据可导出')
    return
  }

  const result = await appStore.callApi('export_accounts_json')
  if (result && result.success) {
    toast.success(result.message)
  } else {
    toast.error(result?.message || '导出失败')
  }
}

async function deleteAll() {
  showDeleteConfirm.value = false
  const result = await appStore.callApi('delete_all_accounts')
  if (result && result.success) {
    accounts.value = []
    toast.success('已删除全部账号')
  } else {
    toast.error(result?.message || '删除失败')
  }
}
</script>

<style scoped>
.accounts-page {
  max-width: 100%;
}

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
  background: var(--bg-secondary);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  cursor: pointer;
}

.btn-danger-text {
  color: var(--text-muted);
}
.btn-danger-text:hover {
  color: var(--error) !important;
  background: rgba(239, 68, 68, 0.1) !important;
}

.empty-state {
  padding: var(--space-10) 0;
  text-align: center;
}

.empty-text {
  font-size: var(--text-sm);
  color: var(--text-muted);
}

.accounts-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm);
}

.accounts-table th {
  text-align: left;
  padding: var(--space-3);
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--surface-border);
  font-weight: 500;
  color: var(--text-secondary);
}

.accounts-table td {
  padding: var(--space-3);
  border-bottom: 1px solid var(--surface-border);
  color: var(--text-primary);
}

.avatar-img {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  object-fit: cover;
}

.avatar-placeholder {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--bg-hover);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
}

.pagination {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-top: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px solid var(--surface-border);
}

.page-btn {
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-xs);
  background: var(--bg-secondary);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  cursor: pointer;
}

.page-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-info {
  font-size: var(--text-xs);
  color: var(--text-muted);
  padding: 0 var(--space-2);
}

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
  width: 400px;
  background: var(--bg-secondary);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-xl);
  z-index: 1000;
  padding: var(--space-5);
}

.dialog-header h3 {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: var(--space-4);
}

.dialog-body p {
  font-size: var(--text-sm);
  color: var(--text-primary);
  margin-bottom: var(--space-2);
}

.confirm-hint {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.dialog-footer {
  display: flex;
  gap: var(--space-2);
  justify-content: flex-end;
  margin-top: var(--space-4);
}

.btn-danger {
  background: var(--error);
  color: #fff;
}

.backdrop-enter-active,
.backdrop-leave-active {
  transition: opacity 0.2s;
}
.backdrop-enter-from,
.backdrop-leave-to {
  opacity: 0;
}

.dialog-enter-active,
.dialog-leave-active {
  transition: all 0.2s;
}
.dialog-enter-from,
.dialog-leave-to {
  opacity: 0;
  transform: translate(-50%, -48%) scale(0.96);
}
</style>
