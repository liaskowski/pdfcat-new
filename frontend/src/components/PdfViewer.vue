<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import {
  ZoomIn, ZoomOut, RotateCw, Download, ChevronLeft, Maximize,
  Sidebar, Grid, FileText, Search, Loader2
} from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
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

const containerRef = ref<HTMLElement | null>(null)
const pdfUrl = computed(() => {
  if (props.src) return props.src
  if (props.documentId) {
    const token = localStorage.getItem('token')
    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
    return `${API_BASE_URL}/documents/${props.documentId}/download?token=${token}`
  }
  return ''
})

const scale = ref(100)
const rotation = ref(0)
const isSidebarOpen = ref(true)
const isLoading = ref(true)
const isError = ref(false)

// Reset loading state when URL changes
watch(pdfUrl, () => {
  isLoading.value = true
  isError.value = false
})

function handleZoomIn() { scale.value = Math.min(scale.value + 10, 300) }
function handleZoomOut() { scale.value = Math.max(scale.value - 10, 50) }
function handleRotate() { rotation.value = (rotation.value + 90) % 360 }

function handleDownload() {
  if (!pdfUrl.value) return
  const link = document.createElement('a')
  link.href = pdfUrl.value
  link.download = ''
  link.click()
}

function handleFullscreen() {
  if (containerRef.value) {
    if (document.fullscreenElement) document.exitFullscreen()
    else containerRef.value.requestFullscreen()
  }
}

function toggleSidebar() { isSidebarOpen.value = !isSidebarOpen.value }
function handleLoad() { 
  console.log('[PdfViewer] Content loaded')
  isLoading.value = false
  isError.value = false 
}
function handleError() { 
  console.error('[PdfViewer] Content error')
  isLoading.value = false
  isError.value = true 
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === '+' || e.key === '=') handleZoomIn()
  else if (e.key === '-') handleZoomOut()
  else if (e.key === 'r' || e.key === 'R') handleRotate()
  else if (e.key === 'Escape') emit('close')
}

onMounted(() => window.addEventListener('keydown', handleKeydown))
onUnmounted(() => window.removeEventListener('keydown', handleKeydown))
</script>

<template>
  <div ref="containerRef" class="pdf-viewer">
    <!-- Toolbar -->
    <div class="toolbar">
      <div class="toolbar-left">
        <Button variant="ghost" size="sm" @click="emit('close')" :title="t('common.back')">
          <ChevronLeft class="h-4 w-4 mr-2" /> {{ t('common.back') }}
        </Button>
        <div class="divider"></div>
        <Button variant="ghost" size="sm" @click="toggleSidebar" :class="{ 'active': isSidebarOpen }" :title="t('viewer.toggle_sidebar')">
          <Sidebar class="h-4 w-4" />
        </Button>
      </div>
      
      <div class="toolbar-center">
        <div class="zoom-controls">
          <Button variant="ghost" size="sm" @click="handleZoomOut"><ZoomOut class="h-4 w-4" /></Button>
          <span class="zoom-level">{{ scale }}%</span>
          <Button variant="ghost" size="sm" @click="handleZoomIn"><ZoomIn class="h-4 w-4" /></Button>
        </div>
      </div>
      
      <div class="toolbar-right">
        <Button variant="ghost" size="sm" @click="handleRotate" :title="t('viewer.rotate')">
          <RotateCw class="h-4 w-4" />
        </Button>
        <Button variant="ghost" size="sm" @click="handleDownload" :title="t('common.download')">
          <Download class="h-4 w-4" />
        </Button>
        <Button variant="ghost" size="sm" @click="handleFullscreen" :title="t('viewer.fullscreen')">
          <Maximize class="h-4 w-4" />
        </Button>
      </div>
    </div>
    
    <div class="viewer-body">
      <!-- Sidebar (Thumbnails placeholder) -->
      <div class="viewer-sidebar" :class="{ 'closed': !isSidebarOpen }">
        <div class="sidebar-header">
          <button class="sidebar-tab active"><Grid class="h-4 w-4" /></button>
          <button class="sidebar-tab"><FileText class="h-4 w-4" /></button>
          <button class="sidebar-tab"><Search class="h-4 w-4" /></button>
        </div>
        <div class="sidebar-content">
          <div class="thumbnails-placeholder">
            <p>Thumbnails not available in basic viewer</p>
            <div v-for="i in 5" :key="i" class="thumbnail-skeleton"></div>
          </div>
        </div>
      </div>

      <!-- Main Content -->
      <div class="pdf-content">
        <!-- Loader Overlay -->
        <div v-if="isLoading" class="loading-overlay">
          <div class="loading-box">
            <Loader2 class="h-10 w-10 animate-spin text-primary" />
            <p class="mt-4 text-lg font-medium text-foreground">{{ t('viewer.loading_document') }}</p>
          </div>
        </div>

        <div v-if="isError" class="state-msg error">
          {{ t('viewer.failed') }}
          <Button variant="outline" size="sm" @click="() => { isError = false; isLoading = true }">{{ t('common.retry') }}</Button>
        </div>
        
        <div class="iframe-wrapper" :style="{ transform: `scale(${scale / 100}) rotate(${rotation}deg)` }">
          <iframe
            v-if="pdfUrl"
            :src="pdfUrl"
            class="pdf-frame"
            @load="handleLoad"
            @error="handleError"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.pdf-viewer { display: flex; flex-direction: column; height: 100%; background-color: hsl(var(--background)); overflow: hidden; }

.toolbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0.5rem 1rem; border-bottom: 1px solid hsl(var(--border));
  background-color: hsl(var(--background)); z-index: 10;
}

.toolbar-left, .toolbar-right, .toolbar-center { display: flex; align-items: center; gap: 0.5rem; }
.divider { width: 1px; height: 24px; background-color: hsl(var(--border)); margin: 0 0.5rem; }
.zoom-controls { display: flex; align-items: center; border: 1px solid hsl(var(--border)); border-radius: 0.375rem; }
.zoom-level { font-size: 0.75rem; font-weight: 500; min-width: 45px; text-align: center; }

.viewer-body { flex: 1; display: flex; overflow: hidden; position: relative; }

.viewer-sidebar {
  width: 250px; border-right: 1px solid hsl(var(--border)); background-color: hsl(var(--background));
  display: flex; flex-direction: column; transition: width 0.3s ease;
}
.viewer-sidebar.closed { width: 0; overflow: hidden; border-right: none; }

.sidebar-header { display: flex; border-bottom: 1px solid hsl(var(--border)); }
.sidebar-tab { flex: 1; padding: 0.75rem; background: none; border: none; cursor: pointer; color: hsl(var(--muted-foreground)); border-bottom: 2px solid transparent; }
.sidebar-tab.active { color: hsl(var(--primary)); border-bottom-color: hsl(var(--primary)); }
.sidebar-tab:hover { background-color: hsl(var(--accent)); }

.sidebar-content { flex: 1; padding: 1rem; overflow-y: auto; }
.thumbnails-placeholder { display: flex; flex-direction: column; gap: 1rem; align-items: center; text-align: center; color: hsl(var(--muted-foreground)); font-size: 0.875rem; }
.thumbnail-skeleton { width: 100%; aspect-ratio: 3/4; background-color: hsl(var(--muted)); border-radius: 0.25rem; }

/* Loading Overlay Styles */
.loading-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: hsl(var(--background));
  z-index: 50; /* Ensure it's above everything in pdf-content */
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

.pdf-content { flex: 1; background-color: hsl(var(--muted)); display: flex; align-items: center; justify-content: center; overflow: auto; position: relative; }
.iframe-wrapper { width: 100%; height: 100%; transition: transform 0.2s ease; display: flex; align-items: center; justify-content: center; }
.pdf-frame { width: 100%; height: 100%; border: none; background-color: white; }

.state-msg { color: hsl(var(--muted-foreground)); display: flex; flex-direction: column; gap: 0.5rem; align-items: center; }
.state-msg.error { color: hsl(var(--destructive)); }
</style>
