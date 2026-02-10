<template>
  <div class="debug-page">
    <!-- Tab Layout -->
    <div class="tab-bar">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        class="tab-item"
        :class="{ active: activeTab === tab.id }"
        @click="activeTab = tab.id"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- Tab: 账号监控 -->
    <div v-if="activeTab === 'monitor'" class="tab-content">
      <!-- Controls -->
      <div class="monitor-controls">
        <div class="control-row">
          <label class="control-label">账号链接</label>
          <div class="control-input-group">
            <input
              class="input"
              v-model="accountUrl"
              placeholder="https://www.toutiao.com/c/user/token/xxxxx"
            />
          </div>
        </div>
        <div class="control-row">
          <label class="control-label">起始时间</label>
          <div class="control-input-group">
            <input
              class="input"
              type="datetime-local"
              v-model="sinceTimeStr"
            />
            <span class="control-hint">只采集该时间点之后发布的文章</span>
          </div>
        </div>
        <div class="control-actions">
          <button
            class="btn btn-primary"
            @click="startCollect"
            :disabled="collecting || !accountUrl.trim()"
          >
            <svg v-if="!collecting" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"
              stroke-linecap="round" stroke-linejoin="round">
              <polygon points="5 3 19 12 5 21 5 3" />
            </svg>
            <span v-if="collecting" class="spinner"></span>
            {{ collecting ? '采集中...' : '开始采集' }}
          </button>
          <button v-if="collecting" class="btn" @click="stopCollect">
            停止
          </button>
          <span v-if="progressMsg" class="progress-text">{{ progressMsg }}</span>
        </div>
      </div>

      <!-- Summary -->
      <div v-if="summary && summary.total > 0" class="summary-bar">
        <div class="summary-item">
          <span class="summary-value">{{ summary.total }}</span>
          <span class="summary-label">文章</span>
        </div>
        <div class="summary-item">
          <span class="summary-value">{{ formatNum(summary.total_reads) }}</span>
          <span class="summary-label">总阅读</span>
        </div>
        <div class="summary-item">
          <span class="summary-value">{{ formatNum(summary.total_likes) }}</span>
          <span class="summary-label">总点赞</span>
        </div>
        <div class="summary-item">
          <span class="summary-value">{{ formatNum(summary.total_comments) }}</span>
          <span class="summary-label">总评论</span>
        </div>
        <div class="summary-item">
          <span class="summary-value">{{ formatNum(summary.avg_reads) }}</span>
          <span class="summary-label">平均阅读</span>
        </div>
        <div class="summary-item">
          <span class="summary-value">{{ formatNum(summary.avg_likes) }}</span>
          <span class="summary-label">平均点赞</span>
        </div>
      </div>

      <!-- Results Table -->
      <div v-if="articles.length > 0" class="result-section">
        <div class="result-header">
          <span class="result-count">共 {{ articles.length }} 篇文章</span>
        </div>
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th class="col-idx">#</th>
                <th class="col-title">标题</th>
                <th class="col-type">类型</th>
                <th class="col-num">阅读</th>
                <th class="col-num">展示</th>
                <th class="col-num">点赞</th>
                <th class="col-num">评论</th>
                <th class="col-num">分享</th>
                <th class="col-num">收藏</th>
                <th class="col-time">发布时间</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(art, idx) in articles" :key="art.group_id">
                <td class="col-idx">{{ idx + 1 }}</td>
                <td class="col-title">
                  <a :href="art.url" @click.prevent="openUrl(art.url)" :title="art.title">{{ art.title }}</a>
                </td>
                <td class="col-type">
                  <span class="type-badge" :class="`type-${art.content_type}`">{{ typeLabel(art.content_type) }}</span>
                </td>
                <td class="col-num">{{ formatNum(art.read_count) }}</td>
                <td class="col-num">{{ formatNum(art.show_count) }}</td>
                <td class="col-num">{{ formatNum(art.like_count) }}</td>
                <td class="col-num">{{ formatNum(art.comment_count) }}</td>
                <td class="col-num">{{ formatNum(art.share_count) }}</td>
                <td class="col-num">{{ formatNum(art.repin_count) }}</td>
                <td class="col-time">{{ art.publish_time_str }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useAppStore } from '../stores/app'
import { useToast } from '../composables/useToast'

const appStore = useAppStore()
const { toast } = useToast()

const tabs = [
  { id: 'monitor', label: '账号监控' },
]

const activeTab = ref('monitor')

// Monitor state
const accountUrl = ref('')
const sinceTimeStr = ref('')
const collecting = ref(false)
const progressMsg = ref('')
const articles = ref([])
const summary = ref(null)

// 设置默认时间为今天 00:00
onMounted(() => {
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  sinceTimeStr.value = formatDatetimeLocal(today)

  // 注册进度回调
  window.__onCollectProgress = (message, count) => {
    progressMsg.value = message
  }
})

onUnmounted(() => {
  delete window.__onCollectProgress
})

function formatDatetimeLocal(date) {
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function getSinceTimestamp() {
  if (!sinceTimeStr.value) return 0
  const d = new Date(sinceTimeStr.value)
  return Math.floor(d.getTime() / 1000)
}

async function startCollect() {
  if (!accountUrl.value.trim()) return
  collecting.value = true
  progressMsg.value = '启动中...'
  articles.value = []
  summary.value = null

  const result = await appStore.callApi(
    'collect_account',
    accountUrl.value.trim(),
    getSinceTimestamp()
  )

  collecting.value = false

  if (result && result.success) {
    articles.value = result.articles || []
    summary.value = result.summary || null
    progressMsg.value = ''
    toast.success(result.message)
  } else if (result) {
    progressMsg.value = ''
    toast.error(result.message)
  }
}

async function stopCollect() {
  await appStore.callApi('stop_collect')
  toast.info('已发送停止信号')
}

async function openUrl(url) {
  await appStore.callApi('open_in_browser', url)
}

function formatNum(n) {
  if (n === undefined || n === null) return '0'
  if (n >= 10000) return (n / 10000).toFixed(1) + 'w'
  if (n >= 1000) return (n / 1000).toFixed(1) + 'k'
  return String(n)
}

function typeLabel(t) {
  const map = { video: '视频', image: '图文', text: '文字' }
  return map[t] || t
}
</script>

<style scoped>
.debug-page {
  max-width: 100%;
}

/* ---- Tab Bar ---- */
.tab-bar {
  display: flex;
  gap: var(--space-1);
  margin-bottom: var(--space-6);
  border-bottom: 1px solid var(--surface-border);
  padding-bottom: 0;
}

.tab-item {
  padding: var(--space-3) var(--space-5);
  font-size: var(--text-sm);
  font-weight: 500;
  font-family: var(--font-sans);
  color: var(--text-secondary);
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  transition: all var(--transition-fast);
  margin-bottom: -1px;
}

.tab-item:hover {
  color: var(--text-primary);
}

.tab-item.active {
  color: var(--text-primary);
  border-bottom-color: var(--accent-primary);
}

/* ---- Monitor Controls ---- */
.monitor-controls {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  margin-bottom: var(--space-6);
}

.control-row {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.control-label {
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--text-secondary);
  min-width: 80px;
  flex-shrink: 0;
}

.control-input-group {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex: 1;
}

.control-input-group .input {
  max-width: 480px;
}

.control-input-sm {
  max-width: 100px !important;
}

.control-hint {
  font-size: var(--text-xs);
  color: var(--text-muted);
  white-space: nowrap;
}

.control-actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding-left: 96px;
}

.progress-text {
  font-size: var(--text-xs);
  color: var(--text-secondary);
}

.spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ---- Summary Bar ---- */
.summary-bar {
  display: flex;
  gap: var(--space-6);
  padding: var(--space-4) var(--space-5);
  background: var(--surface-primary);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-lg);
  margin-bottom: var(--space-5);
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.summary-value {
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--text-primary);
}

.summary-label {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

/* ---- Results Table ---- */
.result-section {
  margin-top: var(--space-2);
}

.result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-3);
}

.result-count {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.table-wrap {
  overflow-x: auto;
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-lg);
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm);
}

.data-table th {
  text-align: left;
  padding: var(--space-3) var(--space-3);
  font-weight: 500;
  font-size: var(--text-xs);
  color: var(--text-muted);
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--surface-border);
  white-space: nowrap;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.data-table td {
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--surface-border);
  vertical-align: middle;
}

.data-table tbody tr:last-child td {
  border-bottom: none;
}

.data-table tbody tr:hover {
  background: var(--bg-hover);
}

.col-idx {
  width: 40px;
  text-align: center;
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
}

.col-title {
  min-width: 240px;
  max-width: 400px;
}

.col-title a {
  color: var(--text-primary);
  text-decoration: none;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.4;
  transition: color var(--transition-fast);
}

.col-title a:hover {
  color: var(--accent-primary-hover);
}

.col-type {
  width: 60px;
}

.type-badge {
  font-size: var(--text-xs);
  padding: 2px 8px;
  border-radius: 4px;
  white-space: nowrap;
}

.type-video {
  background: rgba(239, 68, 68, 0.12);
  color: var(--error);
}

.type-image {
  background: rgba(59, 130, 246, 0.12);
  color: var(--info);
}

.type-text {
  background: rgba(34, 197, 94, 0.12);
  color: var(--success);
}

.col-num {
  width: 70px;
  text-align: right;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--text-secondary);
  white-space: nowrap;
}

.col-time {
  width: 140px;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--text-muted);
  white-space: nowrap;
}
</style>
