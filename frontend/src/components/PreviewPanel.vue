<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { 
  Calendar, FileText, User, Download, Trash2, Edit, ExternalLink, 
  Tag, Folder, FileType, Pencil, History, Copy, CheckCircle, X, Loader2
} from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { useDocumentStore, type Document, type FileHistory } from '@/stores/documents'
import { useI18n } from '@/composables/useI18n'

const props = defineProps<{
  document: Document | null
}>()

const emit = defineEmits<{
  open: [doc: Document]
  download: [doc: Document]
  delete: [doc: Document]
  edit: [doc: Document]
  editTags: [doc: Document]
  tagClick: [tag: string]
  close: []
}>()

const docStore = useDocumentStore()
const { t } = useI18n()
const history = ref<FileHistory[]>([])
const isLoadingHistory = ref(false)
const activeTab = ref<'info' | 'history'>('info')

watch(() => props.document, async (newDoc) => {
  if (newDoc) {
    activeTab.value = 'info'
    isLoadingHistory.value = true
    try {
      history.value = await docStore.fetchDocumentHistory(newDoc.id)
    } catch (e) {
      console.error('Failed to fetch history', e)
    } finally {
      isLoadingHistory.value = false
    }
  } else {
    history.value = []
  }
}, { immediate: true })

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleDateString(undefined, {
    year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
  })
}

const formatFileSize = (bytes?: number) => {
  if (!bytes) return '—'
  const units = ['B', 'KB', 'MB', 'GB']
  let size = bytes
  let unitIndex = 0
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex++
  }
  return `${size.toFixed(unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`
}

const getTags = computed(() => {
  if (!props.document?.tags) return []
  return props.document.tags.split(',').map(t => t.trim()).filter(t => t)
})

const getPreviewUrl = computed(() => {
  if (!props.document) return ''
  const token = localStorage.getItem('token')
  return `http://localhost:8000/documents/${props.document.id}/download?token=${token}`
})

const handleDuplicate = async () => {
  if (props.document) {
    try {
      await docStore.duplicateDocument(props.document.id)
      alert('Document duplicated successfully')
    } catch (e) {
      alert('Failed to duplicate document')
    }
  }
}

const handleTagClick = (tag: string) => emit('tagClick', tag.startsWith('#') ? tag : `#${tag}`)
const handleEditTags = () => props.document && emit('editTags', props.document)
const handleOpen = () => props.document && emit('open', props.document)
const handleDownload = () => props.document && emit('download', props.document)
const handleDelete = () => props.document && emit('delete', props.document)
const handleEdit = () => props.document && emit('edit', props.document)
const handleClose = () => emit('close')
</script>

<template>
  <div v-if="document" class="preview-panel">
    <div class="panel-header">
      <h3 class="panel-title">{{ document.title }}</h3>
      <button class="close-btn" @click="handleClose">
        <X class="h-4 w-4" />
      </button>
    </div>

    <div class="panel-tabs">
      <button 
        class="tab-btn" 
        :class="{ active: activeTab === 'info' }"
        @click="activeTab = 'info'"
      >
        Info
      </button>
      <button 
        class="tab-btn" 
        :class="{ active: activeTab === 'history' }"
        @click="activeTab = 'history'"
      >
        History
      </button>
    </div>

    <div class="panel-content">
      <div v-if="activeTab === 'info'" class="tab-pane info-pane">
        <div class="preview-container">
          <iframe v-if="getPreviewUrl" :src="getPreviewUrl" class="preview-frame" />
          <div v-else class="preview-placeholder">
            <FileText class="h-12 w-12 opacity-20" />
            <p>{{ t('common.loading') }}</p>
          </div>
        </div>

        <div class="preview-actions">
          <Button @click="handleOpen" variant="default" size="sm" class="flex-1">
            <ExternalLink class="h-4 w-4 mr-2" /> {{ t('common.open') || 'Open' }}
          </Button>
          <Button @click="handleDownload" variant="outline" size="sm" :title="t('common.download')">
            <Download class="h-4 w-4" />
          </Button>
          <Button @click="handleDuplicate" variant="outline" size="sm" title="Duplicate">
            <Copy class="h-4 w-4" />
          </Button>
          <Button @click="handleEdit" variant="outline" size="sm" :title="t('common.edit')">
            <Edit class="h-4 w-4" />
          </Button>
          <Button @click="handleDelete" variant="outline" size="sm" class="text-destructive" :title="t('common.delete')">
            <Trash2 class="h-4 w-4" />
          </Button>
        </div>

        <div class="metadata-section">
          <h4 class="section-title">{{ t('document.details') || 'Details' }}</h4>
          <div class="metadata-grid">
            <div class="metadata-item">
              <Calendar class="h-4 w-4" />
              <div class="metadata-content">
                <span class="metadata-label">{{ t('document.uploaded') }}</span>
                <span class="metadata-value">{{ formatDate(document.upload_date) }}</span>
              </div>
            </div>
            <div class="metadata-item">
              <FileText class="h-4 w-4" />
              <div class="metadata-content">
                <span class="metadata-label">{{ t('document.size') }}</span>
                <span class="metadata-value">{{ formatFileSize(document.file_size) }}</span>
              </div>
            </div>
            <div class="metadata-item">
              <User class="h-4 w-4" />
              <div class="metadata-content">
                <span class="metadata-label">{{ t('document.owner') }}</span>
                <span class="metadata-value">{{ document.owner_username || '—' }}</span>
              </div>
            </div>
            <div v-if="document.category" class="metadata-item">
              <Folder class="h-4 w-4" />
              <div class="metadata-content">
                <span class="metadata-label">{{ t('document.category') }}</span>
                <span class="metadata-value">{{ document.category.name }}</span>
              </div>
            </div>
            <div v-if="document.file_type" class="metadata-item">
              <FileType class="h-4 w-4" />
              <div class="metadata-content">
                <span class="metadata-label">{{ t('document.type') }}</span>
                <span class="metadata-value">{{ document.file_type.name }}</span>
              </div>
            </div>
            <div class="metadata-item">
              <CheckCircle class="h-4 w-4" :class="document.ocr_status === 'completed' ? 'text-success' : 'text-muted-foreground'" />
              <div class="metadata-content">
                <span class="metadata-label">OCR Status</span>
                <span class="metadata-value capitalize">{{ document.ocr_status || 'not started' }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="tags-section">
          <div class="tags-header">
            <Tag class="h-4 w-4" />
            <h4 class="section-title">{{ t('document.tags') }}</h4>
            <button class="edit-tags-btn" @click="handleEditTags"><Pencil class="h-3 w-3" /></button>
          </div>
          <div v-if="getTags.length > 0" class="tags-list">
            <button v-for="tag in getTags" :key="tag" class="tag-btn" @click="handleTagClick(tag)">
              #{{ tag.startsWith('#') ? tag.slice(1) : tag }}
            </button>
          </div>
          <p v-else class="no-tags">No tags yet.</p>
        </div>

        <div v-if="document.notes" class="notes-section">
          <h4 class="section-title">{{ t('document.notes') }}</h4>
          <p class="notes-text">{{ document.notes }}</p>
        </div>
      </div>

      <div v-else-if="activeTab === 'history'" class="tab-pane history-pane">
        <div v-if="isLoadingHistory" class="loading-history">
          <Loader2 class="h-6 w-6 animate-spin" />
        </div>
        <div v-else-if="history.length > 0" class="history-list">
          <div v-for="item in history" :key="item.id" class="history-item">
            <div class="history-header">
              <span class="version-badge">v{{ item.version }}</span>
              <span class="history-date">{{ formatDate(item.change_date) }}</span>
            </div>
            <p class="history-user">Changed by: {{ item.changed_by }}</p>
            <p v-if="item.notes" class="history-notes">{{ item.notes }}</p>
          </div>
        </div>
        <div v-else class="empty-history">
          <History class="h-12 w-12 opacity-20" />
          <p>No history available</p>
        </div>
      </div>
    </div>
  </div>
  <div v-else class="preview-panel empty">
    <div class="empty-content">
      <FileText class="h-16 w-16 opacity-20" />
      <h3>No document selected</h3>
      <p>Select a document to view its details</p>
    </div>
  </div>
</template>

<style scoped>
.preview-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: hsl(var(--background));
  border-left: 1px solid hsl(var(--border));
  overflow: hidden;
}

.preview-panel.empty { justify-content: center; align-items: center; }

.empty-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  color: hsl(var(--muted-foreground));
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem;
  border-bottom: 1px solid hsl(var(--border));
}

.panel-title {
  font-size: 0.875rem;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.panel-tabs {
  display: flex;
  border-bottom: 1px solid hsl(var(--border));
}

.tab-btn {
  flex: 1;
  padding: 0.75rem;
  font-size: 0.875rem;
  font-weight: 500;
  border: none;
  background: transparent;
  cursor: pointer;
  color: hsl(var(--muted-foreground));
  border-bottom: 2px solid transparent;
}

.tab-btn.active {
  color: hsl(var(--primary));
  border-bottom-color: hsl(var(--primary));
}

.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
}

.tab-pane {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.preview-container {
  aspect-ratio: 3/4;
  background-color: hsl(var(--muted));
  border-radius: 0.5rem;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-frame { width: 100%; height: 100%; border: none; }

.preview-actions { display: flex; gap: 0.5rem; }

.section-title {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  color: hsl(var(--muted-foreground));
  margin-bottom: 0.5rem;
}

.metadata-grid { display: flex; flex-direction: column; gap: 0.75rem; }
.metadata-item { display: flex; gap: 0.75rem; align-items: flex-start; }
.metadata-item .h-4 { color: hsl(var(--muted-foreground)); margin-top: 0.125rem; }
.metadata-content { display: flex; flex-direction: column; }
.metadata-label { font-size: 0.75rem; color: hsl(var(--muted-foreground)); }
.metadata-value { font-size: 0.875rem; }

.tags-header { display: flex; align-items: center; gap: 0.5rem; }
.tags-list { display: flex; flex-wrap: wrap; gap: 0.375rem; margin-top: 0.5rem; }
.tag-btn {
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  background-color: hsl(var(--secondary));
  border-radius: 9999px;
  border: none;
  cursor: pointer;
}

.notes-section { background-color: hsl(var(--muted)); padding: 0.75rem; border-radius: 0.375rem; }
.notes-text { font-size: 0.875rem; line-height: 1.5; margin: 0; }

.history-list { display: flex; flex-direction: column; gap: 1rem; }
.history-item { padding: 0.75rem; border: 1px solid hsl(var(--border)); border-radius: 0.5rem; }
.history-header { display: flex; justify-content: space-between; margin-bottom: 0.25rem; }
.version-badge { font-size: 0.75rem; font-weight: 600; background: hsl(var(--primary) / 0.1); color: hsl(var(--primary)); padding: 0.125rem 0.375rem; border-radius: 0.25rem; }
.history-date { font-size: 0.75rem; color: hsl(var(--muted-foreground)); }
.history-user { font-size: 0.8125rem; margin: 0; }
.history-notes { font-size: 0.8125rem; color: hsl(var(--muted-foreground)); margin-top: 0.25rem; }

.loading-history, .empty-history { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 2rem; color: hsl(var(--muted-foreground)); }
</style>
