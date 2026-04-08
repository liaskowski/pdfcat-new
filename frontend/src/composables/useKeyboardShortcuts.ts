import { onMounted, onUnmounted, ref } from 'vue'

interface KeyboardShortcutHandlers {
  onCopy?: () => void
  onPaste?: () => void
  onCut?: () => void
  onDelete?: () => void
  onRename?: () => void
  onSelectAll?: () => void
  onSearch?: () => void
  onUpload?: () => void
  onClose?: () => void
}

export function useKeyboardShortcuts(handlers: KeyboardShortcutHandlers) {
  const isActive = ref(true)

  function handleKeydown(e: KeyboardEvent) {
    if (!isActive.value) return

    // Don't trigger shortcuts when user is typing in input/textarea
    const target = e.target as HTMLElement
    if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
      // Allow Escape to work even in inputs
      if (e.key === 'Escape') {
        handlers.onClose?.()
      }
      return
    }

    const isCtrl = e.ctrlKey || e.metaKey

    if (isCtrl && e.key === 'c') {
      e.preventDefault()
      handlers.onCopy?.()
    } else if (isCtrl && e.key === 'v') {
      e.preventDefault()
      handlers.onPaste?.()
    } else if (isCtrl && e.key === 'x') {
      e.preventDefault()
      handlers.onCut?.()
    } else if (e.key === 'Delete') {
      e.preventDefault()
      handlers.onDelete?.()
    } else if (e.key === 'F2') {
      e.preventDefault()
      handlers.onRename?.()
    } else if (isCtrl && e.key === 'a') {
      e.preventDefault()
      handlers.onSelectAll?.()
    } else if (isCtrl && e.key === 'f') {
      e.preventDefault()
      handlers.onSearch?.()
    } else if (isCtrl && e.key === 'u') {
      e.preventDefault()
      handlers.onUpload?.()
    } else if (e.key === 'Escape') {
      handlers.onClose?.()
    }
  }

  onMounted(() => {
    window.addEventListener('keydown', handleKeydown)
  })

  onUnmounted(() => {
    window.removeEventListener('keydown', handleKeydown)
  })

  return { isActive }
}
