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
      </div>

      <div class="actions">
        <button class="btn btn-primary" @click="saveSettings">保存设置</button>
        <button class="btn" @click="resetSettings">恢复默认</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, onMounted } from 'vue'
import { useAppStore } from '../stores/app'
import { useToast } from '../composables/useToast'

const appStore = useAppStore()
const { toast } = useToast()

const defaultSettings = {
  headless: false,
  timeout: 30000,
  collectTimeout: 60,
  rewriteWorkers: 10,
  apiBase: '',
  apiKey: '',
  model: '',
  articleSavePath: '',
  rewriteSavePath: '',
}

const settings = reactive({ ...defaultSettings })

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
