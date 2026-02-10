<template>
  <div class="downloads-page">
    <div class="page-header">
      <h1>文章下载</h1>
      <p>批量下载文章为 docx 文档</p>
    </div>

    <!-- Stats cards -->
    <div class="stats-row">
      <div class="card stat-card">
        <span class="stat-val">{{ stats.total }}</span>
        <span class="stat-lbl">全部文章</span>
      </div>
      <div class="card stat-card">
        <span class="stat-val downloaded">{{ stats.downloaded }}</span>
        <span class="stat-lbl">已下载</span>
      </div>
      <div class="card stat-card">
        <span class="stat-val pending">{{ stats.not_downloaded }}</span>
        <span class="stat-lbl">未下载</span>
      </div>
    </div>

    <!-- Filter & actions bar -->
    <div class="toolbar">
      <div class="filter-tabs">
        <button class="filter-tab" :class="{ active: filter === 'all' }" @click="setFilter('all')">
          全部
        </button>
        <button class="filter-tab" :class="{ active: filter === 'not_downloaded' }" @click="setFilter('not_downloaded')">
          未下载
        </button>
        <button class="filter-tab" :class="{ active: filter === 'downloaded' }" @click="setFilter('downloaded')">
          已下载
        </button>
      </div>
      <div class="toolbar-right">
        <button
          v-if="selectedIds.size > 0"
          class="btn btn-primary btn-sm"
          :disabled="batchDownloading"
          @click="batchDownload"
        >
          <span v-if="batchDownloading" class="spinner-sm"></span>
          {{ batchDownloading ? `下载中 ${downloadProgress.current}/${downloadProgress.total}` : `下载选中 (${selectedIds.size})` }}
        </button>
        <button
          v-if="filter === 'not_downloaded' && articles.length > 0"
          class="btn btn-sm"
          :disabled="batchDownloading"
          @click="downloadAll"
        >
          全部下载
        </button>
      </div>
    </div>

    <!-- Article List -->
    <div v-if="articles.length === 0 && !loading" class="empty-state">
      <p class="empty-text">
        {{ filter === 'downloaded' ? '暂无已下载的文章' : filter === 'not_downloaded' ? '所有文章已下载完成' : '暂无文章数据，请先采集文章' }}
      </p>
    </div>

    <div v-else class="article-list">
      <!-- Select all -->
      <div v-if="articles.length > 0" class="select-all-row">
        <label class="checkbox-label" @click.prevent="toggleSelectAll">
          <span class="checkbox" :class="{ checked: isAllSelected, indeterminate: isPartialSelected }">
            <svg v-if="isAllSelected" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="20 6 9 17 4 12" />
            </svg>
            <svg v-else-if="isPartialSelected" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round">
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
          </span>
          <span class="select-all-text">全选当前页</span>
        </label>
      </div>

      <div
        v-for="art in articles"
        :key="art.id"
        class="article-row"
        :class="{ selected: selectedIds.has(art.id) }"
        @click="toggleSelect(art.id)"
      >
        <span class="checkbox" :class="{ checked: selectedIds.has(art.id) }">
          <svg v-if="selectedIds.has(art.id)" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        </span>
        <div class="article-main">
          <div class="article-title-line">
            <span class="type-badge" :class="`type-${art.content_type}`">{{ typeLabel(art.content_type) }}</span>
            <span class="article-title">{{ art.title }}</span>
          </div>
          <div class="article-meta">
            <span>{{ art.source || art.user_name }}</span>
            <span class="meta-dot"></span>
            <span>{{ art.publish_time_str }}</span>
            <span v-if="art.category" class="meta-dot"></span>
            <span v-if="art.category">{{ art.category }}</span>
          </div>
        </div>
        <div class="article-right">
          <span v-if="downloadingIds.has(art.id)" class="download-status downloading">
            <span class="spinner-sm"></span> 下载中
          </span>
          <span v-else-if="art.doc_path" class="download-status done">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
              <polyline points="22 4 12 14.01 9 11.01" />
            </svg>
            已下载
          </span>
          <span v-else class="download-status not-downloaded">未下载</span>
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
const stats = ref({ total: 0, downloaded: 0, not_downloaded: 0 })
const selectedIds = ref(new Set())
const downloadingIds = ref(new Set())
const batchDownloading = ref(false)
const downloadProgress = reactive({ current: 0, total: 0 })

const isAllSelected = computed(() =>
  articles.value.length > 0 && articles.value.every(a => selectedIds.value.has(a.id))
)

const isPartialSelected = computed(() =>
  !isAllSelected.value && articles.value.some(a => selectedIds.value.has(a.id))
)

onMounted(() => {
  loadStats()
  loadArticles()
  // 监听下载进度
  window.__onDownloadProgress = onDownloadProgress
})

onUnmounted(() => {
  window.__onDownloadProgress = null
})

function onDownloadProgress(articleId, title, current, total) {
  downloadProgress.current = current
  downloadProgress.total = total
  downloadingIds.value.add(articleId)
}

async function loadStats() {
  const r = await appStore.callApi('get_download_stats')
  if (r && r.success) {
    stats.value = { total: r.total, downloaded: r.downloaded, not_downloaded: r.not_downloaded }
  }
}

async function loadArticles() {
  loading.value = true
  const filterVal = filter.value === 'downloaded' ? true : filter.value === 'not_downloaded' ? false : null
  const r = await appStore.callApi('get_download_articles', page.value, pageSize, filterVal)
  loading.value = false
  if (r && r.success) {
    articles.value = r.articles
    total.value = r.total
    totalPages.value = Math.ceil(r.total / pageSize) || 1
  }
}

function setFilter(f) {
  filter.value = f
  page.value = 1
  selectedIds.value = new Set()
  loadArticles()
}

function goPage(p) {
  page.value = p
  selectedIds.value = new Set()
  loadArticles()
}

function toggleSelect(id) {
  const s = new Set(selectedIds.value)
  if (s.has(id)) {
    s.delete(id)
  } else {
    s.add(id)
  }
  selectedIds.value = s
}

function toggleSelectAll() {
  if (isAllSelected.value) {
    selectedIds.value = new Set()
  } else {
    selectedIds.value = new Set(articles.value.map(a => a.id))
  }
}

async function batchDownload() {
  const ids = Array.from(selectedIds.value)
  if (ids.length === 0) return

  batchDownloading.value = true
  downloadProgress.current = 0
  downloadProgress.total = ids.length
  downloadingIds.value = new Set(ids)

  const r = await appStore.callApi('batch_download_articles', ids)

  batchDownloading.value = false
  downloadingIds.value = new Set()

  if (r && r.success) {
    toast.success(r.message)
    selectedIds.value = new Set()
    loadArticles()
    loadStats()
  } else if (r) {
    toast.error(r.message)
  }
}

async function downloadAll() {
  // 选择当前过滤条件下的所有未下载文章
  // 先获取所有未下载的文章 ID
  const r = await appStore.callApi('get_download_articles', 1, 999, false)
  if (r && r.success && r.articles.length > 0) {
    const ids = r.articles.map(a => a.id)
    selectedIds.value = new Set(ids)
    // 触发批量下载
    batchDownloading.value = true
    downloadProgress.current = 0
    downloadProgress.total = ids.length
    downloadingIds.value = new Set(ids)

    const result = await appStore.callApi('batch_download_articles', ids)

    batchDownloading.value = false
    downloadingIds.value = new Set()

    if (result && result.success) {
      toast.success(result.message)
      selectedIds.value = new Set()
      loadArticles()
      loadStats()
    } else if (result) {
      toast.error(result.message)
    }
  } else {
    toast.info('没有需要下载的文章')
  }
}

function typeLabel(t) {
  return { video: '视频', image: '图文', text: '文字' }[t] || t
}
</script>

<style scoped>
.downloads-page {
  max-width: 100%;
}

/* Stats row */
.stats-row {
  display: flex;
  gap: var(--space-4);
  margin-bottom: var(--space-6);
}

.stat-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: var(--space-4) var(--space-5);
}

.stat-card .stat-val {
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--text-primary);
}

.stat-card .stat-val.downloaded { color: var(--success); }
.stat-card .stat-val.pending { color: var(--warning); }

.stat-card .stat-lbl {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

/* Toolbar */
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-4);
  border-bottom: 1px solid var(--surface-border);
}

.filter-tabs {
  display: flex;
  gap: var(--space-1);
}

.filter-tab {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
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

.filter-tab:hover { color: var(--text-primary); }
.filter-tab.active {
  color: var(--text-primary);
  border-bottom-color: var(--accent-primary);
}

.toolbar-right {
  display: flex;
  gap: var(--space-2);
  padding-bottom: var(--space-3);
}

/* Empty */
.empty-state { padding: var(--space-10) 0; }
.empty-text { font-size: var(--text-sm); color: var(--text-muted); }

/* Select all */
.select-all-row {
  padding: var(--space-2) var(--space-2);
  border-bottom: 1px solid var(--surface-border);
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  cursor: pointer;
}

.select-all-text {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

/* Checkbox */
.checkbox {
  width: 18px;
  height: 18px;
  border: 1.5px solid var(--surface-border);
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all var(--transition-fast);
  color: #fff;
  cursor: pointer;
}

.checkbox.checked {
  background: var(--accent-primary);
  border-color: var(--accent-primary);
}

.checkbox.indeterminate {
  background: var(--accent-primary);
  border-color: var(--accent-primary);
}

/* Article list */
.article-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.article-row {
  display: flex;
  align-items: center;
  padding: var(--space-3) var(--space-2);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background var(--transition-fast);
  gap: var(--space-3);
}

.article-row:hover { background: var(--bg-hover); }
.article-row.selected { background: rgba(99, 102, 241, 0.06); }

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

.article-right {
  flex-shrink: 0;
}

/* Download status */
.download-status {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-xs);
  padding: 2px 10px;
  border-radius: 9999px;
  font-weight: 500;
  white-space: nowrap;
}

.download-status.done {
  background: rgba(34,197,94,0.12);
  color: var(--success);
}

.download-status.not-downloaded {
  background: rgba(234,179,8,0.12);
  color: var(--warning);
}

.download-status.downloading {
  background: rgba(99,102,241,0.12);
  color: var(--accent-primary);
}

/* Spinner */
.spinner-sm {
  display: inline-block;
  width: 12px; height: 12px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: currentColor;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
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

.page-info-text {
  font-size: var(--text-xs);
  color: var(--text-muted);
}
</style>
