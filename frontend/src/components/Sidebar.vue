<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <div class="logo">
        <div class="logo-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
            stroke-linecap="round" stroke-linejoin="round">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
          </svg>
        </div>
        <span class="logo-text">Toutiao Tool</span>
      </div>
    </div>

    <nav class="sidebar-nav">
      <div class="nav-section">
        <span class="nav-section-label">General</span>
        <router-link to="/" class="nav-item" :class="{ active: $route.path === '/' }">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
            stroke-linecap="round" stroke-linejoin="round">
            <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
            <polyline points="9 22 9 12 15 12 15 22" />
          </svg>
          <span>首页</span>
        </router-link>
        <router-link to="/accounts" class="nav-item" :class="{ active: $route.path === '/accounts' }">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
            stroke-linecap="round" stroke-linejoin="round">
            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
            <circle cx="9" cy="7" r="4" />
            <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
            <path d="M16 3.13a4 4 0 0 1 0 7.75" />
          </svg>
          <span>对标账号</span>
        </router-link>
        <router-link to="/articles" class="nav-item" :class="{ active: $route.path === '/articles' }">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
            stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
          </svg>
          <span>文章</span>
        </router-link>
        <router-link to="/downloads" class="nav-item" :class="{ active: $route.path === '/downloads' }">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
            stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="7 10 12 15 17 10" />
            <line x1="12" y1="15" x2="12" y2="3" />
          </svg>
          <span>文章下载</span>
        </router-link>
      </div>

      <div class="nav-section">
        <span class="nav-section-label">Develop</span>
        <router-link to="/debug" class="nav-item" :class="{ active: $route.path === '/debug' }">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
            stroke-linecap="round" stroke-linejoin="round">
            <path d="M20 16V7a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v9m16 0H4m16 0l1.28 2.55a1 1 0 0 1-.9 1.45H3.62a1 1 0 0 1-.9-1.45L4 16" />
          </svg>
          <span>调试</span>
        </router-link>
      </div>

      <div class="nav-section">
        <span class="nav-section-label">System</span>
        <router-link to="/settings" class="nav-item" :class="{ active: $route.path === '/settings' }">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
            stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="3" />
            <path
              d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
          </svg>
          <span>设置</span>
        </router-link>
      </div>
    </nav>

    <div class="sidebar-footer">
      <div class="status-indicator">
        <span class="status-dot" :class="statusClass"></span>
        <span class="status-text">{{ statusText }}</span>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { useAppStore } from '../stores/app'

const appStore = useAppStore()

const statusClass = computed(() => ({
  'status-connected': appStore.browserConnected,
  'status-disconnected': !appStore.browserConnected,
}))

const statusText = computed(() =>
  appStore.browserConnected ? 'Browser Connected' : 'Browser Idle'
)
</script>

<style scoped>
.sidebar {
  width: var(--sidebar-width);
  min-width: var(--sidebar-width);
  height: 100vh;
  background: var(--bg-secondary);
  border-right: 1px solid var(--surface-border);
  display: flex;
  flex-direction: column;
  user-select: none;
}

.sidebar-header {
  padding: var(--space-5) var(--space-4);
  border-bottom: 1px solid var(--surface-border);
}

.logo {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.logo-icon {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
  border-radius: var(--radius-md);
  color: #fff;
}

.logo-text {
  font-size: var(--text-lg);
  font-weight: 600;
  letter-spacing: -0.02em;
  color: var(--text-primary);
}

.sidebar-nav {
  flex: 1;
  padding: var(--space-3) var(--space-2);
  overflow-y: auto;
}

.nav-section {
  margin-bottom: var(--space-5);
}

.nav-section-label {
  display: block;
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-xs);
  font-weight: 500;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  margin: 1px 0;
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  font-size: var(--text-sm);
  font-weight: 450;
  transition: all var(--transition-fast);
  text-decoration: none;
}

.nav-item:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.nav-item.active {
  background: var(--bg-active);
  color: var(--text-primary);
}

.sidebar-footer {
  padding: var(--space-4);
  border-top: 1px solid var(--surface-border);
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-connected {
  background: var(--success);
  box-shadow: 0 0 6px rgba(34, 197, 94, 0.5);
}

.status-disconnected {
  background: var(--text-muted);
}

.status-text {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}
</style>
