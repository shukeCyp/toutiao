<template>
  <div class="profiles-page">
    <div class="toolbar">
      <button class="btn btn-primary btn-sm" @click="triggerFileInput">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
          <polyline points="17 8 12 3 7 8"/>
          <line x1="12" y1="3" x2="12" y2="15"/>
        </svg>
        导入TXT
      </button>
      <input ref="fileInput" type="file" accept=".txt" @change="handleFileSelect" style="display: none">

      <button class="btn btn-sm" @click="fetchAllProfiles" :disabled="tempAccounts.length === 0 || fetching">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="23 4 23 10 17 10"/>
          <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
        </svg>
        {{ fetching ? '获取中...' : '开始获取信息' }}
      </button>

      <span class="toolbar-sep"></span>
      <span class="toolbar-count">{{ allAccounts.length }} 个账号</span>
    </div>

    <div v-if="allAccounts.length === 0" class="empty-state">
      <p class="empty-text">请导入TXT文件开始</p>
    </div>

    <table v-else class="profiles-table">
      <thead>
        <tr>
          <th width="50">#</th>
          <th width="80">头像</th>
          <th>昵称</th>
          <th width="120">粉丝数</th>
          <th width="120">获赞数</th>
          <th width="120">关注数</th>
          <th>认证信息</th>
          <th width="100">状态</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(acc, idx) in allAccounts" :key="idx">
          <td>{{ idx + 1 }}</td>
          <td>
            <img v-if="acc.avatar" :src="acc.avatar" class="avatar-img" alt="">
            <div v-else class="avatar-placeholder">?</div>
          </td>
          <td>{{ acc.name || '-' }}</td>
          <td>{{ acc.fans_count || '-' }}</td>
          <td>{{ acc.like_count || '-' }}</td>
          <td>{{ acc.follow_count || '-' }}</td>
          <td>{{ acc.auth_info || '-' }}</td>
          <td>
            <span class="status" :class="acc.status">{{ getStatusText(acc.status) }}</span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useAppStore } from '../stores/app'
import { useToast } from '../composables/useToast'

const appStore = useAppStore()
const { toast } = useToast()

const fileInput = ref(null)
const tempAccounts = ref([])
const allAccounts = ref([]) // 保存所有已获取的账号
const fetching = ref(false)

function triggerFileInput() {
  fileInput.value?.click()
}

function handleFileSelect(e) {
  const file = e.target.files[0]
  if (!file) return

  const reader = new FileReader()
  reader.onload = (event) => {
    const text = event.target.result
    const urls = text.split('\n').map(l => l.trim()).filter(l => l)

    tempAccounts.value = urls.map(url => ({
      url,
      name: '',
      avatar: '',
      fans_count: '',
      like_count: '',
      follow_count: '',
      auth_info: '',
      status: 'pending'
    }))

    // 合并到总列表
    allAccounts.value = [...tempAccounts.value, ...allAccounts.value]

    toast.success(`已导入 ${urls.length} 个账号`)
  }
  reader.readAsText(file)
  e.target.value = ''
}

async function fetchAllProfiles() {
  if (tempAccounts.value.length === 0) return

  fetching.value = true

  let success = 0
  let skipped = 0
  let failed = 0

  for (let i = 0; i < tempAccounts.value.length; i++) {
    const acc = tempAccounts.value[i]
    acc.status = 'fetching'

    const result = await appStore.callApi('fetch_and_save_account_profile', acc.url)

    if (result && result.success) {
      if (result.skipped && result.profile) {
        acc.name = result.profile.name || ''
        acc.avatar = result.profile.avatar || ''
        acc.fans_count = result.profile.fans_count || ''
        acc.like_count = result.profile.like_count || ''
        acc.follow_count = result.profile.follow_count || ''
        acc.auth_info = result.profile.auth_info || ''
        acc.status = 'skipped'
        skipped++
      } else if (result.profile) {
        acc.name = result.profile.name || ''
        acc.avatar = result.profile.avatar || ''
        acc.fans_count = result.profile.fans_count || ''
        acc.like_count = result.profile.like_count || ''
        acc.follow_count = result.profile.follow_count || ''
        acc.auth_info = result.profile.auth_info || ''
        acc.status = 'success'
        success++
      }
    } else {
      acc.status = 'failed'
      failed++
    }
  }

  fetching.value = false
  toast.success(`获取完成 - 成功: ${success}, 跳过: ${skipped}, 失败: ${failed}`)
}

function getStatusText(status) {
  const map = {
    pending: '待获取',
    fetching: '获取中',
    success: '成功',
    skipped: '已存在',
    failed: '失败'
  }
  return map[status] || '-'
}
</script>

<style scoped>
.profiles-page {
  max-width: 100%;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
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

.empty-state {
  padding: var(--space-10) 0;
  text-align: center;
}

.empty-text {
  font-size: var(--text-sm);
  color: var(--text-muted);
}

.profiles-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm);
}

.profiles-table th {
  text-align: left;
  padding: var(--space-3);
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--surface-border);
  font-weight: 500;
  color: var(--text-secondary);
}

.profiles-table td {
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

.status {
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
}

.status.pending {
  background: var(--bg-hover);
  color: var(--text-muted);
}

.status.fetching {
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
}

.status.success {
  background: rgba(34, 197, 94, 0.1);
  color: #22c55e;
}

.status.skipped {
  background: rgba(251, 191, 36, 0.1);
  color: #fbbf24;
}

.status.failed {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}
</style>
