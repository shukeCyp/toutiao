<template>
  <div class="articles-page">
    <div class="page-header">
      <h1>文章</h1>
      <p>管理已采集的文章，支持改写和删除操作</p>
    </div>

    <!-- Toolbar -->
    <div class="toolbar">
      <div class="toolbar-left">
        <select class="select filter-select" v-model="filter" @change="onFilterChange">
          <option value="all">全部 ({{ stats.total }})</option>
          <option value="pending">待改写 ({{ stats.pending }})</option>
          <option value="rewritten">已改写 ({{ stats.rewritten }})</option>
        </select>
        <span class="page-info-text">共 {{ total }} 篇</span>
      </div>
      <div class="toolbar-right">
        <button class="btn btn-sm" @click="openImportDialog">
          导入
        </button>
        <button
          class="btn btn-sm"
          :disabled="batchDownloading || stats.total === 0"
          @click="downloadAll"
        >
          <span v-if="batchDownloading" class="spinner-sm"></span>
          {{ batchDownloading ? `下载中 ${downloadProgress.current}/${downloadProgress.total}` : '下载全部' }}
        </button>
        <button class="btn btn-sm btn-primary" @click="openRewriteDialog" :disabled="batchRewriting">
          全部改写
        </button>
        <button class="btn btn-sm btn-danger-outline" @click="confirmDeleteAll" :disabled="stats.total === 0">
          全部删除
        </button>
      </div>
    </div>

    <!-- Article List -->
    <div v-if="articles.length === 0 && !loading" class="empty-state">
      <p class="empty-text">暂无文章数据，请先采集文章</p>
    </div>

    <div v-else class="article-list">
      <div v-for="art in articles" :key="art.id" class="article-row">
        <div class="article-main">
          <div class="article-title-line">
            <span class="type-badge" :class="`type-${art.content_type}`">{{ typeLabel(art.content_type) }}</span>
            <span class="article-title">{{ art.title }}</span>
          </div>
          <div class="article-meta">
            <span>{{ art.source || art.user_name }}</span>
            <span class="meta-dot"></span>
            <span>{{ art.publish_time_str }}</span>
            <span class="meta-dot"></span>
            <span>阅读 {{ formatNum(art.read_count) }}</span>
            <span class="meta-dot"></span>
            <span class="rewrite-badge" :class="art.is_rewritten ? 'done' : 'pending'">
              {{ art.is_rewritten ? '已改写' : '待改写' }}
            </span>
          </div>
        </div>
        <div class="article-actions">
          <button
            class="btn btn-xs"
            :class="rewritingId === art.id ? '' : 'btn-primary'"
            :disabled="rewritingId === art.id"
            @click.stop="rewriteOne(art)"
          >
            <span v-if="rewritingId === art.id" class="spinner-sm"></span>
            {{ rewritingId === art.id ? '改写中' : '改写' }}
          </button>
          <button class="btn btn-xs" @click.stop="openUrl(art.url)">打开</button>
          <button class="btn btn-xs btn-danger-text" @click.stop="deleteOne(art)">删除</button>
        </div>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="totalPages > 1" class="pagination">
      <button class="page-btn" :disabled="page <= 1" @click="goPage(page - 1)">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6" /></svg>
      </button>
      <span class="page-info-text">{{ page }} / {{ totalPages }}</span>
      <button class="page-btn" :disabled="page >= totalPages" @click="goPage(page + 1)">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6" /></svg>
      </button>
    </div>

    <!-- Import Dialog -->
    <Teleport to="body">
      <transition name="backdrop">
        <div v-if="showImportDialog" class="dialog-backdrop" @click="closeImportDialog"></div>
      </transition>
      <transition name="dialog">
        <div v-if="showImportDialog" class="dialog">
          <div class="dialog-header">
            <h3>导入文章链接</h3>
            <button class="btn-icon" @click="closeImportDialog" :disabled="importing">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
          <div class="dialog-body">
            <p class="dialog-hint">请输入文章链接，每行一个。支持头条文章链接格式。</p>
            <textarea
              class="import-textarea"
              v-model="importText"
              placeholder="https://www.toutiao.com/article/7473002025927541286/&#10;https://www.toutiao.com/article/7473002025927541287/&#10;..."
              rows="10"
              :disabled="importing"
            ></textarea>
            <p class="import-count" v-if="importLineCount > 0">
              共 {{ importLineCount }} 个链接
            </p>
          </div>
          <div class="dialog-footer">
            <button class="btn" @click="closeImportDialog" :disabled="importing">取消</button>
            <button class="btn btn-primary" @click="startImport" :disabled="importing || importLineCount === 0">
              <span v-if="importing" class="spinner-sm"></span>
              {{ importing ? '导入中...' : '开始导入' }}
            </button>
          </div>
        </div>
      </transition>
    </Teleport>

    <!-- Rewrite Dialog -->
    <Teleport to="body">
      <transition name="backdrop">
        <div v-if="showRewriteDialog" class="dialog-backdrop" @click="closeRewriteDialog"></div>
      </transition>
      <transition name="dialog">
        <div v-if="showRewriteDialog" class="dialog">
          <div class="dialog-header">
            <h3>批量改写文章</h3>
            <button class="btn-icon" @click="closeRewriteDialog" :disabled="batchRewriting">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
          <div class="dialog-body">
            <div class="dialog-stats">
              <div class="dialog-stat">
                <span class="dialog-stat-val">{{ stats.total }}</span>
                <span class="dialog-stat-lbl">全部文章</span>
              </div>
              <div class="dialog-stat">
                <span class="dialog-stat-val done">{{ stats.rewritten }}</span>
                <span class="dialog-stat-lbl">已改写</span>
              </div>
              <div class="dialog-stat">
                <span class="dialog-stat-val pending">{{ stats.pending }}</span>
                <span class="dialog-stat-lbl">未改写</span>
              </div>
            </div>

            <label class="checkbox-label" @click.prevent="forceRewrite = !forceRewrite">
              <span class="checkbox" :class="{ checked: forceRewrite }">
                <svg v-if="forceRewrite" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </span>
              <span>强制改写全部文章（包括已改写的）</span>
            </label>

            <p class="dialog-hint">
              {{ forceRewrite ? `将改写全部 ${stats.total} 篇文章` : `将改写 ${stats.pending} 篇未改写的文章` }}
            </p>

            <!-- Progress -->
            <div v-if="batchRewriting" class="rewrite-progress">
              <div class="progress-bar">
                <div class="progress-fill" :style="{ width: progressPct + '%' }"></div>
              </div>
              <p class="progress-text">正在改写 {{ rewriteProgress.current }} / {{ rewriteProgress.total }}：{{ rewriteProgress.title }}</p>
            </div>
          </div>
          <div class="dialog-footer">
            <button class="btn" @click="closeRewriteDialog" :disabled="batchRewriting">取消</button>
            <button class="btn btn-primary" @click="startBatchRewrite" :disabled="batchRewriting || targetCount === 0">
              <span v-if="batchRewriting" class="spinner-sm"></span>
              {{ batchRewriting ? '改写中...' : '开始改写' }}
            </button>
          </div>
        </div>
      </transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useAppStore } from '../stores/app'
import { useToast } from '../composables/useToast'

const appStore = useAppStore()
const { toast } = useToast()

const articles = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const totalPages = ref(1)
const filter = ref('all')
const loading = ref(false)
const stats = ref({ total: 0, rewritten: 0, pending: 0 })
const rewritingId = ref(null)

// Import dialog state
const showImportDialog = ref(false)
const importText = ref('')
const importing = ref(false)
const importLineCount = computed(() => {
  return importText.value.trim().split('\n').filter(l => l.trim()).length
})

// Download all state
const batchDownloading = ref(false)
const downloadProgress = reactive({ current: 0, total: 0 })

// Rewrite dialog state
const showRewriteDialog = ref(false)
const forceRewrite = ref(false)
const batchRewriting = ref(false)
const rewriteProgress = reactive({ current: 0, total: 0, title: '' })

const targetCount = computed(() => forceRewrite.value ? stats.value.total : stats.value.pending)
const progressPct = computed(() =>
  rewriteProgress.total > 0 ? Math.round(rewriteProgress.current / rewriteProgress.total * 100) : 0
)

onMounted(() => {
  loadStats()
  loadArticles()
  window.__onRewriteProgress = onRewriteProgress
  window.__onDownloadProgress = onDownloadProgress
})

onUnmounted(() => {
  window.__onRewriteProgress = null
  window.__onDownloadProgress = null
})

function onRewriteProgress(current, total, title) {
  rewriteProgress.current = current
  rewriteProgress.total = total
  rewriteProgress.title = title
}

function onDownloadProgress(articleId, title, current, total) {
  downloadProgress.current = current
  downloadProgress.total = total
}

// ------ Import ------

function openImportDialog() {
  importText.value = ''
  showImportDialog.value = true
}

function closeImportDialog() {
  if (importing.value) return
  showImportDialog.value = false
}

async function startImport() {
  importing.value = true
  const r = await appStore.callApi('import_article_urls', importText.value)
  importing.value = false

  if (r && r.success) {
    toast.success(r.message)
    showImportDialog.value = false
    loadArticles()
    loadStats()
  } else if (r) {
    toast.error(r.message)
  }
}

// ------ Download All ------

async function downloadAll() {
  batchDownloading.value = true
  downloadProgress.current = 0
  downloadProgress.total = 0

  const r = await appStore.callApi('download_all_articles')

  batchDownloading.value = false

  if (r && r.success) {
    toast.success(r.message)
    loadArticles()
    loadStats()
  } else if (r) {
    toast.error(r.message)
  }
}

async function loadStats() {
  const r = await appStore.callApi('get_article_stats')
  if (r && r.success) {
    stats.value = { total: r.total, rewritten: r.rewritten, pending: r.pending }
  }
}

async function loadArticles() {
  loading.value = true
  const filterVal = filter.value === 'rewritten' ? true : filter.value === 'pending' ? false : null
  const r = await appStore.callApi('get_articles', page.value, pageSize, filterVal)
  loading.value = false
  if (r && r.success) {
    articles.value = r.articles
    total.value = r.total
    totalPages.value = Math.ceil(r.total / pageSize) || 1
  }
}

function onFilterChange() {
  page.value = 1
  loadArticles()
}

function goPage(p) {
  page.value = p
  loadArticles()
}

async function rewriteOne(art) {
  rewritingId.value = art.id
  const r = await appStore.callApi('rewrite_article', art.id)
  rewritingId.value = null

  if (r && r.success) {
    toast.success('改写完成')
    // 同步列表
    const idx = articles.value.findIndex(a => a.id === art.id)
    if (idx !== -1) articles.value[idx].is_rewritten = true
    loadStats()
  } else if (r) {
    toast.error(r.message)
  }
}

async function deleteOne(art) {
  const r = await appStore.callApi('delete_article', art.id)
  if (r && r.success) {
    toast.success('已删除')
    loadArticles()
    loadStats()
  }
}

async function confirmDeleteAll() {
  if (!confirm(`确定要删除全部 ${stats.value.total} 篇文章吗？此操作不可恢复。`)) return
  const r = await appStore.callApi('delete_all_articles')
  if (r && r.success) {
    toast.success(r.message)
    loadArticles()
    loadStats()
  } else if (r) {
    toast.error(r.message)
  }
}

function openRewriteDialog() {
  loadStats()
  forceRewrite.value = false
  rewriteProgress.current = 0
  rewriteProgress.total = 0
  rewriteProgress.title = ''
  showRewriteDialog.value = true
}

function closeRewriteDialog() {
  if (batchRewriting.value) return
  showRewriteDialog.value = false
}

async function startBatchRewrite() {
  batchRewriting.value = true
  rewriteProgress.current = 0
  rewriteProgress.total = targetCount.value
  rewriteProgress.title = ''

  const r = await appStore.callApi('batch_rewrite_articles', forceRewrite.value)

  batchRewriting.value = false

  if (r && r.success) {
    toast.success(r.message)
    showRewriteDialog.value = false
    loadArticles()
    loadStats()
  } else if (r) {
    toast.error(r.message)
  }
}

async function openUrl(url) {
  await appStore.callApi('open_in_browser', url)
}

function formatNum(n) {
  if (!n) return '0'
  if (n >= 10000) return (n / 10000).toFixed(1) + 'w'
  if (n >= 1000) return (n / 1000).toFixed(1) + 'k'
  return String(n)
}

function typeLabel(t) {
  return { video: '视频', image: '图文', text: '文字' }[t] || t
}
</script>

<style scoped>
.articles-page {
  max-width: 100%;
}

/* Toolbar */
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-4);
  gap: var(--space-3);
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.toolbar-right {
  display: flex;
  gap: var(--space-2);
}

.filter-select {
  min-width: 160px;
}

.select {
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm);
  font-family: var(--font-sans);
  color: var(--text-primary);
  background: var(--surface-secondary);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  outline: none;
  transition: border-color var(--transition-fast);
  appearance: auto;
}

.select:focus {
  border-color: var(--accent-primary);
}

.page-info-text {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

/* Empty */
.empty-state { padding: var(--space-10) 0; }
.empty-text { font-size: var(--text-sm); color: var(--text-muted); }

/* Article list */
.article-list {
  display: flex;
  flex-direction: column;
}

.article-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-2);
  border-radius: var(--radius-md);
  transition: background var(--transition-fast);
  gap: var(--space-4);
}

.article-row:hover { background: var(--bg-hover); }

.article-main { min-width: 0; flex: 1; }

.article-title-line {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: 4px;
}

.article-title {
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.type-badge {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 4px;
  white-space: nowrap;
  flex-shrink: 0;
}
.type-video { background: rgba(239,68,68,0.12); color: var(--error); }
.type-image { background: rgba(59,130,246,0.12); color: var(--info); }
.type-text { background: rgba(34,197,94,0.12); color: var(--success); }

.article-meta {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.meta-dot {
  width: 3px; height: 3px;
  border-radius: 50%;
  background: var(--text-muted);
  opacity: 0.5;
}

.rewrite-badge {
  font-size: var(--text-xs);
  padding: 1px 8px;
  border-radius: 9999px;
  font-weight: 500;
}
.rewrite-badge.done {
  background: rgba(34,197,94,0.12);
  color: var(--success);
}
.rewrite-badge.pending {
  background: rgba(234,179,8,0.12);
  color: var(--warning);
}

/* Actions */
.article-actions {
  display: flex;
  gap: var(--space-1);
  flex-shrink: 0;
}

.btn-xs {
  padding: 3px 10px;
  font-size: var(--text-xs);
}

.btn-danger-text { color: var(--text-muted); }
.btn-danger-text:hover { color: var(--error) !important; background: rgba(239,68,68,0.1) !important; }

.btn-danger-outline {
  color: var(--error);
  border-color: rgba(239,68,68,0.3);
}
.btn-danger-outline:hover {
  background: rgba(239,68,68,0.1) !important;
}

/* Spinner */
.spinner-sm {
  display: inline-block;
  width: 12px; height: 12px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: currentColor;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
  margin-right: 4px;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* Pagination */
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  margin-top: var(--space-5);
  padding-top: var(--space-4);
  border-top: 1px solid var(--surface-border);
}

.page-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px; height: 30px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
}
.page-btn:hover:not(:disabled) { background: var(--bg-hover); color: var(--text-primary); }
.page-btn:disabled { opacity: 0.3; cursor: not-allowed; }

/* Dialog */
.dialog-backdrop {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.5);
  z-index: 999;
}

.dialog {
  position: fixed;
  top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  width: 480px; max-width: 90vw;
  background: var(--bg-secondary);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-lg);
  z-index: 1000;
  box-shadow: 0 16px 48px rgba(0,0,0,0.4);
  display: flex;
  flex-direction: column;
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-5);
  border-bottom: 1px solid var(--surface-border);
}

.dialog-header h3 {
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--text-primary);
}

.btn-icon {
  width: 28px; height: 28px;
  display: flex; align-items: center; justify-content: center;
  border: none; background: transparent;
  color: var(--text-tertiary);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
}
.btn-icon:hover { background: var(--bg-hover); color: var(--text-primary); }

.dialog-body {
  padding: var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.dialog-stats {
  display: flex;
  gap: var(--space-3);
}

.dialog-stat {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: var(--space-3);
  background: var(--bg-primary);
  border-radius: var(--radius-md);
  border: 1px solid var(--surface-border);
  text-align: center;
}

.dialog-stat-val {
  font-size: var(--text-xl);
  font-weight: 700;
  color: var(--text-primary);
}

.dialog-stat-val.done { color: var(--success); }
.dialog-stat-val.pending { color: var(--warning); }

.dialog-stat-lbl {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

/* Checkbox */
.checkbox-label {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  cursor: pointer;
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.checkbox {
  width: 18px; height: 18px;
  border: 1.5px solid var(--surface-border);
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all var(--transition-fast);
  color: #fff;
}

.checkbox.checked {
  background: var(--accent-primary);
  border-color: var(--accent-primary);
}

.dialog-hint {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

/* Progress */
.rewrite-progress {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.progress-bar {
  width: 100%;
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

.progress-text {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
  padding: var(--space-4) var(--space-5);
  border-top: 1px solid var(--surface-border);
}

/* Import textarea */
.import-textarea {
  width: 100%;
  min-height: 200px;
  padding: var(--space-3);
  font-size: var(--text-sm);
  font-family: var(--font-mono, 'SF Mono', 'Monaco', 'Consolas', monospace);
  line-height: 1.6;
  color: var(--text-primary);
  background: var(--bg-primary);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-md);
  resize: vertical;
  outline: none;
  transition: border-color var(--transition-fast);
  box-sizing: border-box;
}

.import-textarea:focus {
  border-color: var(--accent-primary);
}

.import-textarea::placeholder {
  color: var(--text-muted);
  opacity: 0.6;
}

.import-textarea:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.import-count {
  font-size: var(--text-xs);
  color: var(--text-muted);
  margin: 0;
}

/* Transitions */
.backdrop-enter-active, .backdrop-leave-active { transition: opacity 0.2s ease; }
.backdrop-enter-from, .backdrop-leave-to { opacity: 0; }
.dialog-enter-active, .dialog-leave-active { transition: all 0.2s ease; }
.dialog-enter-from, .dialog-leave-to { opacity: 0; transform: translate(-50%, -48%); }
</style>
