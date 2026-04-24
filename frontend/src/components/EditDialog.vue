<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { X, Save, Loader2, CheckCircle2, AlertCircle, FileText, Lock, Globe, PenSquare, Shield, Calendar, HardDrive, Plus } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useDocumentStore, type Document } from '@/stores/documents'
import PdfPreview from '@/components/PdfPreview.vue'
import TagInput from '@/components/TagInput.vue'
import QuickAddModal from '@/components/QuickAddModal.vue'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()

const props = defineProps<{
  open: boolean
  document: Document | null
}>()

const emit = defineEmits<{
  'update:open': [open: boolean]
  saved: [document: any]
}>()

const docStore = useDocumentStore()

const title = ref('')
const notes = ref('')
const tags = ref('')
const categoryId = ref<number | null>(null)
const fileTypeId = ref<number | null>(null)
const folderId = ref<number | null>(null)
const isPrivate = ref(false)
const isPublic = ref(false)
const isPublicEdit = ref(false)
const isReadOnly = ref(false)

const isSaving = ref(false)
const saveError = ref<string | null>(null)
const saveSuccess = ref(false)

const previewUrl = computed(() => {
  if (props.document?.id) {
    const token = localStorage.getItem('token')
    const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
    const url = `${baseUrl}/documents/${props.document.id}/download?token=${token}&t=${Date.now()}`
    return url
  }
  return null
})

const isOpen = computed({
  get: () => props.open,
  set: (value) => emit('update:open', value)
})

// Visibility mode helper
const visibilityMode = computed({
  get: () => {
    if (isPrivate.value) return 'private'
    if (isPublicEdit.value) return 'public_edit'
    if (isPublic.value) return 'public'
    return 'private'
  },
  set: (mode: string) => {
    isPrivate.value = mode === 'private'
    isPublic.value = mode === 'public'
    isPublicEdit.value = mode === 'public_edit'
  }
})

// Format file size
function formatSize(bytes?: number): string {
  if (!bytes || bytes === 0) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

// Format date
function formatDate(dateStr?: string): string {
  if (!dateStr) return '—'
  const d = new Date(dateStr)
  return d.toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

watch(() => props.document, (doc) => {
  if (doc) {
    title.value = doc.title
    notes.value = doc.notes || ''
    tags.value = doc.tags || ''
    categoryId.value = doc.category_id || null
    fileTypeId.value = doc.file_type_id || null
    folderId.value = doc.folder_id || null
    isPrivate.value = doc.is_private
    isPublic.value = doc.is_public
    isPublicEdit.value = doc.is_public_edit
    isReadOnly.value = doc.is_read_only
  }
}, { immediate: true })

async function handleSave() {
  if (!props.document) return

  isSaving.value = true
  saveError.value = null
  saveSuccess.value = false

  try {
    const data = await docStore.updateDocument(props.document.id, {
      title: title.value,
      notes: notes.value,
      tags: tags.value,
      category_id: categoryId.value || undefined,
      file_type_id: fileTypeId.value || undefined,
      folder_id: folderId.value,
      is_private: isPrivate.value,
      is_public: isPublic.value,
      is_public_edit: isPublicEdit.value,
      is_read_only: isReadOnly.value
    })

    saveSuccess.value = true

    setTimeout(() => {
      emit('saved', data)
      isOpen.value = false
    }, 1000)

  } catch (error: any) {
    saveError.value = error.response?.data?.detail || error.message || t('edit.save_failed')
  } finally {
    isSaving.value = false
  }
}

function handleClose() {
  saveError.value = null
  saveSuccess.value = false
  isOpen.value = false
}

// Quick-add modals
const quickAddCategory = ref(false)
const quickAddType = ref(false)

function onCategoryCreated(item: { id: number; name: string }) {
  categoryId.value = item.id
}
function onTypeCreated(item: { id: number; name: string }) {
  fileTypeId.value = item.id
}
</script>

<template>
  <Transition name="modal">
    <div v-if="isOpen" class="modal-overlay" @click.self="handleClose">
      <div class="modal-content modal-content-wide" @click.stop>
        <div class="modal-header">
          <h2 class="modal-title">{{ t('edit.title') }}</h2>
          <button class="close-btn" @click="handleClose" :disabled="isSaving">
            <X class="h-4 w-4" />
          </button>
        </div>

        <div class="modal-body modal-body-split">
          <!-- Left: PDF Preview -->
          <div class="preview-pane">
            <PdfPreview v-if="previewUrl" :key="previewUrl" :src="previewUrl" />
            <div v-else class="no-preview">
              <FileText class="h-12 w-12 opacity-30" />
              <p>{{ t('edit.no_preview') || 'No preview available' }}</p>
            </div>
          </div>

          <!-- Right: Form -->
          <div class="form-pane">
            <!-- Document Info -->
            <div class="doc-info">
              <p class="doc-filename">{{ document?.filename }}</p>
              <div class="doc-meta">
                <span class="doc-meta-item">
                  <Calendar class="h-3 w-3" />
                  {{ formatDate(document?.upload_date) }}
                </span>
                <span class="doc-meta-sep">&middot;</span>
                <span class="doc-meta-item">
                  <HardDrive class="h-3 w-3" />
                  {{ formatSize(document?.file_size) }}
                </span>
              </div>
            </div>

            <!-- Status alerts -->
            <div v-if="isSaving" class="status-bar status-saving">
              <Loader2 class="h-4 w-4 animate-spin" />
              <span>{{ t('edit.saving') }}</span>
            </div>
            <div v-else-if="saveSuccess" class="status-bar status-success">
              <CheckCircle2 class="h-4 w-4" />
              <span>{{ t('edit.saved_success') }}</span>
            </div>
            <div v-else-if="saveError" class="status-bar status-error">
              <AlertCircle class="h-4 w-4 shrink-0" />
              <span>{{ saveError }}</span>
            </div>

            <!-- Title -->
            <div class="form-section">
              <div class="form-group">
                <label for="edit-title" class="form-label">{{ t('upload.title_label') }}</label>
                <Input id="edit-title" v-model="title" :placeholder="t('upload.title_placeholder')" :disabled="isSaving" />
              </div>
            </div>

            <!-- Metadata -->
            <div class="form-section">
              <div class="section-header">
                <span class="section-icon">🏷️</span>
                <span class="section-title">{{ t('upload.metadata_label') || 'Metadata' }}</span>
              </div>
              <div class="form-grid">
                <div class="form-group">
                  <label class="form-label">{{ t('upload.category_label') }}</label>
                  <div class="select-with-add">
                    <select v-model="categoryId" class="select-input" :disabled="isSaving">
                      <option :value="null">{{ t('upload.no_category') }}</option>
                      <option v-for="cat in docStore.categories" :key="cat.id" :value="cat.id">
                        {{ cat.name }}
                      </option>
                    </select>
                    <button type="button" class="btn-add" :disabled="isSaving" @click="quickAddCategory = true" title="Add category">
                      <Plus class="h-4 w-4" />
                    </button>
                  </div>
                </div>
                <div class="form-group">
                  <label class="form-label">{{ t('upload.file_type_label') }}</label>
                  <div class="select-with-add">
                    <select v-model="fileTypeId" class="select-input" :disabled="isSaving">
                      <option :value="null">{{ t('upload.no_type') }}</option>
                      <option v-for="type in docStore.fileTypes" :key="type.id" :value="type.id">
                        {{ type.name }}
                      </option>
                    </select>
                    <button type="button" class="btn-add" :disabled="isSaving" @click="quickAddType = true" title="Add file type">
                      <Plus class="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
              <div class="form-group">
                <label class="form-label">{{ t('upload.folder_label') }}</label>
                <select v-model="folderId" class="select-input" :disabled="isSaving">
                  <option :value="null">{{ t('upload.root') }}</option>
                  <option v-for="f in docStore.folders" :key="f.id" :value="f.id">
                    {{ f.name }}
                  </option>
                </select>
              </div>
              <div class="form-group">
                <label for="edit-tags" class="form-label">{{ t('upload.tags_label') }}</label>
                <TagInput v-model="tags" :disabled="isSaving" :placeholder="t('upload.tags_placeholder')" />
              </div>
            </div>

            <!-- Notes -->
            <div class="form-section">
              <div class="section-header">
                <span class="section-icon">📝</span>
                <span class="section-title">{{ t('upload.notes_label') }}</span>
              </div>
              <div class="form-group">
                <textarea
                  id="edit-notes"
                  v-model="notes"
                  class="textarea"
                  :placeholder="t('upload.notes_placeholder')"
                  :disabled="isSaving"
                  rows="3"
                />
              </div>
            </div>

            <!-- Access -->
            <div class="form-section">
              <div class="section-header">
                <Lock class="section-icon" />
                <span class="section-title">{{ t('upload.visibility') }}</span>
              </div>

              <div class="pill-group">
                <button
                  type="button"
                  class="pill"
                  :class="{ 'pill-active': visibilityMode === 'private' }"
                  :disabled="isSaving"
                  @click="visibilityMode = 'private'"
                >
                  <Lock class="h-3.5 w-3.5" />
                  <span>{{ t('upload.private') }}</span>
                </button>
                <button
                  type="button"
                  class="pill"
                  :class="{ 'pill-active': visibilityMode === 'public' }"
                  :disabled="isSaving"
                  @click="visibilityMode = 'public'"
                >
                  <Globe class="h-3.5 w-3.5" />
                  <span>{{ t('upload.public_view') }}</span>
                </button>
                <button
                  type="button"
                  class="pill"
                  :class="{ 'pill-active': visibilityMode === 'public_edit' }"
                  :disabled="isSaving"
                  @click="visibilityMode = 'public_edit'"
                >
                  <PenSquare class="h-3.5 w-3.5" />
                  <span>{{ t('upload.public_edit') }}</span>
                </button>
              </div>

              <!-- Read-Only pill -->
              <div class="pill-group" style="margin-top: 0.375rem;">
                <button
                  type="button"
                  class="pill"
                  :class="{ 'pill-active': isReadOnly }"
                  :disabled="isSaving"
                  @click="isReadOnly = !isReadOnly"
                >
                  <Shield class="h-3.5 w-3.5" />
                  <span>{{ t('document.is_read_only') }}</span>
                </button>
              </div>
            </div>

            <!-- Footer -->
            <div class="modal-footer">
              <Button variant="outline" @click="handleClose" :disabled="isSaving">{{ t('common.cancel') }}</Button>
              <Button @click="handleSave" :disabled="isSaving">
                <Save class="h-4 w-4 mr-2" />
                {{ isSaving ? t('edit.saving') : t('edit.save_changes') }}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Transition>

  <!-- Quick-add modals -->
  <QuickAddModal
    :open="quickAddCategory"
    title="Add Category"
    placeholder="Category name"
    @update:open="quickAddCategory = $event"
    @created="onCategoryCreated"
  />
  <QuickAddModal
    :open="quickAddType"
    title="Add File Type"
    placeholder="File type name"
    @update:open="quickAddType = $event"
    @created="onTypeCreated"
  />
</template>

<style scoped>
/* ---- Overlay ---- */
.modal-overlay {
  position: fixed;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
  padding: 1rem;
}

/* ---- Transition ---- */
.modal-enter-active { transition: opacity 0.2s ease; }
.modal-leave-active { transition: opacity 0.15s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }

.modal-enter-active .modal-content {
  transition: transform 0.2s ease, opacity 0.2s ease;
}
.modal-leave-active .modal-content {
  transition: transform 0.15s ease, opacity 0.15s ease;
}
.modal-enter-from .modal-content {
  transform: scale(0.95);
  opacity: 0;
}
.modal-leave-to .modal-content {
  transform: scale(0.95);
  opacity: 0;
}

/* ---- Content ---- */
.modal-content {
  background-color: hsl(var(--background));
  border-radius: 0.5rem;
  width: 100%;
  max-width: 550px;
  max-height: 95vh;
  overflow-y: auto;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
}

.modal-content-wide {
  max-width: 1200px;
  width: 95vw;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid hsl(var(--border));
}

.modal-title {
  font-size: 1.125rem;
  font-weight: 600;
  margin: 0;
}

.close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border: none;
  background: transparent;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  border-radius: 0.25rem;
  transition: background-color 0.15s;
}
.close-btn:hover {
  background-color: hsl(var(--muted));
}

.modal-body {
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.modal-body-split {
  display: flex;
  flex-direction: row;
  gap: 1rem;
  padding: 1rem;
  height: 75vh;
  min-height: 520px;
}

/* ---- Preview ---- */
.preview-pane {
  flex: 0 0 45%;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background-color: hsl(var(--background));
  border-radius: 0.5rem;
}

.preview-pane :deep(.pdf-preview-wrapper) {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.preview-pane :deep(.pdf-preview-container) {
  flex: 1;
  min-height: 0;
}

.no-preview {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  color: hsl(var(--muted-foreground));
  background-color: hsl(var(--muted) / 0.3);
  border-radius: 0.5rem;
  font-size: 0.875rem;
}

/* ---- Form Pane ---- */
.form-pane {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.875rem;
  padding: 1rem;
  overflow-y: auto;
  background-color: hsl(var(--background));
  border: 1px solid hsl(var(--border));
  border-radius: 0.5rem;
}

/* ---- Section Groups ---- */
.form-section {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
  padding: 0.75rem;
  background-color: hsl(var(--muted) / 0.25);
  border-radius: 0.5rem;
  border: 1px solid hsl(var(--border) / 0.4);
}

.section-header {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: hsl(var(--foreground));
}

.section-icon {
  width: 1rem;
  height: 1rem;
  color: hsl(var(--muted-foreground));
}

/* ---- Doc Info Card ---- */
.doc-info {
  padding: 0.75rem;
  background-color: hsl(var(--muted) / 0.3);
  border: 1px solid hsl(var(--border));
  border-radius: 0.5rem;
}

.doc-filename {
  font-size: 0.8125rem;
  font-weight: 500;
  margin: 0 0 0.375rem 0;
  font-family: monospace;
  word-break: break-all;
}

.doc-meta {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  flex-wrap: wrap;
}

.doc-meta-item {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.6875rem;
  color: hsl(var(--muted-foreground));
}

.doc-meta-sep {
  color: hsl(var(--muted-foreground) / 0.5);
  font-size: 0.6875rem;
}

/* ---- Status ---- */
.status-bar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 0.75rem;
  border-radius: 0.5rem;
  font-size: 0.8125rem;
}

.status-saving {
  background-color: hsl(var(--muted));
  color: hsl(var(--primary));
}

.status-success {
  background-color: hsl(var(--success) / 0.1);
  color: hsl(var(--success));
}

.status-error {
  background-color: hsl(var(--destructive) / 0.1);
  color: hsl(var(--destructive));
}

/* ---- Form Fields ---- */
.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.625rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.form-label {
  font-size: 0.875rem;
  font-weight: 500;
}

.select-input {
  width: 100%;
  padding: 0.5rem 0.625rem;
  border: 1px solid hsl(var(--border));
  border-radius: 0.375rem;
  background-color: hsl(var(--background));
  color: hsl(var(--foreground));
  font-size: 0.875rem;
  outline: none;
  transition: border-color 0.15s;
}
.select-input:focus {
  border-color: hsl(var(--ring));
  box-shadow: 0 0 0 2px hsl(var(--ring) / 0.15);
}

.select-with-add {
  display: flex;
  gap: 0.25rem;
  align-items: stretch;
}
.select-with-add .select-input {
  flex: 1;
}
.btn-add {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.25rem;
  border: 1px solid hsl(var(--border));
  border-radius: 0.375rem;
  background: hsl(var(--secondary));
  color: hsl(var(--secondary-foreground));
  cursor: pointer;
  transition: all 0.15s;
  flex-shrink: 0;
}
.btn-add:hover:not(:disabled) {
  background: hsl(var(--accent));
  color: hsl(var(--accent-foreground));
  border-color: hsl(var(--ring));
}
.btn-add:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.textarea {
  width: 100%;
  padding: 0.5rem 0.625rem;
  border: 1px solid hsl(var(--border));
  border-radius: 0.375rem;
  background-color: hsl(var(--background));
  font-size: 0.875rem;
  resize: vertical;
  outline: none;
  transition: border-color 0.15s;
}
.textarea:focus {
  border-color: hsl(var(--ring));
  box-shadow: 0 0 0 2px hsl(var(--ring) / 0.15);
}

/* ---- Pill Visibility ---- */
.pill-group {
  display: flex;
  gap: 0.375rem;
  flex-wrap: wrap;
}

.pill {
  display: inline-flex;
  align-items: center;
  gap: 0.3125rem;
  padding: 0.375rem 0.625rem;
  border: 1px solid hsl(var(--border));
  border-radius: 9999px;
  background-color: hsl(var(--background));
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}
.pill:hover:not(:disabled) {
  border-color: hsl(var(--primary) / 0.3);
  color: hsl(var(--foreground));
}
.pill:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pill-active {
  background-color: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
  border-color: hsl(var(--primary));
}
.pill-active:hover:not(:disabled) {
  background-color: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.8125rem;
  cursor: pointer;
}

/* ---- Footer ---- */
.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding-top: 0.625rem;
  border-top: 1px solid hsl(var(--border));
  margin-top: auto;
}
</style>
