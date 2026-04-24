<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useDocumentStore, type Document } from '@/stores/documents'
import DocumentCard from './DocumentCard.vue'
import ContextMenu from './ui/ContextMenu.vue'
import MoveDialog from './MoveDialog.vue'
import { Upload, Grid3X3, List, Trash2, FolderInput, X, ArrowUpDown, ArrowUp, FileText } from 'lucide-vue-next'
import Shimmer from './ui/Shimmer.vue'
import { useI18n } from '@/composables/useI18n'
import { useKeyboardShortcuts } from '@/composables/useKeyboardShortcuts'
import { useToast } from '@/composables/useToast'

const props = defineProps<{
  viewMode: string
  folderId: number | null
  ownerId: number | null
  searchQuery?: string
}>()

const emit = defineEmits<{
  upload: []
  uploadFiles: [files: FileList]
  documentSelect: [doc: any]
  documentOpen: [doc: any]
  documentDownload: [doc: any]
  documentDelete: [doc: any]
  documentEdit: [doc: any]
  documentDuplicate: [doc: any]
  documentMove: [doc: any, targetFolderId: number | null]
}>()

const docStore = useDocumentStore()
const { t } = useI18n()
const toast = useToast()

// Keyboard Shortcuts
useKeyboardShortcuts({
  onSelectAll: selectAll,
  onDelete: handleBatchDelete,
  onClose: () => selectedIds.value.clear(),
  onSearch: () => {
    const searchInput = document.querySelector('input[type="text"]') as HTMLInputElement
    if (searchInput) searchInput.focus()
  },
  onUpload: () => emit('upload'),
  onOpen: () => {
    if (selectedIds.value.size === 1) {
      const id = Array.from(selectedIds.value)[0]
      const doc = docStore.documents.find(d => d.id === id)
      if (doc) emit('documentOpen', doc)
    }
  },
})

// Drag and Drop State
const isDragOver = ref(false)
const dragCounter = ref(0)

// Selection State
const selectedIds = ref<Set<number>>(new Set())
const lastSelectedId = ref<number | null>(null)

// Context Menu State
const showContextMenu = ref(false)
const contextMenuX = ref(0)
const contextMenuY = ref(0)
const contextTargetId = ref<number | null>(null)

function handleDragEnter(e: DragEvent) {
  e.preventDefault()
  dragCounter.value++
  isDragOver.value = true
}

function handleDragLeave(e: DragEvent) {
  e.preventDefault()
  dragCounter.value--
  if (dragCounter.value === 0) {
    isDragOver.value = false
  }
}

function handleDragOver(e: DragEvent) {
  e.preventDefault()
}

function handleDrop(e: DragEvent) {
  e.preventDefault()
  isDragOver.value = false
  dragCounter.value = 0

  const files = e.dataTransfer?.files
  if (files && files.length > 0) {
    const pdfFiles = Array.from(files).filter(f => f.type === 'application/pdf')
    if (pdfFiles.length === 0) {
      toast.error('Only PDF files are allowed', 'Upload Error')
      return
    }
    const dt = new DataTransfer()
    pdfFiles.forEach(f => dt.items.add(f))
    emit('uploadFiles', dt.files)
  }
}

// View State
const viewLayout = ref<'grid' | 'list'>('grid')
const sortBy = ref<'date' | 'name' | 'owner' | 'size'>('date')
const sortOrder = ref<'asc' | 'desc'>('desc')
const groupBy = ref<'none' | 'date' | 'category' | 'type' | 'owner'>('none')

function blurSelect(e: Event) {
  ;(e.target as HTMLElement).blur()
}

function formatDateGroup(dateString: string): string {
  const date = new Date(dateString)
  const now = new Date()
  const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24))
  
  if (diffDays === 0) return 'Today'
  if (diffDays === 1) return 'Yesterday'
  if (diffDays < 7) return 'This Week'
  if (diffDays < 30) return 'This Month'
  return date.toLocaleDateString(undefined, { month: 'long', year: 'numeric' })
}

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

const groupedDocuments = computed(() => {
  if (groupBy.value === 'none') return null
  
  const groups: Record<string, any[]> = {}
  sortedDocuments.value.forEach(doc => {
    let key: string
    switch (groupBy.value) {
      case 'date':
        key = formatDateGroup(doc.upload_date)
        break
      case 'category':
        key = doc.category?.name || 'Uncategorized'
        break
      case 'type':
        key = doc.file_type?.name || 'Unknown'
        break
      case 'owner':
        key = doc.owner_username || 'Unknown'
        break
      default:
        key = 'Other'
    }
    if (!groups[key]) groups[key] = []
    groups[key].push(doc)
  })
  
  return groups
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

// --- Context Menu Logic (for batch operations) ---

const showMoveDialog = ref(false)

function handleGridContextMenu(event: MouseEvent) {
  // Only show batch context menu if multiple documents selected
  if (selectedIds.value.size < 2) return
  
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

function handleDownload(doc: any) {
  emit('documentDownload', doc)
}

function handleDocumentEdit(doc: any) {
  emit('documentSelect', doc)
  emit('documentEdit', doc)
}

function handleDocumentDelete(doc: any) {
  selectedIds.value = new Set([doc.id])
  handleBatchDelete()
}

function handleDocumentDuplicate(doc: any) {
  docStore.duplicateDocument(doc.id, props.folderId ?? undefined)
    .then(() => {
      toast.success('Document duplicated')
      docStore.fetchDocuments(props.viewMode, props.folderId, props.ownerId)
    })
    .catch((e: any) => {
      toast.error(e?.response?.data?.detail || 'Failed to duplicate document')
    })
}

function handleDocumentMove(doc: any) {
  selectedIds.value = new Set([doc.id])
  showMoveDialog.value = true
}

async function handleBatchDelete() {
  const count = selectedIds.value.size
  if (!confirm(t('confirm.delete_documents').replace('{count}', count.toString()))) return

  try {
    const ids = Array.from(selectedIds.value)
    
    await Promise.all(ids.map(id => docStore.deleteDocument(id)))
    selectedIds.value.clear()
    
    toast.success(`Deleted ${count} document(s)`)
  } catch (e) {
    toast.error(t('confirm.delete_failed'))
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
  <div 
    class="file-grid-container"
    @dragenter="handleDragEnter"
    @dragleave="handleDragLeave"
    @dragover="handleDragOver"
    @drop="handleDrop"
  >
    <!-- Drag Drop Overlay -->
    <div 
      v-if="isDragOver" 
      class="drag-drop-overlay"
    >
      <div class="drag-drop-content">
        <Upload class="h-16 w-16 mb-4 opacity-60" />
        <h3>{{ t('upload.drop_text') }}</h3>
        <p>Drop PDF files here to upload</p>
      </div>
    </div>
    <!-- Toolbar -->
    <div class="toolbar">
      <!-- Normal Toolbar -->
      <template v-if="selectedIds.size === 0">
        <div class="toolbar-left">
          <h2 class="toolbar-title">
            {{ currentFolderName || (viewMode === 'my' ? t('nav.my_documents') : viewMode === 'shared' ? t('nav.shared') : t('nav.community')) }}
          </h2>
          <span class="document-count">{{ sortedDocuments.length }} {{ t('common.documents') }}</span>
        </div>
        
        <div class="toolbar-right">
          <div class="toolbar-filters">
            <!-- Group By Control -->
            <select v-model="groupBy" class="filter-select" :title="t('common.group_by')">
              <option value="none">{{ t('group.none') }}</option>
              <option value="date">{{ t('group.date') }}</option>
              <option value="category">{{ t('group.category') }}</option>
              <option value="type">{{ t('group.type') }}</option>
              <option value="owner">{{ t('group.owner') }}</option>
            </select>
            <!-- Sort Control -->
            <div class="sort-control">
              <select v-model="sortBy" class="sort-select" :title="t('common.sort_by')" @change="blurSelect($event)">
                <option value="date">{{ t('sort.date') }}</option>
                <option value="name">{{ t('sort.name') }}</option>
                <option value="owner">{{ t('sort.owner') }}</option>
              </select>
              <button class="sort-order-btn" @click="sortOrder = sortOrder === 'desc' ? 'asc' : 'desc'" :title="sortOrder === 'desc' ? t('sort.desc') : t('sort.asc')">
                <ArrowUpDown v-if="sortOrder === 'desc'" class="h-3.5 w-3.5" />
                <ArrowUp v-else class="h-3.5 w-3.5" />
              </button>
            </div>
            <select v-model="selectedCategoryId" class="filter-select" @change="handleFilterChange" @blur="blurSelect($event)">
              <option :value="null">{{ t('filters.all_categories') }}</option>
              <option v-for="cat in docStore.categories" :key="cat.id" :value="cat.id">
                {{ cat.name }}
              </option>
            </select>
            <select v-model="selectedFileTypeId" class="filter-select" @change="handleFilterChange" @blur="blurSelect($event)">
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
      </template>
      
      <!-- Batch Actions Toolbar -->
      <template v-else>
        <div class="toolbar-left">
          <span class="selection-count">{{ selectedIds.size }} {{ t('common.selected') }}</span>
          <button class="batch-action-inline" @click="selectAll">
            <span class="batch-icon">☑</span> {{ t('common.select_all') }}
          </button>
        </div>
        <div class="toolbar-right">
          <button class="batch-action-inline" @click="handleBatchMove">
            <FolderInput class="h-4 w-4" />
            <span>{{ t('common.move') }}</span>
          </button>
          <button class="batch-action-inline danger" @click="handleBatchDelete">
            <Trash2 class="h-4 w-4" />
            <span>{{ t('common.delete') }}</span>
          </button>
          <button class="batch-close-inline" @click="selectedIds.clear()" :title="t('common.close')">
            <X class="h-4 w-4" />
          </button>
        </div>
      </template>
    </div>
    
    <!-- Content -->
    <div class="content" @click.self="selectedIds.clear()" @contextmenu.prevent="handleGridContextMenu">
      <div v-if="docStore.loading" class="loading-state">
        <div class="shimmer-grid">
          <Shimmer v-for="i in 6" :key="i" height="280px" rounded class="shimmer-card" />
        </div>
      </div>
      
      <div v-else-if="sortedDocuments.length === 0" class="empty-state">
        <div class="empty-state-content">
          <div class="empty-icon-wrapper">
            <FileText class="empty-icon" />
          </div>
          <div class="empty-text">
            <h3>{{ t('common.no_documents') }}</h3>
            <p>{{ t('upload.drop_text') }}</p>
          </div>
          <button class="upload-btn-primary" @click="emit('upload')">
            <Upload class="h-4 w-4" />
            {{ t('common.upload_pdf') }}
          </button>
          <div class="drag-hint">
            <span class="drag-hint-key">Ctrl</span>
            <span class="drag-hint-plus">+</span>
            <span class="drag-hint-key">V</span>
            <span class="drag-hint-text">or drag & drop</span>
          </div>
        </div>
      </div>
      
      <!-- Grouped View -->
      <template v-else-if="groupedDocuments">
        <div v-for="(docs, groupName) in groupedDocuments" :key="groupName" class="document-group">
          <h3 class="group-header">
            <span>{{ groupName }}</span>
            <span class="group-count">{{ docs.length }}</span>
          </h3>
          <div class="documents-grid" :class="viewLayout">
            <DocumentCard
              v-for="doc in docs"
              :key="doc.id"
              :document="doc"
              :selected="selectedIds.has(doc.id)"
              :view-layout="viewLayout"
              :renaming="renamingDocId === doc.id"
              @click="(e: MouseEvent) => handleCardClick(doc, e)"
              @dblclick="emit('documentOpen', doc)"
              @checkbox-click="handleCheckboxClick"
              @rename-saved="handleRenameSaved"
              @rename-canceled="handleRenameCanceled"
              @open="emit('documentOpen', $event)"
              @download="handleDownload"
              @edit="handleDocumentEdit"
              @delete="handleDocumentDelete"
              @duplicate="handleDocumentDuplicate"
              @move-to="handleDocumentMove"
            />
          </div>
        </div>
      </template>
      
      <!-- Ungrouped View -->
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
          @checkbox-click="handleCheckboxClick"
          @rename-saved="handleRenameSaved"
          @rename-canceled="handleRenameCanceled"
          @open="emit('documentOpen', $event)"
          @download="handleDownload"
          @edit="handleDocumentEdit"
          @delete="handleDocumentDelete"
          @duplicate="handleDocumentDuplicate"
          @move-to="handleDocumentMove"
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
  min-height: 64px;
}

.toolbar-left { display: flex; align-items: center; gap: 0.75rem; flex-wrap: nowrap; }
.toolbar-title { font-size: 1.25rem; font-weight: 600; margin: 0; color: hsl(var(--foreground)); white-space: nowrap; }
.document-count { font-size: 0.9375rem; color: hsl(var(--muted-foreground)); }

.toolbar-right { display: flex; align-items: center; gap: 0.75rem; flex-wrap: nowrap; }

.toolbar-filters { display: flex; gap: 0.5rem; align-items: center; }

/* Compact Sort Control */
.sort-control {
  display: flex;
  align-items: center;
  border: 1px solid hsl(var(--border));
  border-radius: 0.375rem;
  overflow: hidden;
  background-color: hsl(var(--background));
  transition: all 0.15s ease;
}

.sort-control:hover {
  border-color: hsl(var(--primary));
}

.sort-select {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.625rem;
  border: none;
  border-right: 1px solid hsl(var(--border));
  background-color: transparent;
  color: hsl(var(--foreground));
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  outline: none;
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 0.5rem center;
  background-size: 1rem;
  padding-right: 2rem;
}

.sort-select:focus { background-color: hsl(var(--accent)); }

.sort-order-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 2rem;
  height: 2.125rem;
  border: none;
  background-color: transparent;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  transition: all 0.15s ease;
}

.sort-order-btn:hover { background-color: hsl(var(--accent)); color: hsl(var(--foreground)); }
.filter-select {
  padding: 0.375rem 0.625rem;
  border: 1px solid hsl(var(--border));
  border-radius: 0.375rem;
  background-color: hsl(var(--background));
  color: hsl(var(--foreground));
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}
.filter-select:hover { border-color: hsl(var(--primary)); }
.filter-select:focus { outline: none; border-color: hsl(var(--primary)); background-color: hsl(var(--accent)); }

.view-controls { display: flex; border: 1px solid hsl(var(--border)); border-radius: 0.375rem; overflow: hidden; }
.view-btn { display: flex; align-items: center; justify-content: center; width: 2.25rem; height: 2.25rem; border: none; background-color: hsl(var(--background)); color: hsl(var(--muted-foreground)); cursor: pointer; transition: all 0.15s ease; }
.view-btn:hover { background-color: hsl(var(--accent)); }
.view-btn.active { background-color: hsl(var(--secondary)); color: hsl(var(--foreground)); }

.upload-btn { display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem 1rem; border: 1px solid hsl(var(--border)); border-radius: 0.375rem; background-color: hsl(var(--background)); color: hsl(var(--foreground)); font-size: 0.875rem; font-weight: 500; cursor: pointer; transition: all 0.15s ease; }
.upload-btn:hover { background-color: hsl(var(--accent)); border-color: hsl(var(--primary)); }

.content { flex: 1; overflow-y: auto; padding: 1.5rem; }

/* Batch Actions Inline in Toolbar */
.batch-action-inline {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.75rem;
  border: none;
  border-radius: 0.375rem;
  background-color: hsl(var(--primary) / 0.2);
  color: hsl(var(--primary));
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}

.batch-action-inline:hover { background-color: hsl(var(--primary) / 0.3); }
.batch-action-inline.danger:hover { background-color: hsl(var(--destructive) / 0.3); color: hsl(var(--destructive)); }

.batch-close-inline {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border: none;
  border-radius: 50%;
  background-color: hsl(var(--primary) / 0.1);
  color: hsl(var(--primary));
  cursor: pointer;
  transition: all 0.15s;
}

.batch-close-inline:hover { background-color: hsl(var(--primary) / 0.2); color: hsl(var(--primary)); }

.batch-icon { font-size: 1rem; }

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
.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
}

.empty-state-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1.5rem;
  max-width: 400px;
  padding: 3rem 2rem;
  background-color: hsl(var(--card) / 0.5);
  border: 2px dashed hsl(var(--border));
  border-radius: 1rem;
}

.empty-icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 80px;
  height: 80px;
  background: linear-gradient(135deg, hsl(var(--primary) / 0.1), hsl(var(--primary) / 0.05));
  border-radius: 50%;
}

.empty-icon {
  width: 40px;
  height: 40px;
  color: hsl(var(--primary) / 0.6);
}

.empty-text {
  text-align: center;
}

.empty-text h3 {
  font-size: 1.25rem;
  font-weight: 600;
  color: hsl(var(--foreground));
  margin: 0 0 0.5rem 0;
}

.empty-text p {
  font-size: 0.9375rem;
  color: hsl(var(--muted-foreground));
  margin: 0;
  line-height: 1.5;
}

.drag-hint {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground) / 0.7);
}

.drag-hint-key {
  padding: 0.125rem 0.375rem;
  background-color: hsl(var(--muted));
  border: 1px solid hsl(var(--border));
  border-radius: 0.25rem;
  font-family: monospace;
  font-size: 0.6875rem;
}

.drag-hint-plus {
  color: hsl(var(--muted-foreground) / 0.5);
}

.drag-hint-text {
  margin-left: 0.25rem;
}

.upload-btn-primary { display: flex; align-items: center; gap: 0.5rem; padding: 0.625rem 1.25rem; border: none; border-radius: 0.375rem; background-color: hsl(var(--primary)); color: hsl(var(--primary-foreground)); font-size: 0.875rem; font-weight: 500; cursor: pointer; transition: all 0.15s ease; }
.upload-btn-primary:hover { background-color: hsl(var(--primary) / 0.9); }

.documents-grid { display: grid; gap: 1.5rem; }
.documents-grid.grid { grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); }
.documents-grid.list { grid-template-columns: 1fr; gap: 0.5rem; }

@media (min-width: 2000px) { .documents-grid.grid { grid-template-columns: repeat(5, minmax(200px, 1fr)); } }
@media (min-width: 1600px) and (max-width: 1999px) { .documents-grid.grid { grid-template-columns: repeat(4, minmax(200px, 1fr)); } }
@media (min-width: 1200px) and (max-width: 1599px) { .documents-grid.grid { grid-template-columns: repeat(3, minmax(200px, 1fr)); } }

.drag-drop-overlay {
  position: absolute;
  inset: 0;
  background-color: hsl(var(--primary) / 0.08);
  border: 2px dashed hsl(var(--primary) / 0.4);
  border-radius: 0.5rem;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(2px);
}

.dark .drag-drop-overlay {
  background-color: hsl(var(--primary) / 0.15);
}

.drag-drop-content {
  text-align: center;
  color: hsl(var(--primary));
  pointer-events: none;
}

.drag-drop-content h3 {
  font-size: 1.25rem;
  font-weight: 600;
  margin: 0 0 0.5rem;
}

.drag-drop-content p {
  font-size: 0.875rem;
  opacity: 0.8;
  margin: 0;
}
</style>
