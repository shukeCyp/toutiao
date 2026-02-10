import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  const browserConnected = ref(false)
  const isLoading = ref(false)
  const logs = ref([])

  function addLog(message, type = 'info') {
    logs.value.unshift({
      id: Date.now(),
      message,
      type,
      time: new Date().toLocaleTimeString(),
    })
    // Keep last 100 logs
    if (logs.value.length > 100) {
      logs.value = logs.value.slice(0, 100)
    }
  }

  function setBrowserConnected(connected) {
    browserConnected.value = connected
  }

  function setLoading(loading) {
    isLoading.value = loading
  }

  // pywebview API 就绪 Promise（全局只创建一次）
  let _apiReady = null
  function waitForApi() {
    if (_apiReady) return _apiReady
    _apiReady = new Promise((resolve) => {
      // 已经可用
      if (window.pywebview && window.pywebview.api) {
        resolve(true)
        return
      }
      // 监听 pywebview 官方 ready 事件
      window.addEventListener('pywebviewready', () => {
        resolve(true)
      })
      // 兜底：轮询检测
      const start = Date.now()
      const check = setInterval(() => {
        if (window.pywebview && window.pywebview.api) {
          clearInterval(check)
          resolve(true)
        } else if (Date.now() - start > 15000) {
          clearInterval(check)
          resolve(false)
        }
      }, 200)
    })
    return _apiReady
  }

  // Call Python backend via pywebview
  async function callApi(method, ...args) {
    const ready = await waitForApi()
    if (ready && window.pywebview && window.pywebview.api) {
      try {
        isLoading.value = true
        const result = await window.pywebview.api[method](...args)
        return result
      } catch (e) {
        addLog(`API Error: ${e.message}`, 'error')
        throw e
      } finally {
        isLoading.value = false
      }
    } else {
      addLog('pywebview API not available', 'warning')
      return null
    }
  }

  return {
    browserConnected,
    isLoading,
    logs,
    addLog,
    setBrowserConnected,
    setLoading,
    callApi,
  }
})
