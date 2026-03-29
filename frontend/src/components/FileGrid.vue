<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useDocumentStore, type Document } from '@/stores/documents'
import DocumentCard from './DocumentCard.vue'
import ContextMenu from './ui/ContextMenu.vue'
import AdvancedSearch from './AdvancedSearch.vue'
import { Upload, Search, Grid3X3, List, Loader2, Trash2, FolderInput, X, Filter } from 'lucide-vue-next'
import { useI18n } from '@/composables/useI18n'

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
const showAdvancedSearch = ref(false)

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

function toggleSelection(id: number, multi: boolean, range: boolean) {
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
    if (newSet.has(id)) {
      if (multi) newSet.delete(id)
      else newSet.clear() // Click on selected in single mode deselects others? No, usually keeps it.
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
  if (event.ctrlKey || event.metaKey) {
    toggleSelection(doc.id, true, false)
  } else if (event.shiftKey) {
    toggleSelection(doc.id, true, true)
  } else {
    // If selecting one that is already selected in multi-mode, don't clear others immediately on mousedown
    // But for simplicity, let's follow standard explorer behavior: click without modifiers clears others
    toggleSelection(doc.id, false, false)
  }
}

function selectAll() {
  if (selectedIds.value.size === sortedDocuments.value.length) {
    selectedIds.value.clear()
  } else {
    selectedIds.value = new Set(sortedDocuments.value.map(d => d.id))
  }
}

// --- Context Menu Logic ---

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
      label: single ? 'Open' : `Open ${count} items`,
      action: () => {
        if (single && targetDoc) emit('documentOpen', targetDoc)
      },
      disabled: !single
    },
    {
      label: 'Download',
      action: () => {
        selectedIds.value.forEach(id => {
          const doc = docStore.documents.find(d => d.id === id)
          if (doc) emit('documentOpen', doc)
        })
      }
    },
    { label: '', separator: true },
    {
      label: 'Move to Folder',
      icon: FolderInput,
      action: () => {
        alertMoveNotImplemented()
      }
    },
    { label: '', separator: true },
    {
      label: 'Delete',
      icon: Trash2,
      danger: true,
      action: () => handleBatchDelete()
    }
  ]
})

// --- Batch Actions ---

function alertMoveNotImplemented() {
  alert('Batch move not implemented yet')
}

async function handleBatchDelete() {
  const count = selectedIds.value.size
  if (!confirm(`Are you sure you want to delete ${count} documents?`)) return
  
  try {
    const ids = Array.from(selectedIds.value)
    // Parallel delete (better to have batch API)
    await Promise.all(ids.map(id => docStore.deleteDocument(id)))
    selectedIds.value.clear()
  } catch (e) {
    alert('Failed to delete some documents')
  }
}

// --- Watchers ---

function handleAdvancedSearch(filters: any) {
  // Construct query string or filter locally/via API
  // For now, let's append tags to search query
  if (filters.tags) {
    docStore.searchQuery += ` ${filters.tags}`
    docStore.searchDocuments(docStore.searchQuery)
  }
}

watch(() => props.folderId, () => {
  selectedIds.value.clear()
})

watch(() => props.viewMode, () => {
  docStore.fetchDocuments(props.viewMode)
  selectedIds.value.clear()
})

onMounted(() => {
  docStore.fetchDocuments(props.viewMode)
})
</script>

<template>
  <div class="file-grid-container" @click.self="selectedIds.clear()">
    <!-- Toolbar -->
    <div class="toolbar">
      <div class="toolbar-left">
        <h2 class="toolbar-title">
          {{ folderId ? 'Folder' : viewMode === 'my' ? t('nav.my_documents') : viewMode === 'shared' ? t('nav.shared') : t('nav.community') }}
        </h2>
        <span class="document-count">{{ sortedDocuments.length }} documents</span>
      </div>
      
      <div class="toolbar-right">
        <div class="search-box">
          <Search class="h-4 w-4" />
          <input 
            type="text" 
            :placeholder="t('common.search')" 
            class="search-input"
            v-model="docStore.searchQuery"
            @keyup.enter="docStore.searchDocuments(docStore.searchQuery)"
          />
          <button 
            class="adv-search-btn" 
            :class="{ active: showAdvancedSearch }"
            @click="showAdvancedSearch = !showAdvancedSearch"
            title="Advanced Filters"
          >
            <Filter class="h-3 w-3" />
          </button>
          
          <AdvancedSearch 
            v-model:open="showAdvancedSearch"
            @search="handleAdvancedSearch"
          />
        </div>
        
        <div class="view-controls">
          <button 
            class="view-btn"
            :class="{ active: viewLayout === 'grid' }"
            @click="viewLayout = 'grid'"
            title="Grid view"
          >
            <Grid3X3 class="h-4 w-4" />
          </button>
          <button 
            class="view-btn"
            :class="{ active: viewLayout === 'list' }"
            @click="viewLayout = 'list'"
            title="List view"
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
        <button class="close-selection-btn" @click="selectedIds.clear()">
          <X class="h-4 w-4" />
        </button>
        <span class="selection-count">{{ selectedIds.size }} selected</span>
        <button class="select-all-btn" @click="selectAll">Select All</button>
      </div>
      <div class="batch-right">
        <button class="batch-btn" @click="alertMoveNotImplemented">
          <FolderInput class="h-4 w-4 mr-2" /> Move
        </button>
        <button class="batch-btn danger" @click="handleBatchDelete">
          <Trash2 class="h-4 w-4 mr-2" /> Delete
        </button>
      </div>
    </div>
    
    <!-- Content -->
    <div class="content" @click.self="selectedIds.clear()">
      <div v-if="docStore.loading" class="loading-state">
        <Loader2 class="h-8 w-8 animate-spin" />
        <p>{{ t('common.loading') }}</p>
      </div>
      
      <div v-else-if="sortedDocuments.length === 0" class="empty-state">
        <Upload class="h-12 w-12 opacity-20" />
        <h3>No documents found</h3>
        <p>Upload your first PDF file to get started</p>
        <button class="upload-btn-primary" @click="emit('upload')">
          <Upload class="h-4 w-4" />
          Upload PDF
        </button>
      </div>
      
      <div v-else class="documents-grid" :class="viewLayout">
        <DocumentCard
          v-for="doc in sortedDocuments"
          :key="doc.id"
          :document="doc"
          :selected="selectedIds.has(doc.id)"
          :view-layout="viewLayout"
          @click="(e: MouseEvent) => handleCardClick(doc, e)"
          @dblclick="emit('documentOpen', doc)"
          @contextmenu.prevent="(e: MouseEvent) => handleContextMenu(doc, e)"
        />
      </div>
    </div>

    <ContextMenu 
      v-model="showContextMenu" 
      :x="contextMenuX" 
      :y="contextMenuY" 
      :items="contextMenuItems"
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

.search-box { position: relative; }
.search-box .h-4 { position: absolute; left: 0.75rem; top: 0.6rem; color: hsl(var(--muted-foreground)); }
.search-input { width: 200px; padding: 0.5rem 0.75rem 0.5rem 2.25rem; border: 1px solid hsl(var(--border)); border-radius: 0.375rem; background-color: hsl(var(--background)); color: hsl(var(--foreground)); font-size: 0.875rem; }
.search-input:focus { outline: none; border-color: hsl(var(--primary)); box-shadow: 0 0 0 2px hsl(var(--primary) / 0.1); }

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
  top: 4rem; /* Below toolbar */
  left: 50%;
  transform: translateX(-50%);
  background-color: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
  border-radius: 9999px;
  padding: 0.5rem 1rem;
  display: flex;
  align-items: center;
  gap: 1.5rem;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
  z-index: 20;
  animation: slide-in 0.2s ease-out;
}

@keyframes slide-in { from { transform: translate(-50%, -10px); opacity: 0; } to { transform: translate(-50%, 0); opacity: 1; } }

.batch-left, .batch-right { display: flex; align-items: center; gap: 0.75rem; }
.close-selection-btn { background: none; border: none; cursor: pointer; color: hsl(var(--primary-foreground) / 0.8); }
.close-selection-btn:hover { color: hsl(var(--primary-foreground)); }
.selection-count { font-size: 0.875rem; font-weight: 500; }
.select-all-btn { background: none; border: none; cursor: pointer; color: hsl(var(--primary-foreground) / 0.8); font-size: 0.875rem; text-decoration: underline; }

.batch-btn { display: flex; align-items: center; background-color: hsl(var(--primary-foreground) / 0.1); border: none; padding: 0.375rem 0.75rem; border-radius: 0.25rem; color: hsl(var(--primary-foreground)); font-size: 0.875rem; cursor: pointer; transition: all 0.2s; }
.batch-btn:hover { background-color: hsl(var(--primary-foreground) / 0.2); }
.batch-btn.danger { color: #fca5a5; }
.batch-btn.danger:hover { background-color: rgba(252, 165, 165, 0.2); }

.loading-state, .empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; gap: 1rem; color: hsl(var(--muted-foreground)); }
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
