import { ref } from 'vue'

const toasts = ref([])
let idCounter = 0

/**
 * 全局 Toast 通知
 * 用法:
 *   const { toast } = useToast()
 *   toast.success('操作成功')
 *   toast.error('操作失败')
 *   toast.warning('请注意')
 *   toast.info('提示信息')
 */
export function useToast() {
  function add(message, type = 'info', duration = 3000) {
    const id = ++idCounter
    toasts.value.push({ id, message, type })
    if (duration > 0) {
      setTimeout(() => remove(id), duration)
    }
  }

  function remove(id) {
    toasts.value = toasts.value.filter(t => t.id !== id)
  }

  const toast = {
    success: (msg, duration) => add(msg, 'success', duration),
    error: (msg, duration) => add(msg, 'error', duration),
    warning: (msg, duration) => add(msg, 'warning', duration),
    info: (msg, duration) => add(msg, 'info', duration),
  }

  return { toasts, toast, remove }
}
