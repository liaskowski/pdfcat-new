<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import {
  ChevronLeft,
  ChevronRight,
  Shield,
  ShieldAlert,
  Loader2,
  ZoomIn,
  ZoomOut,
  RotateCw
} from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { VuePDFjs } from '@tuttarealstep/vue-pdf.js'
import '@tuttarealstep/vue-pdf.js/dist/style.css'
import { useI18n } from '@/composables/useI18n'

// Import localization files using the exported subpath
import enUS_FTL from '@tuttarealstep/vue-pdf.js/l10n/en-US/viewer.ftl?raw'
import pl_FTL from '@tuttarealstep/vue-pdf.js/l10n/pl/viewer.ftl?raw'

const { t } = useI18n()

const props = defineProps<{
  documentId?: number
  src?: string
  visible?: boolean
}>()

const emit = defineEmits<{
  close: []
}>()

const { locale: appLocale } = useI18n()

// State
const isLoading = ref(true)
const renderError = ref<string | null>(null)
const currentPage = ref(1)
const totalPagesCount = ref(1)
const scale = ref(1.0)
const rotation = ref(0)

// Security info
const securityInfo = ref({
  isPasswordProtected: false,
  hasJavaScript: false,
  hasActions: false,
  hasEmbeddedFiles: false
})

// Compute PDF URL
const pdfUrl = computed(() => {
  if (props.src) return props.src
  if (props.documentId) {
    const token = localStorage.getItem('token')
    return `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/documents/${props.documentId}/download?token=${token}`
  }
  return ''
})

// Security check
async function securityCheck() {
  if (!pdfUrl.value) return
  
  try {
    const response = await fetch(pdfUrl.value)
    const data = await response.arrayBuffer()
    const textDecoder = new TextDecoder('latin1')
    const pdfHeader = textDecoder.decode(data.slice(0, 1024))

    if (pdfHeader.includes('/JavaScript') || pdfHeader.includes('/JS')) {
      securityInfo.value.hasJavaScript = true
    }
    if (pdfHeader.includes('/EmbeddedFiles')) {
      securityInfo.value.hasEmbeddedFiles = true
    }
    if (pdfHeader.includes('/Launch')) {
      securityInfo.value.hasActions = true
    }
  } catch (e) {
    console.error('Security check failed:', e)
  }
}

// Viewer Options
const viewerOptions = ref({
  isEvalSupported: false,
  isRemoteResourcesAllowed: false,
  locale: {
    code: 'en-US',
    ftl: enUS_FTL
  },
  toolbar: {
    options: {
      openFileButton: false,
      printButton: false,
      downloadButton: false,
      viewBookmarkButton: false,
      editorFreeTextButton: false,
      editorInkButton: false,
    }
  }
})

// Sync locale with app
function syncLocale() {
  if (appLocale.value === 'pl') {
    viewerOptions.value.locale = {
      code: 'pl',
      ftl: pl_FTL
    }
  } else {
    viewerOptions.value.locale = {
      code: 'en-US',
      ftl: enUS_FTL
    }
  }
}

function onPdfLoaded() {
  isLoading.value = false
  hideToolbarButtons()
}

function hideToolbarButtons() {
  setTimeout(() => {
    // Try multiple possible toolbar selectors
    const containers = document.querySelectorAll('.pdf-app .toolbar, .pdf-app #toolbarViewer, .pdf-app .secondaryToolbar')
    containers.forEach(container => {
      const buttons = container.querySelectorAll('button, .toolbarButton, [role="button"]')
      buttons.forEach(btn => {
        const el = btn as HTMLElement
        const ariaLabel = (el.getAttribute('aria-label') || '').toLowerCase()
        const title = (el.getAttribute('title') || '').toLowerCase()
        const dataId = (el.getAttribute('data-l10n-id') || '').toLowerCase()
        const id = (el.id || '').toLowerCase()

        const isTarget =
          id.includes('open') || id.includes('print') ||
          dataId.includes('open') || dataId.includes('print') ||
          ariaLabel.includes('open file') || ariaLabel.includes('print') ||
          title.includes('open') || title.includes('print')

        if (isTarget) {
          el.style.display = 'none'
        }
      })
    })
  }, 300)
}

function onPdfError(error: any) {
  console.error('[PDF Viewer] PDF Error:', error)
  renderError.value = error.message || 'Failed to load PDF'
  isLoading.value = false
}

function zoomIn() { scale.value = Math.min(scale.value + 0.2, 3.0) }
function zoomOut() { scale.value = Math.max(scale.value - 0.2, 0.5) }
function handleReload() { isLoading.value = true; setTimeout(() => { isLoading.value = false }, 2000) }
function handleRotate() { rotation.value = (rotation.value + 90) % 360 }
function prevPage() { if (currentPage.value > 1) currentPage.value-- }
function nextPage() { if (currentPage.value < totalPagesCount.value) currentPage.value++ }

function handleKeydown(e: KeyboardEvent) {
  // Block Ctrl+S (Save) and Ctrl+P (Print)
  if ((e.ctrlKey || e.metaKey) && (e.key === 's' || e.key === 'p')) {
    e.preventDefault()
    console.warn('[Security] Print/Save blocked')
    return false
  }

  if (e.key === 'Escape') {
    emit('close')
  }
}

// Watch for visibility
watch(() => props.visible, (newVal) => {
  if (newVal) {
    syncLocale()
    securityCheck()
    isLoading.value = true
    renderError.value = null
  }
})

// Watch for locale changes
watch(appLocale, () => {
  syncLocale()
})

onMounted(() => {
  syncLocale()
  if (props.visible) {
    securityCheck()
  }
  window.addEventListener('keydown', handleKeydown)

  // Watch for PDF.js toolbar buttons appearing and hide Open/Print
  const observer = new MutationObserver(() => {
    hideToolbarButtons()
  })
  // Wait for PDF.js to render, then start observing
  setTimeout(() => {
    hideToolbarButtons()
    const target = document.querySelector('.pdf-app')
    if (target) {
      observer.observe(target, { childList: true, subtree: true })
    }
  }, 1000)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<template>
  <div class="pdf-viewer-container">
    <!-- Header/Back button overlay -->
    <div class="viewer-header">
      <Button variant="ghost" size="sm" @click="emit('close')" title="Back">
        <ChevronLeft class="h-4 w-4 mr-2" /> Back
      </Button>
      <div v-if="isLoading" class="loading-indicator">
        <Loader2 class="h-4 w-4 animate-spin mr-2" />
        <span>Loading...</span>
      </div>
    </div>

    <!-- Security Warning Banner -->
    <div v-if="securityInfo.hasJavaScript || securityInfo.hasEmbeddedFiles || securityInfo.hasActions" class="security-banner">
      <ShieldAlert class="h-4 w-4" />
      <span>
        <strong>Security Notice:</strong>
        This PDF contains potentially unsafe elements (
        <span v-if="securityInfo.hasJavaScript">JavaScript</span>
        <span v-if="securityInfo.hasEmbeddedFiles">, Embedded Files</span>
        <span v-if="securityInfo.hasActions">, External Actions</span>
        ). These have been blocked for your protection.
      </span>
      <Shield class="h-4 w-4 ml-auto" />
    </div>

    <!-- Main Viewer -->
    <div class="viewer-wrapper" @contextmenu.prevent>
      <!-- Centered Loading State -->
      <div v-if="isLoading && !renderError" class="loading-overlay">
        <div class="loading-box">
          <Loader2 class="h-10 w-10 animate-spin text-primary" />
          <p class="mt-4 text-lg font-medium">Przygotowywanie bezpiecznego podglądu...</p>
          <p class="text-sm text-muted-foreground">To może chwilę potrwać dla dużych plików</p>
        </div>
      </div>

      <div v-if="renderError" class="error-state">
        <ShieldAlert class="h-12 w-12" />
        <h3>Failed to load PDF</h3>
        <p>{{ renderError }}</p>
        <Button variant="outline" @click="isLoading = true; renderError = null">Retry</Button>
      </div>

      <VuePDFjs
        v-if="pdfUrl && !renderError"
        :source="pdfUrl"
        :options="viewerOptions"
        @pdf-app:loaded="onPdfLoaded"
        @pdf-app:error="onPdfError"
        class="pdf-app"
        :style="{ transform: `rotate(${rotation}deg)`, transition: 'transform 0.2s ease' }"
      />

      <!-- Custom Toolbar -->
      <div v-if="!renderError" class="custom-toolbar">
        <button @click="zoomOut" title="Zoom Out"><ZoomOut class="h-4 w-4" /></button>
        <span class="zoom-label">{{ Math.round(scale * 100) }}%</span>
        <button @click="zoomIn" title="Zoom In"><ZoomIn class="h-4 w-4" /></button>
        <div class="toolbar-divider"></div>
        <button @click="handleRotate" :title="t('viewer.rotate') || 'Rotate'">
          <RotateCw class="h-4 w-4" :style="{ transform: `rotate(${rotation}deg)` }" />
        </button>
        <div class="toolbar-divider"></div>
        <button @click="prevPage" :disabled="currentPage <= 1" :title="t('viewer.prev_page') || 'Previous Page'">
          <ChevronLeft class="h-4 w-4" />
        </button>
        <span class="page-info">{{ currentPage }} / {{ totalPagesCount }}</span>
        <button @click="nextPage" :disabled="currentPage >= totalPagesCount" :title="t('viewer.next_page') || 'Next Page'">
          <ChevronRight class="h-4 w-4" />
        </button>
        <div class="toolbar-divider"></div>
        <button @click="handleReload" title="Reload">
          <RotateCw class="h-4 w-4" />
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.pdf-viewer-container {
  display: flex;
  flex-direction: column;
  height: 100dvh;
  height: -webkit-fill-available;
  height: 100vh;
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
}

.loading-indicator {
  display: flex;
  align-items: center;
  margin-left: 1rem;
  font-size: 0.875rem;
  color: hsl(var(--muted-foreground));
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
}

.viewer-wrapper {
  flex: 1;
  position: relative;
  overflow: hidden;
}

.pdf-app {
  width: 100%;
  height: 100%;
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

/* Ensure the underlying viewer takes full height */
:deep(.pdf-app) {
  height: 100% !important;
}

/* Hide Open and Print buttons in VuePDFjs/PDF.js toolbar */
/* PDF.js uses these IDs for toolbar buttons */
:deep(.pdf-app #toolbarViewer #openFile),
:deep(.pdf-app #toolbarViewer #print),
:deep(.pdf-app .toolbarButton[aria-label*="Open"]),
:deep(.pdf-app .toolbarButton[aria-label*="Print"]),
:deep(.pdf-app .toolbarButton[data-l10n-id*="open"]),
:deep(.pdf-app .toolbarButton[data-l10n-id*="print"]) {
  display: none !important;
}

/* Security: try to hide scrollbars or UI elements that could be used for bypass */
:deep(.pdf-app .toolbar) {
  user-select: none;
}

/* Fix for potential z-index issues with tooltips */
:deep(.pdf-app .tooltip) {
  z-index: 10000;
}

/* Custom Toolbar */
.custom-toolbar {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.75rem;
  background-color: hsl(var(--background));
  border-top: 1px solid hsl(var(--border));
}

.custom-toolbar button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  padding: 0;
  border: 1px solid hsl(var(--border));
  background: transparent;
  color: hsl(var(--foreground));
  border-radius: 0.25rem;
  cursor: pointer;
}

.custom-toolbar button:hover {
  background-color: hsl(var(--accent));
}

.zoom-label {
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground));
  min-width: 3rem;
  text-align: center;
}

.toolbar-divider {
  width: 1px;
  height: 1.25rem;
  background-color: hsl(var(--border));
}

.page-info {
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground));
  min-width: 4rem;
  text-align: center;
}

.custom-toolbar button:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}
</style>
