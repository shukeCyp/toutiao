<template>
  <div class="home">
    <div class="home-layout">
      <!-- Left: Create Task -->
      <div class="panel create-panel">
        <h3 class="panel-title">创建任务</h3>

        <div class="form-group">
          <label class="form-label">抓取类型</label>
          <select class="input" v-model="selectedType" :disabled="isRunning">
            <option value="" disabled>选择类型...</option>
            <option v-for="t in types" :key="t" :value="t">{{ t }}</option>
          </select>
          <span v-if="selectedType" class="form-hint">该类型下共 {{ typeAccountCount }} 个账号</span>
        </div>

        <div class="form-group">
          <label class="form-label">抓取数量</label>
          <div class="count-row">
            <input
              class="input count-input"
              type="number"
              v-model.number="count"
              :disabled="isRunning || collectAll"
              min="1"
              placeholder="数量"
            />
            <label class="checkbox-label">
              <input type="checkbox" v-model="collectAll" :disabled="isRunning" />
              <span>全部</span>
            </label>
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">起始时间</label>
          <input class="input" type="datetime-local" v-model="sinceTimeStr" :disabled="isRunning" />
          <span class="form-hint">只抓取该时间之后发布的文章</span>
        </div>

        <div class="form-actions">
          <button
            class="btn btn-primary"
            @click="startTask"
            :disabled="isRunning"
          >
            <svg v-if="!isRunning" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"
              stroke-linecap="round" stroke-linejoin="round">
              <polygon points="5 3 19 12 5 21 5 3" />
            </svg>
            <span v-if="isRunning" class="spinner"></span>
            {{ isRunning ? '运行中...' : '开始抓取' }}
          </button>
          <button v-if="isRunning" class="btn" @click="stopTask">
            停止任务
          </button>
        </div>
      </div>

      <!-- Right: Progress & Logs -->
      <div class="panel progress-panel">
        <h3 class="panel-title">任务进度</h3>

        <!-- Status -->
        <div class="status-row">
          <span class="status-badge" :class="`status-${taskStatus.status}`">{{ statusLabel }}</span>
          <span class="status-detail" v-if="taskStatus.total > 0">
            {{ taskStatus.completed }} / {{ taskStatus.total }} 个账号
          </span>
          <span class="status-detail" v-if="taskStatus.total_articles > 0">
            · {{ taskStatus.total_articles }} 篇文章
          </span>
        </div>

        <!-- Progress bar -->
        <div v-if="taskStatus.total > 0" class="progress-bar-wrap">
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: taskStatus.progress + '%' }"></div>
          </div>
          <span class="progress-pct">{{ taskStatus.progress }}%</span>
        </div>

        <!-- Stats -->
        <div v-if="taskStatus.completed > 0" class="mini-stats">
          <span class="mini-stat success">成功 {{ taskStatus.success }}</span>
          <span v-if="taskStatus.failed > 0" class="mini-stat fail">失败 {{ taskStatus.failed }}</span>
        </div>

        <!-- Log list -->
        <div class="log-section">
          <div class="log-header">
            <span class="log-title">日志</span>
            <span class="log-count">{{ taskStatus.logs?.length || 0 }} 条</span>
          </div>
          <div class="log-list" ref="logListRef">
            <div v-if="!taskStatus.logs || taskStatus.logs.length === 0" class="log-empty">
              暂无日志，创建任务后将在此显示
            </div>
            <div
              v-for="(entry, i) in taskStatus.logs"
              :key="i"
              class="log-entry"
              :class="`log-${entry.level}`"
            >
              <span class="log-time">{{ entry.time }}</span>
              <span class="log-msg">{{ entry.message }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useAppStore } from '../stores/app'
import { useToast } from '../composables/useToast'

const appStore = useAppStore()
const { toast } = useToast()

// Form state
const types = ref([])
const selectedType = ref('')
const count = ref(10)
const collectAll = ref(false)
const sinceTimeStr = ref('')

// Task state
const taskStatus = ref({
  status: 'idle',
  total: 0,
  completed: 0,
  success: 0,
  failed: 0,
  total_articles: 0,
  progress: 0,
  logs: [],
})

const logListRef = ref(null)
let pollTimer = null

const isRunning = computed(() => taskStatus.value.status === 'running')

const statusLabel = computed(() => {
  const map = {
    idle: '空闲',
    running: '运行中',
    completed: '已完成',
    failed: '失败',
    stopped: '已停止',
  }
  return map[taskStatus.value.status] || taskStatus.value.status
})

const typeAccountCount = computed(() => {
  // Will be loaded on type change
  return typeCountCache.value
})

const typeCountCache = ref(0)

// Load types on mount
onMounted(async () => {
  // Set default time to today 00:00
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  sinceTimeStr.value = formatDatetimeLocal(today)

  const r = await appStore.callApi('get_account_types')
  if (r && r.success) {
    types.value = r.types
  }

  // Check if there's already a running task
  await pollStatus()
  if (isRunning.value) {
    startPolling()
  }
})

onUnmounted(() => {
  stopPolling()
})

// Load account count when type changes
watch(selectedType, async (t) => {
  if (!t) { typeCountCache.value = 0; return }
  const r = await appStore.callApi('get_accounts', t)
  if (r && r.success) {
    typeCountCache.value = r.accounts.length
  }
})

// Auto-scroll log
watch(() => taskStatus.value.logs?.length, () => {
  nextTick(() => {
    if (logListRef.value) {
      logListRef.value.scrollTop = logListRef.value.scrollHeight
    }
  })
})

function formatDatetimeLocal(date) {
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function getSinceTimestamp() {
  if (!sinceTimeStr.value) return 0
  return Math.floor(new Date(sinceTimeStr.value).getTime() / 1000)
}

async function startTask() {
  if (!selectedType.value) {
    toast.warning('请先选择抓取类型')
    return
  }

  const c = collectAll.value ? 0 : (count.value || 0)
  const result = await appStore.callApi(
    'start_batch_collect',
    selectedType.value,
    c,
    getSinceTimestamp()
  )

  if (result && result.success) {
    toast.success(result.message)
    startPolling()
  } else if (result) {
    toast.error(result.message)
  }
}

async function stopTask() {
  const r = await appStore.callApi('stop_batch_task')
  if (r && r.success) {
    toast.info('已发送停止信号')
  }
}

async function pollStatus() {
  const r = await appStore.callApi('get_task_status')
  if (r) {
    taskStatus.value = r
  }
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(async () => {
    await pollStatus()
    if (!isRunning.value) {
      stopPolling()
    }
  }, 2000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}
</script>

<style scoped>
.home {
  max-width: 100%;
  height: calc(100vh - 64px);
  overflow: hidden;
}

.home-layout {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: var(--space-6);
  height: 100%;
}

/* Panel */
.panel {
  background: var(--surface-primary);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  overflow: hidden;
}

.create-panel {
  align-self: flex-start;
}

.progress-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.panel-title {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: var(--space-5);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

/* Form */
.form-group {
  margin-bottom: var(--space-5);
}

.form-label {
  display: block;
  font-size: var(--text-xs);
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: var(--space-2);
}

.form-hint {
  display: block;
  font-size: var(--text-xs);
  color: var(--text-muted);
  margin-top: var(--space-1);
}

.form-group .input {
  width: 100%;
}

.count-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.count-input {
  width: 100px !important;
  flex-shrink: 0;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
  color: var(--text-secondary);
  cursor: pointer;
  white-space: nowrap;
}

.checkbox-label input[type="checkbox"] {
  width: 16px;
  height: 16px;
  accent-color: var(--accent-primary);
  cursor: pointer;
}

.form-actions {
  display: flex;
  gap: var(--space-2);
  margin-top: var(--space-6);
}

.spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
  margin-right: 4px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Status */
.status-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.status-badge {
  font-size: var(--text-xs);
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 9999px;
}

.status-idle { background: var(--bg-hover); color: var(--text-muted); }
.status-running { background: rgba(59,130,246,0.15); color: var(--info); }
.status-completed { background: rgba(34,197,94,0.15); color: var(--success); }
.status-failed { background: rgba(239,68,68,0.15); color: var(--error); }
.status-stopped { background: rgba(234,179,8,0.15); color: var(--warning); }

.status-detail {
  font-size: var(--text-xs);
  color: var(--text-secondary);
}

/* Progress bar */
.progress-bar-wrap {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.progress-bar {
  flex: 1;
  height: 6px;
  background: var(--surface-border);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--accent-primary);
  border-radius: 3px;
  transition: width 0.3s ease;
}

.progress-pct {
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--text-secondary);
  min-width: 36px;
  text-align: right;
}

/* Mini stats */
.mini-stats {
  display: flex;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.mini-stat {
  font-size: var(--text-xs);
  font-weight: 500;
}

.mini-stat.success { color: var(--success); }
.mini-stat.fail { color: var(--error); }

/* Log section */
.log-section {
  margin-top: var(--space-4);
  border-top: 1px solid var(--surface-border);
  padding-top: var(--space-4);
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.log-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-3);
}

.log-title {
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.log-count {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.log-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-height: 0;
}

.log-empty {
  font-size: var(--text-xs);
  color: var(--text-muted);
  padding: var(--space-6) 0;
  text-align: center;
}

.log-entry {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  line-height: 1.5;
}

.log-entry:hover {
  background: var(--bg-hover);
}

.log-time {
  font-family: var(--font-mono);
  color: var(--text-muted);
  flex-shrink: 0;
  min-width: 56px;
}

.log-msg {
  color: var(--text-secondary);
  word-break: break-all;
}

.log-info .log-msg { color: var(--text-secondary); }
.log-success .log-msg { color: var(--success); }
.log-error .log-msg { color: var(--error); }
.log-warning .log-msg { color: var(--warning); }
</style>
