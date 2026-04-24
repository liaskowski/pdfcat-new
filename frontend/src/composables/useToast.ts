import { ref } from 'vue'
import type { ToastProps } from '@/components/ui/toast/Toast.vue'

export interface ToastOptions {
  title?: string
  description?: string
  variant?: ToastProps['variant']
  duration?: number
}

const toasts = ref<ToastProps[]>([])
let idCounter = 0

export function useToast() {
  function add(options: ToastOptions) {
    const id = `toast-${++idCounter}-${Date.now()}`
    const toast: ToastProps = {
      id,
      title: options.title,
      description: options.description,
      variant: options.variant ?? 'default',
      duration: options.duration ?? 5000,
    }
    toasts.value.push(toast)
    return id
  }

  function dismiss(id: string) {
    const index = toasts.value.findIndex(t => t.id === id)
    if (index !== -1) {
      toasts.value.splice(index, 1)
    }
  }

  function dismissAll() {
    toasts.value = []
  }

  // Convenience methods
  function success(description: string, title = 'Success') {
    return add({ title, description, variant: 'success' })
  }

  function error(description: string, title = 'Error') {
    return add({ title, description, variant: 'error', duration: 8000 })
  }

  function warning(description: string, title = 'Warning') {
    return add({ title, description, variant: 'warning', duration: 6000 })
  }

  function info(description: string, title = 'Info') {
    return add({ title, description, variant: 'info' })
  }

  return {
    toasts,
    add,
    dismiss,
    dismissAll,
    success,
    error,
    warning,
    info,
  }
}
