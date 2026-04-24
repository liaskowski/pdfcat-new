<script setup lang="ts">
import { ref, nextTick, computed } from 'vue'
import { FileText, Check, Loader2, Eye, Download, Edit, Trash2, Copy, FolderInput } from 'lucide-vue-next'
import ContextMenu from './ui/ContextMenu.vue'
import { useAuthStore } from '@/stores/auth'

interface Document {
  id: number
  title: string
  filename: string
  upload_date: string
  owner_id: number
  owner_username?: string
  owner_avatar_url?: string
  file_size?: number
  tags?: string
  category?: { name: string }
  file_type?: { name: string }
}

const props = defineProps<{
  document: Document
  selected?: boolean
  viewLayout?: 'grid' | 'list'
  renaming?: boolean
}>()

const emit = defineEmits<{
  click: [event: MouseEvent]
  dblclick: [event: MouseEvent]
  select: [doc: any]
  open: [doc: any]
  delete: [doc: any]
  rename: [doc: any]
  renameSaved: [doc: any, newTitle: string]
  renameCanceled: []
  checkboxClick: [doc: any, event: MouseEvent]
  download: [doc: any]
  edit: [doc: any]
  duplicate: [doc: any]
  moveTo: [doc: any]
}>()

const auth = useAuthStore()
const showContextMenu = ref(false)
const contextMenuX = ref(0)
const contextMenuY = ref(0)

const isOwner = computed(() => {
  return auth.user?.id === props.document.owner_id
})

const contextMenuItems = computed(() => [
  {
    label: 'Open',
    icon: Eye,
    action: () => emit('open', props.document)
  },
  {
    label: 'Download',
    icon: Download,
    action: () => emit('download', props.document)
  },
  { label: '', separator: true },
  {
    label: 'Edit',
    icon: Edit,
    action: () => emit('edit', props.document),
    disabled: !isOwner.value
  },
  {
    label: 'Duplicate',
    icon: Copy,
    action: () => emit('duplicate', props.document)
  },
  {
    label: 'Move to...',
    icon: FolderInput,
    action: () => emit('moveTo', props.document)
  },
  { label: '', separator: true },
  {
    label: 'Delete',
    icon: Trash2,
    action: () => emit('delete', props.document),
    danger: true,
    disabled: !isOwner.value
  }
])

function handleContextMenu(event: MouseEvent) {
  event.preventDefault()
  event.stopPropagation()
  
  // Show context menu WITHOUT selecting (avoid checkbox conflict)
  // User can still select via checkbox if needed
  
  // Calculate position relative to viewport (account for scroll)
  contextMenuX.value = event.clientX
  contextMenuY.value = event.clientY
  showContextMenu.value = true
}

function closeContextMenu() {
  showContextMenu.value = false
}

const renameInputRef = ref<HTMLElement | null>(null)
const renameTitle = ref('')

if (props.renaming) {
  renameTitle.value = props.document.title
  nextTick(() => renameInputRef.value?.focus())
}

function handleRenameSave() {
  const newTitle = renameTitle.value.trim()
  if (newTitle && newTitle !== props.document.title) {
    emit('renameSaved', props.document, newTitle)
  } else {
    emit('renameCanceled')
  }
}

function handleRenameCancel() {
  emit('renameCanceled')
}

function onPreviewError(event: Event) {
  const img = event.target as HTMLImageElement
  img.style.display = 'none'
}

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleDateString()
}

const formatFileSize = (bytes?: number) => {
  if (!bytes) return '—'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

const getPreviewUrl = (docId: number) => {
  const token = localStorage.getItem('token')
  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
  return `${API_BASE_URL}/documents/${docId}/preview?token=${token}`
}

// In grid mode, we want standard image preview
// In list mode, maybe just icon
</script>

<template>
  <div 
    class="document-card"
    :class="{ 'selected': selected, 'list-view': viewLayout === 'list' }"
    @contextmenu="handleContextMenu"
    @click="emit('click', $event)"
    @dblclick="emit('dblclick', $event)"
  >
    <!-- Selection Checkbox (Visible on hover or selected) -->
    <div class="selection-checkbox" :class="{ 'visible': selected }" @click.stop="emit('checkboxClick', document, $event)">
      <div class="checkbox-indicator">
        <Check v-if="selected" class="h-3 w-3 text-white" />
      </div>
    </div>

    <!-- Preview / Icon -->
    <div class="card-preview">
      <template v-if="viewLayout === 'grid'">
        <img
          :src="getPreviewUrl(document.id)"
          :alt="document.title"
          class="preview-image"
          loading="lazy"
          @error="onPreviewError"
        />
        <div class="preview-fallback">
          <FileText class="h-8 w-8 text-muted-foreground opacity-50" />
        </div>
        
        <!-- Hover Overlay with Quick Actions -->
        <div class="card-overlay">
          <button class="overlay-btn" @click.stop="emit('open', document)" title="Open">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>
          </button>
          <button class="overlay-btn" @click.stop="emit('download', document)" title="Download">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/></svg>
          </button>
          <button class="overlay-btn" @click.stop="emit('edit', document)" title="Edit">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/><path d="m15 5 4 4"/></svg>
          </button>
          <button class="overlay-btn" @click.stop="emit('delete', document)" title="Delete">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>
          </button>
        </div>
      </template>
      <template v-else>
        <FileText class="h-5 w-5 text-primary" />
      </template>
    </div>
    
    <!-- Content -->
    <div class="card-content">
      <div v-if="renaming" class="rename-input-wrapper">
        <input
          ref="renameInputRef"
          v-model="renameTitle"
          class="rename-input"
          @keydown.enter="handleRenameSave"
          @keydown.escape="handleRenameCancel"
          @blur="handleRenameSave"
        />
        <Loader2 v-if="false" class="h-3 w-3 rename-spinner animate-spin" />
      </div>
      <h3 v-else class="card-title" :title="document.title">{{ document.title }}</h3>
      <div class="card-meta">
        <span class="meta-item date">{{ formatDate(document.upload_date) }}</span>
        <span v-if="document.file_size" class="meta-item size">{{ formatFileSize(document.file_size) }}</span>
        <span v-if="document.owner_username" class="meta-item owner">{{ document.owner_username }}</span>
      </div>
      <div v-if="viewLayout === 'grid' && document.tags" class="card-tags">
        <span 
          v-for="tag in document.tags.split(',').slice(0, 3)" 
          :key="tag"
          class="tag"
        >
          {{ tag.trim() }}
        </span>
        <span v-if="document.tags.split(',').length > 3" class="tag more">
          +{{ document.tags.split(',').length - 3 }}
        </span>
      </div>
    </div>
    
    <!-- List View Quick Actions (appear on hover) -->
    <div v-if="viewLayout === 'list'" class="list-actions">
      <button class="list-action-btn" @click.stop="emit('open', document)" title="Open">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>
      </button>
      <button class="list-action-btn" @click.stop="emit('download', document)" title="Download">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/></svg>
      </button>
      <button class="list-action-btn" @click.stop="emit('edit', document)" title="Edit">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/><path d="m15 5 4 4"/></svg>
      </button>
      <button class="list-action-btn delete" @click.stop="emit('delete', document)" title="Delete">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>
      </button>
    </div>
  </div>

  <!-- Context Menu (rendered OUTSIDE card to avoid overflow:hidden) -->
  <ContextMenu
    :model-value="showContextMenu"
    :x="contextMenuX"
    :y="contextMenuY"
    :items="contextMenuItems"
    @update:model-value="showContextMenu = $event"
    @close="closeContextMenu"
  />
</template>

<style scoped>
.document-card {
  position: relative;
  background-color: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  border-radius: 0.5rem;
  overflow: hidden;
  transition: all 0.2s ease;
  cursor: pointer;
  user-select: none;
}

.document-card:hover {
  border-color: hsl(var(--primary) / 0.5);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.document-card.selected {
  background-color: hsl(var(--accent) / 0.3);
  border-color: hsl(var(--primary));
  box-shadow: 0 0 0 1px hsl(var(--primary));
}

/* Checkbox */
.selection-checkbox {
  position: absolute;
  top: 0.5rem;
  left: 0.5rem;
  z-index: 10;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.2s;
}

.document-card:hover .selection-checkbox,
.selection-checkbox.visible {
  opacity: 1;
  pointer-events: auto;
}

.checkbox-indicator {
  width: 1.25rem;
  height: 1.25rem;
  border: 2px solid hsl(var(--muted-foreground) / 0.5);
  background-color: transparent;
  backdrop-filter: blur(4px);
  border-radius: 0.25rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.document-card.selected .checkbox-indicator {
  background-color: hsl(var(--primary));
  border-color: hsl(var(--primary));
}

/* Grid Layout */
.document-card:not(.list-view) {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.document-card:not(.list-view) .card-preview {
  position: relative;
  aspect-ratio: 3/4;
  background-color: hsl(var(--muted));
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.shimmer-preview {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.preview-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  position: relative;
  z-index: 1;
}

.preview-fallback {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Hover Overlay */
.card-overlay {
  position: absolute;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  opacity: 0;
  transition: opacity 0.2s ease;
  z-index: 5;
}

.document-card:hover .card-overlay {
  opacity: 1;
}

.overlay-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.5rem;
  height: 2.5rem;
  border: none;
  border-radius: 50%;
  background-color: hsl(var(--background) / 0.9);
  color: hsl(var(--foreground));
  cursor: pointer;
  transition: all 0.15s ease;
  backdrop-filter: blur(4px);
}

.overlay-btn svg {
  width: 18px;
  height: 18px;
  stroke: currentColor;
}

.overlay-btn:hover {
  background-color: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
  transform: scale(1.1);
}

.overlay-btn:active {
  transform: scale(0.95);
}

.document-card:not(.list-view) .card-content {
  padding: 0.85rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  flex: 1;
}

.card-title {
  font-size: 1rem;
  font-weight: 600;
  margin: 0;
  line-height: 1.25;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.rename-input-wrapper {
  width: 100%;
}

.rename-input {
  width: 100%;
  padding: 0.125rem 0.25rem;
  font-size: 0.875rem;
  font-weight: 500;
  border: 1px solid hsl(var(--primary));
  border-radius: 0.25rem;
  background-color: hsl(var(--background));
  color: hsl(var(--foreground));
  outline: none;
  box-shadow: 0 0 0 2px hsl(var(--primary) / 0.2);
}

.card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  font-size: 0.8125rem;
  color: hsl(var(--muted-foreground));
  margin-top: auto;
}

.meta-item { display: inline-flex; align-items: center; }

.card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
  margin-top: 0.5rem;
}

.tag {
  display: inline-flex;
  padding: 0.125rem 0.5rem;
  font-size: 0.6875rem;
  background-color: hsl(var(--secondary));
  border-radius: 9999px;
  color: hsl(var(--secondary-foreground));
}

/* List Layout */
.document-card.list-view {
  display: grid;
  grid-template-columns: 3rem 1fr auto;
  align-items: center;
  padding: 0.5rem 1rem;
  height: 3.5rem;
}

.list-view .selection-checkbox {
  position: absolute;
  left: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  background: hsl(var(--card));
}

.document-card.list-view:hover .selection-checkbox,
.document-card.list-view.selected .selection-checkbox {
  opacity: 1;
}

.list-view .card-preview {
  grid-column: 1;
  width: 2.5rem;
  height: 2.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: hsl(var(--muted));
  border-radius: 0.25rem;
}

.list-view .card-content {
  grid-column: 2;
  display: flex;
  flex-direction: column;
  gap: 0;
  padding: 0 0.5rem;
  overflow: hidden;
}

.list-view .card-title {
  font-size: 0.875rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.list-view .card-meta {
  display: flex;
  gap: 0.5rem;
  font-size: 0.7rem;
  color: hsl(var(--muted-foreground));
}

.list-view .card-tags { display: none; }

/* List View Quick Actions */
.list-actions {
  grid-column: 3;
  display: flex;
  align-items: center;
  gap: 0.25rem;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.document-card.list-view:hover .list-actions {
  opacity: 1;
}

.list-action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.75rem;
  height: 1.75rem;
  border: none;
  border-radius: 0.25rem;
  background-color: transparent;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  transition: all 0.15s ease;
}

.list-action-btn:hover {
  background-color: hsl(var(--accent));
  color: hsl(var(--foreground));
}

.list-action-btn.delete:hover {
  background-color: hsl(var(--destructive) / 0.2);
  color: hsl(var(--destructive));
}
</style>
