<template>
  <div class="settings-page">
    <div class="page-header">
      <h1>设置</h1>
      <p>配置应用程序参数，设置会自动保存到本地</p>
    </div>

    <div class="settings-sections">
      <div class="card settings-section">
        <h3 class="section-title">浏览器设置</h3>
        <div class="setting-item">
          <div class="setting-info">
            <label class="setting-label">无头模式(隐藏浏览器)</label>
            <span class="setting-desc">开启后所有浏览器操作在后台运行，不显示窗口</span>
          </div>
          <label class="toggle">
            <input type="checkbox" v-model="settings.headless" />
            <span class="toggle-slider"></span>
          </label>
        </div>
        <div class="setting-item setting-item-vertical">
          <div class="setting-info">
            <label class="setting-label">代理池</label>
            <span class="setting-desc">每行一个代理，格式：IP:端口 用户名 密码（用户名密码可选）<br>示例：183.146.16.147:29011 user123 pass456</span>
          </div>
          <div class="proxy-list" v-if="proxyList.length">
            <div class="proxy-row" v-for="(item, idx) in proxyList" :key="idx">
              <span class="proxy-addr">{{ item.addr }}</span>
              <span class="proxy-user" v-if="item.user">{{ item.user }}</span>
              <button class="proxy-remove" @click="removeProxy(idx)" title="删除">
                <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M4 4L12 12M12 4L4 12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                </svg>
              </button>
            </div>
          </div>
          <div class="proxy-empty" v-else>暂无代理，请在下方添加</div>
          <div class="proxy-add">
            <input
              class="input proxy-add-input"
              v-model="newProxy"
              placeholder="183.146.16.147:29011 用户名 密码"
              @keyup.enter="addProxy"
            />
            <button class="btn btn-primary btn-sm" @click="addProxy">添加</button>
          </div>
        </div>
      </div>

      <div class="card settings-section">
        <h3 class="section-title">模型设置</h3>
        <div class="setting-item">
          <div class="setting-info">
            <label class="setting-label">API 地址</label>
            <span class="setting-desc">模型服务的接口地址</span>
          </div>
          <input class="input setting-input" v-model="settings.apiBase" placeholder="https://api.openai.com/v1" />
        </div>
        <div class="setting-item">
          <div class="setting-info">
            <label class="setting-label">API 秘钥</label>
            <span class="setting-desc">用于鉴权的 API Key</span>
          </div>
          <input class="input setting-input" type="password" v-model="settings.apiKey" placeholder="sk-..." />
        </div>
        <div class="setting-item">
          <div class="setting-info">
            <label class="setting-label">模型</label>
            <span class="setting-desc">使用的模型名称</span>
          </div>
          <input class="input setting-input" v-model="settings.model" placeholder="gpt-4o" />
        </div>
      </div>

      <div class="card settings-section">
        <h3 class="section-title">存储设置</h3>
        <div class="setting-item">
          <div class="setting-info">
            <label class="setting-label">文章保存路径</label>
            <span class="setting-desc">下载的原始文章 docx 保存目录</span>
          </div>
          <div class="path-input-group">
            <input class="input setting-input" v-model="settings.articleSavePath" placeholder="/Users/xxx/articles" />
            <button class="btn btn-folder" @click="selectFolder('articleSavePath')" title="选择文件夹">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M1.5 3C1.5 2.17157 2.17157 1.5 3 1.5H5.58579C5.98361 1.5 6.36514 1.65804 6.64645 1.93934L7.85355 3.14645C8.13486 3.42776 8.51639 3.58579 8.91421 3.58579H13C13.8284 3.58579 14.5 4.25736 14.5 5.08579V12C14.5 12.8284 13.8284 13.5 13 13.5H3C2.17157 13.5 1.5 12.8284 1.5 12V3Z" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/>
              </svg>
            </button>
          </div>
        </div>
        <div class="setting-item">
          <div class="setting-info">
            <label class="setting-label">改写文章保存路径</label>
            <span class="setting-desc">改写后的文章保存目录</span>
          </div>
          <div class="path-input-group">
            <input class="input setting-input" v-model="settings.rewriteSavePath" placeholder="/Users/xxx/rewrite" />
            <button class="btn btn-folder" @click="selectFolder('rewriteSavePath')" title="选择文件夹">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M1.5 3C1.5 2.17157 2.17157 1.5 3 1.5H5.58579C5.98361 1.5 6.36514 1.65804 6.64645 1.93934L7.85355 3.14645C8.13486 3.42776 8.51639 3.58579 8.91421 3.58579H13C13.8284 3.58579 14.5 4.25736 14.5 5.08579V12C14.5 12.8284 13.8284 13.5 13 13.5H3C2.17157 13.5 1.5 12.8284 1.5 12V3Z" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/>
              </svg>
            </button>
          </div>
        </div>
      </div>

      <div class="card settings-section">
        <h3 class="section-title">通用设置</h3>
        <div class="setting-item">
          <div class="setting-info">
            <label class="setting-label">请求超时</label>
            <span class="setting-desc">页面加载超时时间（毫秒）</span>
          </div>
          <input class="input setting-input" type="number" v-model.number="settings.timeout" />
        </div>
        <div class="setting-item">
          <div class="setting-info">
            <label class="setting-label">采集超时</label>
            <span class="setting-desc">单个账号文章采集的超时时间（秒），默认 60 秒</span>
          </div>
          <input class="input setting-input" type="number" v-model.number="settings.collectTimeout" />
        </div>
        <div class="setting-item">
          <div class="setting-info">
            <label class="setting-label">改写线程数</label>
            <span class="setting-desc">批量改写文章的并行线程数，默认 10</span>
          </div>
          <input class="input setting-input" type="number" v-model.number="settings.rewriteWorkers" />
        </div>
        <div class="setting-item">
          <div class="setting-info">
            <label class="setting-label">文字字数限制</label>
            <span class="setting-desc">改写文章的最大字数限制，默认 1000</span>
          </div>
          <input class="input setting-input" type="number" v-model.number="settings.maxWordCount" />
        </div>
      </div>

      <div class="actions">
        <button class="btn btn-primary" @click="saveSettings">保存设置</button>
        <button class="btn" @click="resetSettings">恢复默认</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, computed, ref, onMounted } from 'vue'
import { useAppStore } from '../stores/app'
import { useToast } from '../composables/useToast'

const appStore = useAppStore()
const { toast } = useToast()

const defaultSettings = {
  headless: false,
  timeout: 30000,
  collectTimeout: 60,
  rewriteWorkers: 10,
  maxWordCount: 1000,
  apiBase: '',
  apiKey: '',
  model: '',
  articleSavePath: '',
  rewriteSavePath: '',
  proxyPool: '',
}

const settings = reactive({ ...defaultSettings })
const newProxy = ref('')

const proxyList = computed(() => {
  if (!settings.proxyPool || !settings.proxyPool.trim()) return []
  return settings.proxyPool.trim().split('\n').filter(l => l.trim()).map(line => {
    const parts = line.trim().split(/\s+/)
    return { addr: parts[0] || '', user: parts[1] || '', raw: line.trim() }
  })
})

function addProxy() {
  const val = newProxy.value.trim()
  if (!val) return
  const parts = val.split(/\s+/)
  if (!parts[0] || !parts[0].includes(':')) {
    toast.error('格式不正确，请输入 IP:端口 用户名 密码')
    return
  }
  const current = settings.proxyPool ? settings.proxyPool.trim() : ''
  settings.proxyPool = current ? current + '\n' + val : val
  newProxy.value = ''
}

function removeProxy(idx) {
  const lines = settings.proxyPool.trim().split('\n').filter(l => l.trim())
  lines.splice(idx, 1)
  settings.proxyPool = lines.join('\n')
}

onMounted(async () => {
  const result = await appStore.callApi('get_settings')
  if (result && result.success && result.settings) {
    Object.assign(settings, result.settings)
  }
})

async function saveSettings() {
  const result = await appStore.callApi('save_settings', JSON.parse(JSON.stringify(settings)))
  if (result && result.success) {
    toast.success('设置已保存')
  } else if (result) {
    toast.error(result.message)
  }
}

async function selectFolder(field) {
  const result = await appStore.callApi('select_folder')
  if (result && result.success && result.path) {
    settings[field] = result.path
  }
}

function resetSettings() {
  Object.assign(settings, defaultSettings)
  toast.info('已恢复默认，点击保存生效')
}
</script>

<style scoped>
.settings-page {
  max-width: 720px;
}

.settings-sections {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.settings-section {
  display: flex;
  flex-direction: column;
  gap: 0;
  padding: 0;
}

.section-title {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--text-primary);
  padding: var(--space-4) var(--space-6);
  border-bottom: 1px solid var(--surface-border);
}

.setting-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4) var(--space-6);
  border-bottom: 1px solid var(--surface-border);
  gap: var(--space-4);
}

.setting-item:last-child {
  border-bottom: none;
}

.setting-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.setting-label {
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--text-primary);
}

.setting-desc {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.setting-input {
  max-width: 240px;
}

.setting-item-vertical {
  flex-direction: column;
  align-items: stretch;
}

.proxy-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.proxy-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  background: var(--surface-secondary);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-md);
}

.proxy-addr {
  font-family: 'SF Mono', 'Monaco', 'Menlo', 'Consolas', monospace;
  font-size: var(--text-xs);
  color: var(--text-primary);
  flex: 1;
  min-width: 0;
}

.proxy-user {
  font-size: var(--text-xs);
  color: var(--text-muted);
  flex-shrink: 0;
}

.proxy-remove {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  padding: 0;
  flex-shrink: 0;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  transition: all var(--transition-normal);
}

.proxy-remove:hover {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.1);
}

.proxy-empty {
  font-size: var(--text-xs);
  color: var(--text-muted);
  padding: var(--space-3) 0;
}

.proxy-add {
  display: flex;
  gap: var(--space-2);
  margin-top: var(--space-2);
}

.proxy-add-input {
  flex: 1;
  font-family: 'SF Mono', 'Monaco', 'Menlo', 'Consolas', monospace;
  font-size: var(--text-xs);
}

.btn-sm {
  padding: var(--space-1) var(--space-3);
  font-size: var(--text-xs);
  flex-shrink: 0;
}

.path-input-group {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.btn-folder {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  padding: 0;
  flex-shrink: 0;
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  background: var(--surface-secondary);
  border: 1px solid var(--surface-border);
  cursor: pointer;
  transition: all var(--transition-normal);
}

.btn-folder:hover {
  color: var(--text-primary);
  background: var(--surface-hover);
  border-color: var(--accent-primary);
}

/* Toggle Switch */
.toggle {
  position: relative;
  display: inline-block;
  width: 40px;
  height: 22px;
  flex-shrink: 0;
}

.toggle input {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--surface-border);
  border-radius: 11px;
  transition: all var(--transition-normal);
}

.toggle-slider::before {
  content: '';
  position: absolute;
  height: 16px;
  width: 16px;
  left: 3px;
  bottom: 3px;
  background: var(--text-primary);
  border-radius: 50%;
  transition: all var(--transition-normal);
}

.toggle input:checked + .toggle-slider {
  background: var(--accent-primary);
}

.toggle input:checked + .toggle-slider::before {
  transform: translateX(18px);
}

.actions {
  display: flex;
  gap: var(--space-3);
}
</style>
