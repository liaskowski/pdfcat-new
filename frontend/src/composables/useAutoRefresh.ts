import { ref, onMounted, onUnmounted, watch } from 'vue'

interface UseAutoRefreshOptions {
  intervalMs?: number
  onRefresh: () => void | Promise<void>
  paused?: boolean
}

export function useAutoRefresh(options: UseAutoRefreshOptions) {
  const intervalMs = options.intervalMs ?? 30000
  const isPaused = ref(options.paused ?? false)
  const lastRefresh = ref<Date | null>(null)
  let timer: ReturnType<typeof setInterval> | null = null

  async function refresh() {
    if (isPaused.value) return
    try {
      await options.onRefresh()
      lastRefresh.value = new Date()
    } catch (e) {
      console.error('Auto-refresh failed:', e)
    }
  }

  function start() {
    stop()
    timer = setInterval(refresh, intervalMs)
  }

  function stop() {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  }

  function pause() {
    isPaused.value = true
    stop()
  }

  function resume() {
    isPaused.value = false
    start()
  }

  function secondsSinceLastRefresh(): number {
    if (!lastRefresh.value) return -1
    return Math.floor((Date.now() - lastRefresh.value.getTime()) / 1000)
  }

  // Watch for pause state changes
  watch(isPaused, (paused) => {
    if (paused) stop()
    else start()
  })

  onMounted(() => {
    if (!isPaused.value) start()
  })

  onUnmounted(() => {
    stop()
  })

  return {
    isPaused,
    lastRefresh,
    refresh,
    pause,
    resume,
    secondsSinceLastRefresh,
  }
}
