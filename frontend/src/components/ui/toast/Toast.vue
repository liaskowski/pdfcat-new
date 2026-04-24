<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { X, CheckCircle, AlertCircle, Info, AlertTriangle } from 'lucide-vue-next'

export interface ToastProps {
  id: string
  title?: string
  description?: string
  variant?: 'default' | 'success' | 'error' | 'warning' | 'info'
  duration?: number
}

const props = withDefaults(defineProps<ToastProps>(), {
  variant: 'default',
  duration: 5000,
})

const emit = defineEmits<{
  dismiss: [id: string]
}>()

const isVisible = ref(false)
const progress = ref(100)
let progressInterval: ReturnType<typeof setInterval>
let dismissTimeout: ReturnType<typeof setTimeout>

const icons = {
  default: Info,
  success: CheckCircle,
  error: AlertCircle,
  warning: AlertTriangle,
  info: Info,
}

const icon = computed(() => icons[props.variant])

const variantClasses = computed(() => {
  const map = {
    default: 'bg-background border-border text-foreground',
    success: 'bg-green-50 border-green-200 text-green-900 dark:bg-green-950 dark:border-green-800 dark:text-green-100',
    error: 'bg-red-50 border-red-200 text-red-900 dark:bg-red-950 dark:border-red-800 dark:text-red-100',
    warning: 'bg-yellow-50 border-yellow-200 text-yellow-900 dark:bg-yellow-950 dark:border-yellow-800 dark:text-yellow-100',
    info: 'bg-blue-50 border-blue-200 text-blue-900 dark:bg-blue-950 dark:border-blue-800 dark:text-blue-100',
  }
  return map[props.variant]
})

const iconClasses = computed(() => {
  const map = {
    default: 'text-foreground',
    success: 'text-green-600 dark:text-green-400',
    error: 'text-red-600 dark:text-red-400',
    warning: 'text-yellow-600 dark:text-yellow-400',
    info: 'text-blue-600 dark:text-blue-400',
  }
  return map[props.variant]
})

function startDismissTimer() {
  const step = 100 / (props.duration / 100)
  progressInterval = setInterval(() => {
    progress.value -= step
    if (progress.value <= 0) {
      clearInterval(progressInterval)
    }
  }, 100)

  dismissTimeout = setTimeout(() => {
    dismiss()
  }, props.duration)
}

function dismiss() {
  clearInterval(progressInterval)
  clearTimeout(dismissTimeout)
  isVisible.value = false
  setTimeout(() => {
    emit('dismiss', props.id)
  }, 300)
}

function pauseTimer() {
  clearInterval(progressInterval)
  clearTimeout(dismissTimeout)
}

function resumeTimer() {
  if (progress.value > 0) {
    const remaining = (progress.value / 100) * props.duration
    dismissTimeout = setTimeout(() => {
      dismiss()
    }, remaining)
    const step = 100 / (remaining / 100)
    progressInterval = setInterval(() => {
      progress.value -= step
      if (progress.value <= 0) {
        clearInterval(progressInterval)
      }
    }, 100)
  }
}

onMounted(() => {
  requestAnimationFrame(() => {
    isVisible.value = true
    startDismissTimer()
  })
})
</script>

<template>
  <div
    class="toast-container"
    :class="[isVisible ? 'toast-visible' : 'toast-hidden', variantClasses]"
    @mouseenter="pauseTimer"
    @mouseleave="resumeTimer"
  >
    <div class="toast-content">
      <component :is="icon" class="toast-icon" :class="iconClasses" />
      <div class="toast-text">
        <p v-if="title" class="toast-title">{{ title }}</p>
        <p v-if="description" class="toast-description">{{ description }}</p>
      </div>
      <button class="toast-close" @click="dismiss">
        <X class="h-4 w-4" />
      </button>
    </div>
    <div class="toast-progress-bar" :style="{ width: progress + '%' }"></div>
  </div>
</template>

<style scoped>
.toast-container {
  pointer-events: auto;
  border-radius: 0.5rem;
  border: 1px solid;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  overflow: hidden;
  min-width: 300px;
  max-width: 420px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.toast-hidden {
  opacity: 0;
  transform: translateX(100%);
}

.toast-visible {
  opacity: 1;
  transform: translateX(0);
}

.toast-content {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 0.875rem 1rem;
}

.toast-icon {
  width: 1.25rem;
  height: 1.25rem;
  flex-shrink: 0;
  margin-top: 0.125rem;
}

.toast-text {
  flex: 1;
  min-width: 0;
}

.toast-title {
  font-size: 0.875rem;
  font-weight: 600;
  line-height: 1.25;
  margin: 0;
}

.toast-description {
  font-size: 0.8125rem;
  line-height: 1.4;
  margin: 0.25rem 0 0;
  opacity: 0.9;
}

.toast-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 0.25rem;
  border: none;
  background: transparent;
  cursor: pointer;
  color: currentColor;
  opacity: 0.5;
  transition: opacity 0.2s, background-color 0.2s;
  flex-shrink: 0;
}

.toast-close:hover {
  opacity: 1;
  background-color: rgba(0, 0, 0, 0.05);
}

.dark .toast-close:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.toast-progress-bar {
  height: 3px;
  background-color: currentColor;
  opacity: 0.3;
  transition: width 0.1s linear;
}
</style>
