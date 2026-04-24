<script setup lang="ts">
/**
 * PdfPreview - PDF preview with toolbar for dialogs
 * Features: zoom, page navigation, rotate, pan (drag to scroll)
 */
import { ref, shallowRef, watch, onUnmounted, nextTick, computed } from 'vue'
import { Loader2, FileText, AlertCircle, ZoomIn, ZoomOut, RotateCw, RotateCcw, ChevronLeft, ChevronRight, Maximize2, Move, Expand } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import * as pdfjsLib from 'pdfjs-dist'
import pdfjsWorker from 'pdfjs-dist/build/pdf.worker.min.mjs?url'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()

// Set worker
pdfjsLib.GlobalWorkerOptions.workerSrc = pdfjsWorker

const props = defineProps<{
  src?: string | null
}>()

// State
const containerRef = ref<HTMLDivElement | null>(null)
const canvasRef = ref<HTMLCanvasElement | null>(null)
const pdfDoc = shallowRef<pdfjsLib.PDFDocumentProxy | null>(null)
const currentPage = ref(1)
const totalPages = ref(0)
const scale = ref(1)
const rotation = ref(0)
const isLoading = ref(false)
const error = ref<string | null>(null)

// Pan state
const isPanning = ref(false)
const panStart = ref({ x: 0, y: 0 })
const panOffset = ref({ x: 0, y: 0 })

// Computed
const displayScale = computed(() => Math.round(scale.value * 100))

// Scale presets for fit
async function fitToWidth() {
  if (!pdfDoc.value || !containerRef.value) return
  
  const page = await pdfDoc.value.getPage(currentPage.value)
  const viewport = page.getViewport({ scale: 1, rotation: rotation.value })
  
  const containerWidth = containerRef.value.clientWidth - 20 // padding
  scale.value = containerWidth / viewport.width
  scale.value = Math.max(0.5, Math.min(2, scale.value))
  
  await renderPage()
}

// Fit to container on initial load
async function fitToContainer() {
  if (!pdfDoc.value) {
    return false
  }
  
  // Wait for container if needed
  if (!containerRef.value) {
    await nextTick()
  }
  
  if (!containerRef.value) {
    return false
  }
  
  const page = await pdfDoc.value.getPage(currentPage.value)
  const viewport = page.getViewport({ scale: 1, rotation: rotation.value })
  
  const containerWidth = containerRef.value.clientWidth - 20
  const containerHeight = containerRef.value.clientHeight - 20
  
  const scaleX = containerWidth / viewport.width
  const scaleY = containerHeight / viewport.height
  
  scale.value = Math.min(scaleX, scaleY, 1.5)
  scale.value = Math.max(0.25, scale.value)
  
  await renderPage()
  return true
}

// Watch for src changes
watch(() => props.src, async (newSrc) => {
  if (newSrc) {
    isLoading.value = true
    error.value = null
    pdfDoc.value = null
    totalPages.value = 0
    currentPage.value = 1
    scale.value = 1
    rotation.value = 0
    panOffset.value = { x: 0, y: 0 }
    await loadPdf(newSrc)
  } else {
    pdfDoc.value = null
    isLoading.value = false
  }
}, { immediate: true })

async function loadPdf(url: string) {
  try {
    // Fetch the PDF first to check response
    const response = await fetch(url)
    
    if (!response.ok) {
      throw new Error(`Server returned ${response.status}: ${response.statusText}`)
    }
    
    const contentType = response.headers.get('Content-Type') || ''
    
    // Check if response is actually a PDF
    if (!contentType.includes('application/pdf') && !contentType.includes('application/octet-stream')) {
      const text = await response.text()
      console.error('[PdfPreview] Non-PDF response:', text.substring(0, 500))
      throw new Error(`Expected PDF but got ${contentType}`)
    }
    
    const arrayBuffer = await response.arrayBuffer()
    
    // Check if PDF is empty or too small
    if (arrayBuffer.byteLength < 100) {
      throw new Error('PDF file is empty or corrupted')
    }
    
    // Check PDF header
    const header = new Uint8Array(arrayBuffer, 0, 5)
    const headerStr = String.fromCharCode(...header)
    if (!headerStr.startsWith('%PDF-')) {
      console.error('[PdfPreview] Invalid PDF header:', headerStr)
      throw new Error('Invalid PDF structure - file may be encrypted or corrupted')
    }
    
    const loadingTask = pdfjsLib.getDocument({ data: arrayBuffer })
    pdfDoc.value = await loadingTask.promise
    totalPages.value = pdfDoc.value.numPages
    currentPage.value = 1
    
    // Fit to container after loading
    await nextTick()
    
    // Wait for container to be available
    let attempts = 0
    while (!containerRef.value && attempts < 10) {
      await nextTick()
      attempts++
    }
    
    if (containerRef.value) {
      await fitToContainer()
    } else {
      // Fallback: just render at default scale
      scale.value = 1
      await renderPage()
    }
  } catch (e: any) {
    console.error('[PdfPreview] Failed to load PDF:', e)
    error.value = e.message || 'Failed to load PDF preview'
  } finally {
    isLoading.value = false
  }
}
async function renderPage() {
  if (!pdfDoc.value) {
    return
  }
  
  if (!canvasRef.value) {
    await nextTick()
  }
  
  if (!canvasRef.value) {
    return
  }
  
  const page = await pdfDoc.value.getPage(currentPage.value)
  const viewport = page.getViewport({ scale: scale.value, rotation: rotation.value })
  
  const canvas = canvasRef.value
  const context = canvas.getContext('2d')
  if (!context) return
  
  canvas.height = viewport.height
  canvas.width = viewport.width
  
  // Reset pan when rendering
  panOffset.value = { x: 0, y: 0 }
  
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  await page.render({ canvasContext: context, viewport } as any).promise
}

// Zoom controls
async function zoomIn() {
  if (scale.value < 4) {
    scale.value = Math.min(4, scale.value + 0.25)
    await renderPage()
  }
}

async function zoomOut() {
  if (scale.value > 0.25) {
    scale.value = Math.max(0.25, scale.value - 0.25)
    await renderPage()
  }
}

async function resetZoom() {
  scale.value = 1
  await fitToContainer()
}

// Rotation controls
async function rotateClockwise() {
  rotation.value = (rotation.value + 90) % 360
  await renderPage()
}

async function rotateCounterClockwise() {
  rotation.value = (rotation.value - 90 + 360) % 360
  await renderPage()
}

// Page navigation
async function prevPage() {
  if (currentPage.value > 1) {
    currentPage.value--
    await fitToContainer()
  }
}

async function nextPage() {
  if (currentPage.value < totalPages.value) {
    currentPage.value++
    await fitToContainer()
  }
}

// Pan handlers (drag to scroll)
function handleMouseDown(e: MouseEvent) {
  if (scale.value > 1 && containerRef.value) {
    isPanning.value = true
    panStart.value = { x: e.clientX, y: e.clientY }
    containerRef.value.style.cursor = 'grabbing'
  }
}

function handleMouseMove(e: MouseEvent) {
  if (!isPanning.value || !containerRef.value) return
  
  const dx = e.clientX - panStart.value.x
  const dy = e.clientY - panStart.value.y
  
  containerRef.value.scrollLeft -= dx
  containerRef.value.scrollTop -= dy
  
  panStart.value = { x: e.clientX, y: e.clientY }
}

function handleMouseUp() {
  if (isPanning.value && containerRef.value) {
    isPanning.value = false
    containerRef.value.style.cursor = scale.value > 1 ? 'grab' : 'default'
  }
}

// Scroll-wheel zoom
async function handleWheel(e: WheelEvent) {
  if (!pdfDoc.value) return

  // Only zoom when Ctrl is held (like browser zoom)
  if (!e.ctrlKey && !e.metaKey) return
  e.preventDefault()

  const delta = e.deltaY > 0 ? -0.1 : 0.1
  const newScale = Math.max(0.25, Math.min(4, scale.value + delta))

  if (newScale !== scale.value) {
    scale.value = newScale
    await renderPage()
  }
}

onUnmounted(() => {
  if (pdfDoc.value) {
    pdfDoc.value.destroy()
  }
})
</script>

<template>
  <div class="pdf-preview-wrapper">
    <!-- Toolbar -->
    <div v-if="pdfDoc && !error" class="pdf-toolbar">
      <!-- Zoom -->
      <div class="toolbar-group">
        <Button variant="ghost" size="icon" @click="zoomOut" :disabled="scale <= 0.25" :title="t('viewer.zoom_out')">
          <ZoomOut class="h-4 w-4" />
        </Button>
        <span class="zoom-label">{{ displayScale }}%</span>
        <Button variant="ghost" size="icon" @click="zoomIn" :disabled="scale >= 4" :title="t('viewer.zoom_in')">
          <ZoomIn class="h-4 w-4" />
        </Button>
        <Button variant="ghost" size="icon" @click="resetZoom" :title="t('viewer.fit_to_page')">
          <Maximize2 class="h-4 w-4" />
        </Button>
        <Button variant="ghost" size="icon" @click="fitToWidth" :title="t('viewer.fit_to_width')">
          <Expand class="h-4 w-4" />
        </Button>
      </div>
      
      <!-- Page navigation -->
      <div class="toolbar-group" v-if="totalPages > 1">
        <Button variant="ghost" size="icon" @click="prevPage" :disabled="currentPage <= 1" :title="t('viewer.prev_page')">
          <ChevronLeft class="h-4 w-4" />
        </Button>
        <span class="page-indicator">{{ currentPage }} / {{ totalPages }}</span>
        <Button variant="ghost" size="icon" @click="nextPage" :disabled="currentPage >= totalPages" :title="t('viewer.next_page')">
          <ChevronRight class="h-4 w-4" />
        </Button>
      </div>
      
      <!-- Rotation -->
      <div class="toolbar-group">
        <Button variant="ghost" size="icon" @click="rotateCounterClockwise" :title="t('viewer.rotate_left')">
          <RotateCcw class="h-4 w-4" />
        </Button>
        <Button variant="ghost" size="icon" @click="rotateClockwise" :title="t('viewer.rotate_right')">
          <RotateCw class="h-4 w-4" />
        </Button>
      </div>
      
      <!-- Pan/zoom hint -->
      <div v-if="scale > 1" class="toolbar-group pan-hint">
        <Move class="h-4 w-4" />
        <span class="hint-text">{{ t('viewer.drag_to_pan') }}</span>
      </div>
      <div v-else class="toolbar-group pan-hint">
        <span class="hint-text dim">{{ t('viewer.ctrl_scroll_zoom') }}</span>
      </div>
    </div>
    
    <!-- PDF Container -->
    <div 
      ref="containerRef"
      class="pdf-preview-container"
      :class="{ 'can-pan': scale > 1 }"
      @mousedown="handleMouseDown"
      @mousemove="handleMouseMove"
      @mouseup="handleMouseUp"
      @mouseleave="handleMouseUp"
      @wheel="handleWheel"
    >
      <!-- Loading state -->
      <Transition name="fade">
        <div v-if="isLoading && props.src" class="loading-overlay">
          <div class="loading-content">
            <Loader2 class="h-8 w-8 animate-spin text-primary" />
            <p class="mt-2 text-sm text-muted-foreground">Loading preview...</p>
          </div>
        </div>
      </Transition>

      <!-- Error state -->
      <div v-if="error" class="error-state">
        <AlertCircle class="h-8 w-8 text-destructive" />
        <p class="text-sm text-muted-foreground">{{ error }}</p>
      </div>

      <!-- Empty state -->
      <div v-if="!props.src && !error" class="empty-state">
        <FileText class="h-12 w-12 text-muted-foreground" />
        <p class="mt-2 text-sm text-muted-foreground">No file selected</p>
      </div>

      <!-- PDF Canvas -->
      <div v-if="props.src && !error" class="canvas-wrapper">
        <canvas ref="canvasRef" class="pdf-canvas" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.pdf-preview-wrapper {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  min-height: 300px;
}

.pdf-toolbar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  background-color: hsl(var(--card));
  border-bottom: 1px solid hsl(var(--border));
  border-radius: 0.5rem 0.5rem 0 0;
  flex-shrink: 0;
  flex-wrap: wrap;
}

.toolbar-group {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.toolbar-group + .toolbar-group {
  margin-left: 0.75rem;
  padding-left: 0.75rem;
  border-left: 1px solid hsl(var(--border));
}

.zoom-label {
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground));
  min-width: 3rem;
  text-align: center;
}

.page-indicator {
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground));
  min-width: 4rem;
  text-align: center;
}

.pan-hint {
  margin-left: auto;
  color: hsl(var(--muted-foreground));
  font-size: 0.625rem;
}

    .pan-hint .hint-text.dim {
  opacity: 0.6;
}


.pdf-preview-container {
  flex: 1;
  min-height: 0;
  border: 1px solid hsl(var(--border));
  border-top: none;
  border-radius: 0 0 0.5rem 0.5rem;
  overflow: auto;
  background-color: hsl(var(--muted) / 0.3);
  position: relative;
}

.pdf-preview-container.can-pan {
  cursor: grab;
}

.pdf-preview-container.can-pan:active {
  cursor: grabbing;
}

.canvas-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0.5rem;
  min-width: 100%;
  min-height: 100%;
}

.pdf-canvas {
  display: block;
  max-width: none;
  transition: opacity 0.15s ease;
}

.loading-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: hsl(var(--background) / 0.9);
  z-index: 10;
}

.loading-content {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  color: hsl(var(--muted-foreground));
  position: absolute;
  inset: 0;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: hsl(var(--muted-foreground));
  position: absolute;
  inset: 0;
}

/* Transition */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>