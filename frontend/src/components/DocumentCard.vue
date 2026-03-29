<script setup lang="ts">
import { FileText, Check } from 'lucide-vue-next'

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
}>()

const emit = defineEmits<{
  select: [doc: Document]
  open: [doc: Document]
  delete: [doc: Document]
  rename: [doc: Document]
}>()

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
  return `http://localhost:8000/documents/${docId}/preview?token=${token}`
}

// In grid mode, we want standard image preview
// In list mode, maybe just icon
</script>

<template>
  <div 
    class="document-card"
    :class="{ 'selected': selected, 'list-view': viewLayout === 'list' }"
  >
    <!-- Selection Checkbox (Visible on hover or selected) -->
    <div class="selection-checkbox" :class="{ 'visible': selected }">
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
          @error="($event.target as HTMLImageElement).style.display = 'none'"
        />
        <div class="preview-fallback">
          <FileText class="h-8 w-8 text-muted-foreground opacity-20" />
        </div>
      </template>
      <template v-else>
        <FileText class="h-5 w-5 text-primary" />
      </template>
    </div>
    
    <!-- Content -->
    <div class="card-content">
      <h3 class="card-title" :title="document.title">{{ document.title }}</h3>
      
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
  </div>
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
  background-color: hsl(var(--accent));
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
  transition: opacity 0.2s;
}

.document-card:hover .selection-checkbox,
.selection-checkbox.visible {
  opacity: 1;
}

.checkbox-indicator {
  width: 1.25rem;
  height: 1.25rem;
  border: 1px solid hsl(var(--border));
  background-color: hsl(var(--background));
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
  aspect-ratio: 3/4; /* PDF Aspect */
  background-color: hsl(var(--muted));
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
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

.document-card:not(.list-view) .card-content {
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  flex: 1;
}

.card-title {
  font-size: 0.875rem;
  font-weight: 500;
  margin: 0;
  line-height: 1.2;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  font-size: 0.75rem;
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
  padding: 0.125rem 0.375rem;
  font-size: 0.625rem;
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
  position: relative;
  top: auto;
  left: auto;
  margin-right: 0.75rem;
  grid-column: 1;
  opacity: 0; /* Only show on hover/select in list too? Or always? Standard is hover */
}

.document-card.list-view:hover .selection-checkbox,
.document-card.list-view.selected .selection-checkbox {
  opacity: 1;
}

/* Adjust grid if checkbox is hidden */
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

/* When checkbox is visible, it might overlap preview in list view or we shift.
   For simplicity in this CSS grid, let's just overlay checkbox on preview area 
   or shift content. Overlay is easier.
*/
.list-view .selection-checkbox {
  position: absolute;
  left: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  background: hsl(var(--card)); /* To cover icon behind */
}

.list-view .card-content {
  grid-column: 2 / -1;
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1fr;
  align-items: center;
  gap: 1rem;
  padding: 0 1rem;
}

.list-view .card-title {
  font-size: 0.875rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.list-view .card-meta {
  display: contents; /* Use grid from parent */
}

.list-view .card-tags { display: none; } /* Hide tags in list for now or add column */
</style>
