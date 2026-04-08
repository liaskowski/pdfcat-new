<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useDocumentStore, type Document } from '@/stores/documents'
import DocumentCard from './DocumentCard.vue'
import ContextMenu from './ui/ContextMenu.vue'
import MoveDialog from './MoveDialog.vue'
import { Upload, Grid3X3, List, Trash2, FolderInput, X } from 'lucide-vue-next'
import Shimmer from './ui/Shimmer.vue'
import { useI18n } from '@/composables/useI18n'
import { useKeyboardShortcuts } from '@/composables/useKeyboardShortcuts'

const props = defineProps<{
  viewMode: string
  folderId: number | null
  ownerId: number | null
  searchQuery?: string
}>()

const emit = defineEmits<{
  upload: []
  documentSelect: [doc: any]
  documentOpen: [doc: any]
  documentDelete: [doc: any]
}>()

const docStore = useDocumentStore()
const { t } = useI18n()

// Selection State
const selectedIds = ref<Set<number>>(new Set())
const lastSelectedId = ref<number | null>(null)

// Context Menu State
const showContextMenu = ref(false)
const contextMenuX = ref(0)
const contextMenuY = ref(0)
const contextTargetId = ref<number | null>(null)

// View State
const viewLayout = ref<'grid' | 'list'>('grid')
const sortBy = ref<'date' | 'name' | 'size'>('date')
const sortOrder = ref<'asc' | 'desc'>('desc')

const sortedDocuments = computed(() => {
  let docs = [...docStore.documents]
  
  if (props.folderId !== null) {
    docs = docs.filter(d => d.folder_id === props.folderId)
  }
  
  docs.sort((a, b) => {
    let comparison = 0
    switch (sortBy.value) {
      case 'name':
        comparison = a.title.localeCompare(b.title)
        break
      case 'date':
        comparison = new Date(a.upload_date).getTime() - new Date(b.upload_date).getTime()
        break
      case 'size':
        comparison = (a.file_size || 0) - (b.file_size || 0)
        break
    }
    return sortOrder.value === 'desc' ? -comparison : comparison
  })
  
  return docs
})

// --- Selection Logic ---

function toggleSelection(id: number, multi: boolean, range: boolean, isCheckbox = false) {
  if (isCheckbox) {
    // Checkbox click — ВСЕГДА toggle этого конкретного ID
    const newSet = new Set(selectedIds.value)
    if (newSet.has(id)) {
      newSet.delete(id)
    } else {
      newSet.add(id)
    }
    selectedIds.value = newSet
    // Обновляем превью
    if (selectedIds.value.size === 1) {
      const doc = docStore.documents.find(d => d.id === id)
      if (doc) emit('documentSelect', doc)
    } else {
      emit('documentSelect', null)
    }
    return
  }

  const newSet = new Set(multi ? selectedIds.value : [])

  if (range && lastSelectedId.value !== null) {
    const docs = sortedDocuments.value
    const idx1 = docs.findIndex(d => d.id === lastSelectedId.value)
    const idx2 = docs.findIndex(d => d.id === id)

    if (idx1 !== -1 && idx2 !== -1) {
      const start = Math.min(idx1, idx2)
      const end = Math.max(idx1, idx2)
      for (let i = start; i <= end; i++) {
        newSet.add(docs[i].id)
      }
    }
  } else {
    // Card click — select only this one
    if (newSet.has(id) && !multi) {
      newSet.clear()
    } else {
      newSet.add(id)
    }
  }

  selectedIds.value = newSet
  lastSelectedId.value = id

  // Emit single select for preview panel
  if (newSet.size === 1) {
    const doc = docStore.documents.find(d => d.id === id)
    if (doc) emit('documentSelect', doc)
  } else {
    emit('documentSelect', null)
  }
}

function handleCardClick(doc: Document, event: MouseEvent) {
  const target = event.target as HTMLElement
  const isCheckbox = target.closest('.selection-checkbox') || target.closest('.checkbox-indicator')

  if (isCheckbox) {
    // Клик по checkbox — toggle selection для конкретного документа
    toggleSelection(doc.id, event.ctrlKey || event.metaKey, event.shiftKey, true)
    return
  }

  // Клик по карточке — показываем превью, НЕ выделяем
  emit('documentSelect', doc)
}

function handleCheckboxClick(doc: any, event: MouseEvent) {
  // Checkbox click — toggle selection для конкретного документа
  toggleSelection(doc.id, event.ctrlKey || event.metaKey, event.shiftKey, true)
}

function selectAll() {
  if (selectedIds.value.size === sortedDocuments.value.length) {
    selectedIds.value.clear()
  } else {
    selectedIds.value = new Set(sortedDocuments.value.map(d => d.id))
  }
}

// --- Context Menu Logic ---

const showMoveDialog = ref(false)

function handleContextMenu(doc: Document, event: MouseEvent) {
  // If right-clicked item is not in selection, select it exclusively
  if (!selectedIds.value.has(doc.id)) {
    selectedIds.value = new Set([doc.id])
    emit('documentSelect', doc)
  }
  
  contextTargetId.value = doc.id
  contextMenuX.value = event.clientX
  contextMenuY.value = event.clientY
  showContextMenu.value = true
}

const contextMenuItems = computed(() => {
  const count = selectedIds.value.size
  const single = count === 1
  const targetDoc = docStore.documents.find(d => d.id === contextTargetId.value)

  return [
    {
      label: single ? t('common.open') : `${t('common.open')} ${count} ${t('common.documents')}`,
      action: () => {
        if (single && targetDoc) emit('documentOpen', targetDoc)
      },
      disabled: !single
    },
    {
      label: t('common.download'),
      action: () => {
        selectedIds.value.forEach(id => {
          const doc = docStore.documents.find(d => d.id === id)
          if (doc) emit('documentOpen', doc)
        })
      }
    },
    { label: '', separator: true },
    {
      label: t('common.move'),
      icon: FolderInput,
      action: () => {
        showMoveDialog.value = true
      }
    },
    { label: '', separator: true },
    {
      label: t('common.delete'),
      icon: Trash2,
      danger: true,
      action: () => handleBatchDelete()
    }
  ]
})

// --- Batch Actions ---

function handleBatchMove() {
  if (selectedIds.value.size === 0) return
  showMoveDialog.value = true
}

function handleMoveComplete() {
  docStore.fetchDocuments(props.viewMode, props.folderId, props.ownerId)
  selectedIds.value.clear()
}

async function handleBatchDelete() {
  const count = selectedIds.value.size
  if (!confirm(t('confirm.delete_documents').replace('{count}', count.toString()))) return

  try {
    const ids = Array.from(selectedIds.value)
    await Promise.all(ids.map(id => docStore.deleteDocument(id)))
    selectedIds.value.clear()
  } catch (e) {
    alert(t('confirm.delete_failed'))
  }
}

// --- Watchers ---

// Filter state for toolbar
const selectedCategoryId = ref<number | null>(null)
const selectedFileTypeId = ref<number | null>(null)

function handleFilterChange() {
  docStore.advancedFilters.categoryId = selectedCategoryId.value
  docStore.advancedFilters.fileTypeId = selectedFileTypeId.value
  docStore.searchWithFilters()
}

const currentFolderName = computed(() => {
  if (props.folderId === null) return ''
  const folder = docStore.folders.find(f => f.id === props.folderId)
  return folder?.name || ''
})

watch(() => props.folderId, () => {
  selectedIds.value.clear()
})

watch(() => props.viewMode, () => {
  docStore.fetchDocuments(props.viewMode)
  selectedIds.value.clear()
})

// --- Keyboard Shortcuts ---

// Simple clipboard state for copy/cut/paste
const clipboard = ref<{ ids: number[]; operation: 'copy' | 'cut' } | null>(null)
const renamingDocId = ref<number | null>(null)

async function handleCopy() {
  if (selectedIds.value.size === 0) return
  clipboard.value = { ids: Array.from(selectedIds.value), operation: 'copy' }
}

async function handleCut() {
  if (selectedIds.value.size === 0) return
  clipboard.value = { ids: Array.from(selectedIds.value), operation: 'cut' }
}

async function handlePaste() {
  if (!clipboard.value) return
  const targetFolderId = props.folderId

  for (const id of clipboard.value.ids) {
    try {
      await docStore.duplicateDocument(id, targetFolderId ?? undefined)
    } catch (e) {
      console.error('Failed to paste document:', e)
    }
  }

  // If it was a cut operation, remove originals
  if (clipboard.value.operation === 'cut') {
    for (const id of clipboard.value.ids) {
      try {
        await docStore.deleteDocument(id)
      } catch (e) {
        console.error('Failed to delete cut document:', e)
      }
    }
  }

  clipboard.value = null
  docStore.fetchDocuments(props.viewMode, props.folderId, props.ownerId)
  selectedIds.value.clear()
}

function handleRename() {
  if (selectedIds.value.size === 1) {
    const id = Array.from(selectedIds.value)[0]
    renamingDocId.value = id
  }
}

async function handleRenameSaved(doc: any, newTitle: string) {
  try {
    await docStore.updateDocument(doc.id, { title: newTitle })
  } catch (e) {
    console.error('Failed to rename document:', e)
  } finally {
    renamingDocId.value = null
  }
}

function handleRenameCanceled() {
  renamingDocId.value = null
}

useKeyboardShortcuts({
  onCopy: handleCopy,
  onCut: handleCut,
  onPaste: handlePaste,
  onRename: handleRename,
  onDelete: handleBatchDelete,
  onSelectAll: selectAll,
  onSearch: () => {
    const input = document.querySelector('.search-input') as HTMLInputElement
    input?.focus()
  },
  onUpload: () => emit('upload'),
  onClose: () => {
    selectedIds.value.clear()
    showContextMenu.value = false
  }
})

onMounted(() => {
  docStore.fetchDocuments(props.viewMode)
})
</script>

<template>
  <div class="file-grid-container">
    <!-- Toolbar -->
    <div class="toolbar">
      <div class="toolbar-left">
        <h2 class="toolbar-title">
          {{ currentFolderName || (viewMode === 'my' ? t('nav.my_documents') : viewMode === 'shared' ? t('nav.shared') : t('nav.community')) }}
        </h2>
        <span class="document-count">{{ sortedDocuments.length }} {{ t('common.documents') }}</span>
      </div>
      
      <div class="toolbar-right">
        <div class="toolbar-filters">
          <select v-model="selectedCategoryId" class="filter-select" @change="handleFilterChange">
            <option :value="null">{{ t('filters.all_categories') }}</option>
            <option v-for="cat in docStore.categories" :key="cat.id" :value="cat.id">
              {{ cat.name }}
            </option>
          </select>
          <select v-model="selectedFileTypeId" class="filter-select" @change="handleFilterChange">
            <option :value="null">{{ t('filters.all_types') }}</option>
            <option v-for="type in docStore.fileTypes" :key="type.id" :value="type.id">
              {{ type.name }}
            </option>
          </select>
        </div>

        <div class="view-controls">
          <button 
            class="view-btn"
            :class="{ active: viewLayout === 'grid' }"
            @click="viewLayout = 'grid'"
            :title="t('viewer.toggle_sidebar')"
          >
            <Grid3X3 class="h-4 w-4" />
          </button>
          <button 
            class="view-btn"
            :class="{ active: viewLayout === 'list' }"
            @click="viewLayout = 'list'"
            :title="t('common.info')"
          >
            <List class="h-4 w-4" />
          </button>
        </div>
        
        <button class="upload-btn" @click="emit('upload')">
          <Upload class="h-4 w-4" />
          <span>{{ t('common.upload') }}</span>
        </button>
      </div>
    </div>

    <!-- Batch Actions Bar -->
    <div v-if="selectedIds.size > 0" class="batch-actions-bar">
      <div class="batch-left">
        <span class="selection-count">{{ selectedIds.size }} {{ t('common.selected') }}</span>
        <button class="batch-action" @click="selectAll">
          <span class="batch-icon">☑</span> {{ t('common.select_all') }}
        </button>
      </div>
      <div class="batch-right">
        <button class="batch-action" @click="handleBatchMove">
          <FolderInput class="h-4 w-4" />
          <span>{{ t('common.move') }}</span>
        </button>
        <button class="batch-action danger" @click="handleBatchDelete">
          <Trash2 class="h-4 w-4" />
          <span>{{ t('common.delete') }}</span>
        </button>
        <button class="batch-close" @click="selectedIds.clear()" :title="t('common.close')">
          <X class="h-4 w-4" />
        </button>
      </div>
    </div>
    
    <!-- Content -->
    <div class="content" @click.self="selectedIds.clear()">
      <div v-if="docStore.loading" class="loading-state">
        <div class="shimmer-grid">
          <Shimmer v-for="i in 6" :key="i" height="280px" rounded class="shimmer-card" />
        </div>
      </div>
      
      <div v-else-if="sortedDocuments.length === 0" class="empty-state">
        <Upload class="h-12 w-12 opacity-20" />
        <h3>{{ t('common.no_documents') }}</h3>
        <p>{{ t('upload.drop_text') }}</p>
        <button class="upload-btn-primary" @click="emit('upload')">
          <Upload class="h-4 w-4" />
          {{ t('common.upload_pdf') }}
        </button>
      </div>
      
      <div v-else class="documents-grid" :class="viewLayout">
        <DocumentCard
          v-for="doc in sortedDocuments"
          :key="doc.id"
          :document="doc"
          :selected="selectedIds.has(doc.id)"
          :view-layout="viewLayout"
          :renaming="renamingDocId === doc.id"
          @click="(e: MouseEvent) => handleCardClick(doc, e)"
          @dblclick="emit('documentOpen', doc)"
          @contextmenu.prevent="(e: MouseEvent) => handleContextMenu(doc, e)"
          @checkbox-click="handleCheckboxClick"
          @rename-saved="handleRenameSaved"
          @rename-canceled="handleRenameCanceled"
        />
      </div>
    </div>

    <ContextMenu
      v-model="showContextMenu"
      :x="contextMenuX"
      :y="contextMenuY"
      :items="contextMenuItems"
    />

    <MoveDialog
      v-model:open="showMoveDialog"
      :selectedIds="selectedIds"
      @moved="handleMoveComplete"
    />
  </div>
</template>

<style scoped>
.file-grid-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  position: relative;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid hsl(var(--border));
  background-color: hsl(var(--background));
}

.toolbar-left { display: flex; align-items: center; gap: 0.75rem; }
.toolbar-title { font-size: 1.125rem; font-weight: 600; margin: 0; color: hsl(var(--foreground)); }
.document-count { font-size: 0.875rem; color: hsl(var(--muted-foreground)); }

.toolbar-right { display: flex; align-items: center; gap: 0.75rem; }

.toolbar-filters { display: flex; gap: 0.5rem; }
.filter-select {
  padding: 0.375rem 0.5rem;
  border: 1px solid hsl(var(--border));
  border-radius: 0.25rem;
  background-color: hsl(var(--background));
  color: hsl(var(--foreground));
  font-size: 0.8125rem;
}
.filter-select:focus { outline: none; border-color: hsl(var(--primary)); }

.view-controls { display: flex; border: 1px solid hsl(var(--border)); border-radius: 0.375rem; overflow: hidden; }
.view-btn { display: flex; align-items: center; justify-content: center; width: 2.25rem; height: 2.25rem; border: none; background-color: hsl(var(--background)); color: hsl(var(--muted-foreground)); cursor: pointer; transition: all 0.15s ease; }
.view-btn:hover { background-color: hsl(var(--accent)); }
.view-btn.active { background-color: hsl(var(--secondary)); color: hsl(var(--foreground)); }

.upload-btn { display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem 1rem; border: 1px solid hsl(var(--border)); border-radius: 0.375rem; background-color: hsl(var(--background)); color: hsl(var(--foreground)); font-size: 0.875rem; font-weight: 500; cursor: pointer; transition: all 0.15s ease; }
.upload-btn:hover { background-color: hsl(var(--accent)); border-color: hsl(var(--primary)); }

.content { flex: 1; overflow-y: auto; padding: 1.5rem; }

/* Batch Actions Bar */
.batch-actions-bar {
  position: absolute;
  top: calc(60px + 0.75rem);
  left: 50%;
  transform: translateX(-50%);
  background-color: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
  border-radius: 9999px;
  padding: 0.375rem 1rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.2);
  z-index: 20;
  animation: slide-in 0.2s ease-out;
}

@keyframes slide-in { from { transform: translate(-50%, -10px); opacity: 0; } to { transform: translate(-50%, 0); opacity: 1; } }

.batch-left, .batch-right { display: flex; align-items: center; gap: 0.5rem; }
.selection-count { font-size: 0.8125rem; font-weight: 600; white-space: nowrap; }

.batch-action {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.75rem;
  border: none;
  border-radius: 0.375rem;
  background-color: hsl(var(--primary-foreground) / 0.15);
  color: hsl(var(--primary-foreground));
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}

.batch-action:hover { background-color: hsl(var(--primary-foreground) / 0.25); }
.batch-action.danger:hover { background-color: hsl(var(--destructive) / 0.3); color: #fca5a5; }

.batch-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border: none;
  border-radius: 50%;
  background-color: hsl(var(--primary-foreground) / 0.1);
  color: hsl(var(--primary-foreground) / 0.7);
  cursor: pointer;
  transition: all 0.15s;
}

.batch-close:hover { background-color: hsl(var(--primary-foreground) / 0.2); color: hsl(var(--primary-foreground)); }

.loading-state { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; gap: 1rem; color: hsl(var(--muted-foreground)); }

.shimmer-grid {
  display: grid;
  gap: 1.5rem;
  width: 100%;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
}

.shimmer-card {
  width: 100%;
}

@media (min-width: 1200px) { .shimmer-grid { grid-template-columns: repeat(3, minmax(200px, 1fr)); } }
@media (min-width: 1600px) { .shimmer-grid { grid-template-columns: repeat(4, minmax(200px, 1fr)); } }
@media (min-width: 2000px) { .shimmer-grid { grid-template-columns: repeat(5, minmax(200px, 1fr)); } }
.empty-state h3 { font-size: 1.125rem; font-weight: 600; color: hsl(var(--foreground)); margin: 0; }
.empty-state p { font-size: 0.875rem; margin: 0; }

.upload-btn-primary { display: flex; align-items: center; gap: 0.5rem; padding: 0.625rem 1.25rem; border: none; border-radius: 0.375rem; background-color: hsl(var(--primary)); color: hsl(var(--primary-foreground)); font-size: 0.875rem; font-weight: 500; cursor: pointer; transition: all 0.15s ease; }
.upload-btn-primary:hover { background-color: hsl(var(--primary) / 0.9); }

.documents-grid { display: grid; gap: 1.5rem; }
.documents-grid.grid { grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); }
.documents-grid.list { grid-template-columns: 1fr; gap: 0.5rem; }

@media (min-width: 2000px) { .documents-grid.grid { grid-template-columns: repeat(5, minmax(200px, 1fr)); } }
@media (min-width: 1600px) and (max-width: 1999px) { .documents-grid.grid { grid-template-columns: repeat(4, minmax(200px, 1fr)); } }
@media (min-width: 1200px) and (max-width: 1599px) { .documents-grid.grid { grid-template-columns: repeat(3, minmax(200px, 1fr)); } }
</style>
