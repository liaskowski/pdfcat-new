<script setup lang="ts">
/**
 * EmbedPdfViewer - Secure PDF viewer wrapper using @embedpdf/vue-pdf-viewer
 * 
 * Uses the full EmbedPDF viewer with native toolbar.
 * Includes security checks and token-based authentication.
 * 
 * Disabled features (via disabledCategories):
 * - print, document-print: Печать
 * - export, document-export: Скачать/экспорт
 * - document-open: Открыть файл
 * - document-protect: Security меню
 * - annotation: Все аннотации (иерархическая категория)
 * - redaction: Redact
 * - form: Формы
 * - stamp: Штампы
 * - signature: Подписи
 * - insert: Insert mode
 * - bookmark: Закладки
 * - attachment: Вложения
 * 
 * Available: zoom, page navigation, rotate, thumbnails, search
 */
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { ChevronLeft, Shield, ShieldAlert, Loader2 } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { PDFViewer, type PDFViewerConfig, type PluginRegistry } from '@embedpdf/vue-pdf-viewer'
import type { UIPlugin } from '@embedpdf/plugin-ui'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()

const props = defineProps<{
  documentId?: number
  src?: string
  visible?: boolean
}>()

const emit = defineEmits<{
  close: []
}>()

// State
const isLoading = ref(true)
const renderError = ref<string | null>(null)
const viewerKey = ref(0)

// Security info
const securityInfo = ref({
  hasJavaScript: false,
  hasActions: false,
  hasEmbeddedFiles: false
})

// Compute PDF URL with authentication
const pdfUrl = computed(() => {
  if (props.src) return props.src
  if (props.documentId) {
    const token = localStorage.getItem('token')
    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
    return `${API_BASE_URL}/documents/${props.documentId}/download?token=${token}`
  }
  return ''
})

// Theme configuration based on app theme
const themeConfig = computed(() => {
  const isDark = document.documentElement.classList.contains('dark')
  return {
    preference: isDark ? 'dark' as const : 'light' as const,
    light: {
      accent: { primary: '#3b82f6' }
    },
    dark: {
      accent: { primary: '#60a5fa' }
    }
  }
})

// Viewer configuration
// Disable: print, export, annotation, document-open, document-protect, redaction, form, stamp, signature, insert, bookmark, attachment
// Keep: zoom, page navigation, rotate (in Page Settings menu), thumbnails, search
const viewerConfig = computed<PDFViewerConfig>(() => ({
  src: pdfUrl.value,
  theme: themeConfig.value,
  // Disable unnecessary/dangerous features
  disabledCategories: [
    'print',              // Печать
    'document-print',     // Печать (document menu)
    'export',             // Экспорт
    'document-export',    // Экспорт (document menu)
    'document-open',      // Открыть файл
    'document-protect',   // Security меню
    'annotation',         // Все аннотации (иерархическая категория - отключает все sub-кategorii)
    'redaction',          // Redact
    'form',               // Формы
    'stamp',              // Штампы
    'signature',          // Подписи
    'insert',             // Insert mode (View/insert/Form/redact)
    'bookmark',           // Закладки
    'attachment',         // Вложения
    // НЕ отключаем 'page' - Page Settings содержит rotate
    // НЕ отключаем 'rotate' - нужно для кнопок вращения
  ],
  // Tab bar for multiple documents (disable for single doc)
  tabBar: 'never' as const
}))

// Security check - scan PDF for potentially dangerous content
async function securityCheck() {
  if (!pdfUrl.value) return
  
  try {
    const response = await fetch(pdfUrl.value)
    const data = await response.arrayBuffer()
    const textDecoder = new TextDecoder('latin1')
    // Check first 10KB for security markers
    const pdfHeader = textDecoder.decode(data.slice(0, 10240))
    
    securityInfo.value = {
      hasJavaScript: pdfHeader.includes('/JavaScript') || pdfHeader.includes('/JS'),
      hasActions: pdfHeader.includes('/Launch') || pdfHeader.includes('/Action'),
      hasEmbeddedFiles: pdfHeader.includes('/EmbeddedFiles')
    }
    
    if (securityInfo.value.hasJavaScript) {
      console.warn('[Security] PDF contains JavaScript - viewer will render safely')
    }
    if (securityInfo.value.hasActions) {
      console.warn('[Security] PDF contains potential external actions')
    }
    if (securityInfo.value.hasEmbeddedFiles) {
      console.warn('[Security] PDF contains embedded files')
    }
  } catch (e) {
    console.error('[Security] Security check failed:', e)
  }
}

// Handle viewer ready - customize UI
function onReady(registry: PluginRegistry) {
  isLoading.value = false
  console.log('[EmbedPdfViewer] Viewer ready')
  
  // Get UI plugin to customize toolbar
  const ui = registry.getPlugin<UIPlugin>('ui')?.provides()
  if (!ui) {
    console.warn('[EmbedPdfViewer] UI plugin not found')
    return
  }
  
  // Get current schema
  const schema = ui.getSchema()
  const mainToolbar = schema.toolbars['main-toolbar']
  
  if (!mainToolbar) {
    console.warn('[EmbedPdfViewer] Main toolbar not found')
    return
  }
  
  // Clone toolbar items
  const items = structuredClone(mainToolbar.items)
  
  // Find left-group (where document controls are on the left side)
  const leftGroup = items.find((item: { id?: string }) => item.id === 'left-group')
  
  if (leftGroup && 'items' in leftGroup) {
    // Add rotate buttons at the end of left-group (leftmost visible position)
    leftGroup.items.push(
      {
        type: 'divider',
        id: 'rotate-divider',
        orientation: 'vertical',
        categories: ['page', 'rotate']
      } as const,
      {
        type: 'command-button',
        id: 'rotate-counter-clockwise-btn',
        commandId: 'rotate:counter-clockwise',
        variant: 'icon',
        categories: ['page', 'rotate']
      } as const,
      {
        type: 'command-button',
        id: 'rotate-clockwise-btn',
        commandId: 'rotate:clockwise',
        variant: 'icon',
        categories: ['page', 'rotate']
      } as const
    )
    
    // Apply the changes
    ui.mergeSchema({
      toolbars: {
        'main-toolbar': {
          ...mainToolbar,
          items
        }
      }
    })
    
    console.log('[EmbedPdfViewer] Rotate buttons added to left-group (left side of toolbar)')
  } else {
    console.warn('[EmbedPdfViewer] left-group not found in toolbar')
  }
}

// Handle viewer init
function onInit() {
  console.log('[EmbedPdfViewer] Viewer initialized')
}

// Security: Block keyboard shortcuts for download/print
function handleKeydown(e: KeyboardEvent) {
  // Block Ctrl+S (Save) and Ctrl+P (Print)
  if ((e.ctrlKey || e.metaKey) && (e.key === 's' || e.key === 'p')) {
    e.preventDefault()
    console.warn('[Security] Print/Save shortcut blocked')
    return false
  }
  
  if (e.key === 'Escape') {
    emit('close')
  }
}

// Reset state when visibility changes
watch(() => props.visible, async (newVal) => {
  if (newVal) {
    isLoading.value = true
    renderError.value = null
    securityInfo.value = { hasJavaScript: false, hasActions: false, hasEmbeddedFiles: false }
    await securityCheck()
    // Increment key to force re-render
    viewerKey.value++
  }
})

// Watch for src changes
watch(pdfUrl, async () => {
  if (props.visible && pdfUrl.value) {
    isLoading.value = true
    renderError.value = null
    await securityCheck()
    viewerKey.value++
  }
})

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
  if (props.visible && pdfUrl.value) {
    securityCheck()
  }
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<template>
  <div class="pdf-viewer-container" @contextmenu.prevent>
    <!-- Header with back button -->
    <div class="viewer-header">
      <Button variant="ghost" size="sm" @click="emit('close')" :title="t('common.back')">
        <ChevronLeft class="h-4 w-4 mr-2" />
        {{ t('common.back') }}
      </Button>
      
      <div v-if="isLoading" class="loading-indicator">
        <Loader2 class="h-4 w-4 animate-spin mr-2" />
        <span>{{ t('viewer.loading') }}</span>
      </div>
      
      <!-- Security indicator -->
      <div class="security-badge" :class="{ 'has-issues': securityInfo.hasJavaScript || securityInfo.hasActions }">
        <template v-if="securityInfo.hasJavaScript || securityInfo.hasActions">
          <ShieldAlert class="h-4 w-4 text-yellow-500" />
        </template>
        <template v-else>
          <Shield class="h-4 w-4 text-green-500" />
        </template>
      </div>
    </div>

    <!-- Security Warning Banner -->
    <Transition name="slide-down">
      <div 
        v-if="securityInfo.hasJavaScript || securityInfo.hasEmbeddedFiles || securityInfo.hasActions" 
        class="security-banner"
      >
        <ShieldAlert class="h-4 w-4 flex-shrink-0" />
        <span>
          <strong>{{ t('viewer.security_notice') }}:</strong>
          {{ t('viewer.security_warning') }}
          <span v-if="securityInfo.hasJavaScript">JavaScript</span>
          <span v-if="securityInfo.hasEmbeddedFiles">{{ (securityInfo.hasJavaScript ? ', ' : '') + 'Embedded Files' }}</span>
          <span v-if="securityInfo.hasActions">{{ ((securityInfo.hasJavaScript || securityInfo.hasEmbeddedFiles) ? ', ' : '') + 'External Actions' }}</span>
          ).
        </span>
        <Shield class="h-4 w-4 ml-auto flex-shrink-0" />
      </div>
    </Transition>

    <!-- Main Viewer -->
    <div class="viewer-wrapper">
      <!-- Loading overlay -->
      <Transition name="fade">
        <div v-if="isLoading" class="loading-overlay">
          <div class="loading-box">
            <Loader2 class="h-10 w-10 animate-spin text-primary" />
            <p class="mt-4 text-lg font-medium text-foreground">
              {{ t('viewer.loading_document') }}
            </p>
            <p class="text-sm text-muted-foreground">
              {{ t('viewer.loading_hint') }}
            </p>
          </div>
        </div>
      </Transition>

      <!-- Error state -->
      <div v-if="renderError" class="error-state">
        <ShieldAlert class="h-12 w-12" />
        <h3>{{ t('viewer.failed') }}</h3>
        <p>{{ renderError }}</p>
        <Button variant="outline" @click="isLoading = true; renderError = null; viewerKey++">
          {{ t('common.retry') }}
        </Button>
      </div>

      <!-- EmbedPDF Viewer - rotate available in Page Settings menu -->
      <PDFViewer
        v-if="pdfUrl && !renderError"
        :key="viewerKey"
        :config="viewerConfig"
        :style="{ width: '100%', height: '100%' }"
        @init="onInit"
        @ready="onReady"
      />
    </div>
  </div>
</template>

<style scoped>
.pdf-viewer-container {
  display: flex;
  flex-direction: column;
  height: 100dvh;
  width: 100vw;
  background-color: hsl(var(--background));
  overflow: hidden;
  position: fixed;
  inset: 0;
  z-index: 9999;
}

.viewer-header {
  display: flex;
  align-items: center;
  padding: 0.5rem 1rem;
  border-bottom: 1px solid hsl(var(--border));
  background-color: hsl(var(--background));
  z-index: 10;
  height: 48px;
  flex-shrink: 0;
  gap: 0.5rem;
}

.loading-indicator {
  display: flex;
  align-items: center;
  margin-left: 1rem;
  font-size: 0.875rem;
  color: hsl(var(--muted-foreground));
}

.security-badge {
  margin-left: auto;
  display: flex;
  align-items: center;
}

.security-banner {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background-color: hsl(var(--destructive) / 0.1);
  border-bottom: 1px solid hsl(var(--destructive) / 0.2);
  color: hsl(var(--destructive));
  font-size: 0.875rem;
  z-index: 10;
  flex-shrink: 0;
}

.viewer-wrapper {
  flex: 1;
  position: relative;
  overflow: hidden;
}

.loading-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: hsl(var(--background));
  z-index: 30;
}

.loading-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 2rem;
  border-radius: 1rem;
  background-color: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);
}

.error-state {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  color: hsl(var(--muted-foreground));
  text-align: center;
  background-color: hsl(var(--muted));
  z-index: 20;
}

.error-state h3 {
  font-size: 1.125rem;
  font-weight: 600;
  color: hsl(var(--destructive));
  margin: 0;
}

/* Transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-down-enter-active,
.slide-down-leave-active {
  transition: all 0.3s ease;
}

.slide-down-enter-from,
.slide-down-leave-to {
  transform: translateY(-100%);
  opacity: 0;
}

/* Prevent context menu on viewer (security) */
:deep(.embedpdf-container) {
  user-select: none;
}
</style>