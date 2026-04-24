<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { X, Upload, Loader2, CheckCircle2, AlertCircle, FileText, Lock, Globe, PenSquare, Shield, Plus } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useDocumentStore } from '@/stores/documents'
import { useI18n } from '@/composables/useI18n'
import PdfPreview from '@/components/PdfPreview.vue'
import TagInput from '@/components/TagInput.vue'
import QuickAddModal from '@/components/QuickAddModal.vue'

const { t } = useI18n()

const props = defineProps<{
  open: boolean
  files?: File[]
}>()

const emit = defineEmits<{
  'update:open': [open: boolean]
  uploaded: [document: any]
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
const useOcr = ref(true)

const selectedFiles = ref<File[]>([])
const isUploading = ref(false)
const uploadProgress = ref(0)
const uploadError = ref<string | null>(null)
const uploadSuccess = ref(false)
const uploadResults = ref<{ name: string; success: boolean; error?: string }[]>([])

// Preview URL for local file
const previewUrl = ref<string | null>(null)

const isOpen = computed({
  get: () => props.open,
  set: (value) => emit('update:open', value)
})

// Clean up blob URL
watch(previewUrl, (_newUrl, oldUrl) => {
  if (oldUrl) {
    URL.revokeObjectURL(oldUrl)
  }
})

// Accept incoming files from parent (drag-and-drop from FileGrid)
watch(() => props.files, (incoming) => {
  if (incoming && incoming.length > 0) {
    selectedFiles.value = incoming
    if (incoming.length === 1 && !title.value) {
      title.value = incoming[0].name.replace('.pdf', '')
    }
    uploadError.value = null
    uploadSuccess.value = false
    uploadResults.value = []
    previewUrl.value = URL.createObjectURL(incoming[0])
  }
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

// Total file size
const totalFileSize = computed(() => {
  const total = selectedFiles.value.reduce((sum, f) => sum + f.size, 0)
  if (total === 0) return ''
  return formatSize(total)
})

// Quick-add modals
const quickAddCategory = ref(false)
const quickAddType = ref(false)

function onCategoryCreated(item: { id: number; name: string }) {
  categoryId.value = item.id
}
function onTypeCreated(item: { id: number; name: string }) {
  fileTypeId.value = item.id
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function handleFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files && input.files.length > 0) {
    selectedFiles.value = Array.from(input.files)
    if (!title.value && selectedFiles.value.length === 1) {
      title.value = selectedFiles.value[0].name.replace('.pdf', '')
    }
    uploadError.value = null
    uploadSuccess.value = false
    uploadResults.value = []

    if (selectedFiles.value[0]) {
      previewUrl.value = URL.createObjectURL(selectedFiles.value[0])
    }
  }
}

function handleDrop(event: DragEvent) {
  event.preventDefault()
  if (event.dataTransfer?.files && event.dataTransfer.files.length > 0) {
    const files = Array.from(event.dataTransfer.files).filter(f => f.name.endsWith('.pdf'))
    if (files.length > 0) {
      selectedFiles.value = files
      if (!title.value && files.length === 1) {
        title.value = files[0].name.replace('.pdf', '')
      }
      uploadError.value = null
      uploadSuccess.value = false
      uploadResults.value = []

      previewUrl.value = URL.createObjectURL(files[0])
    } else {
      uploadError.value = t('upload.pdf_only')
    }
  }
}

function removeFile(index: number) {
  selectedFiles.value.splice(index, 1)
  if (selectedFiles.value.length === 0) {
    title.value = ''
    previewUrl.value = null
  } else if (index === 0) {
    previewUrl.value = URL.createObjectURL(selectedFiles.value[0])
  }
}

function handleDragOver(event: DragEvent) {
  event.preventDefault()
}

async function handleUpload() {
  if (selectedFiles.value.length === 0) {
    uploadError.value = t('upload.no_file')
    return
  }

  isUploading.value = true
  uploadProgress.value = 0
  uploadError.value = null
  uploadSuccess.value = false
  uploadResults.value = []

  const isBatch = selectedFiles.value.length > 1

  for (let i = 0; i < selectedFiles.value.length; i++) {
    const file = selectedFiles.value[i]
    uploadProgress.value = Math.round(((i + 1) / selectedFiles.value.length) * 100)

    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('title', isBatch ? file.name.replace(/\.pdf$/i, '') : (title.value || file.name))
      if (notes.value) formData.append('notes', notes.value)
      if (tags.value) formData.append('tags', tags.value)
      if (categoryId.value) formData.append('category_id', categoryId.value.toString())
      if (fileTypeId.value) formData.append('file_type_id', fileTypeId.value.toString())
      if (folderId.value) formData.append('folder_id', folderId.value.toString())

      formData.append('is_private', isPrivate.value.toString())
      formData.append('is_public', isPublic.value.toString())
      formData.append('is_public_edit', isPublicEdit.value.toString())
      formData.append('is_read_only', isReadOnly.value.toString())
      formData.append('use_ocr', useOcr.value.toString())

      await docStore.uploadDocument(formData)
      uploadResults.value.push({ name: file.name, success: true })
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || error.message || t('upload.upload_failed')
      uploadResults.value.push({ name: file.name, success: false, error: errorMsg })
      console.error(`Failed to upload ${file.name}:`, error)
    }
  }

  const successCount = uploadResults.value.filter(r => r.success).length
  uploadSuccess.value = successCount > 0

  if (successCount === 0) {
    uploadError.value = t('upload.all_failed')
  }

  setTimeout(() => {
    emit('uploaded', null)
    resetForm()
    isOpen.value = false
  }, 1500)
}

function resetForm() {
  selectedFiles.value = []
  title.value = ''
  notes.value = ''
  tags.value = ''
  categoryId.value = null
  fileTypeId.value = null
  folderId.value = null
  isPrivate.value = false
  isPublic.value = false
  isPublicEdit.value = false
  isReadOnly.value = false
  useOcr.value = true
  uploadProgress.value = 0
  uploadError.value = null
  uploadSuccess.value = false
  previewUrl.value = null
}

function handleClose() {
  resetForm()
  isOpen.value = false
}
</script>

<template>
  <Transition name="modal">
    <div v-if="isOpen" class="modal-overlay" @click.self="handleClose">
      <div class="modal-content modal-content-wide" @click.stop>
        <div class="modal-header">
          <h2 class="modal-title">{{ t('upload.title') }}</h2>
          <button class="close-btn" @click="handleClose" :disabled="isUploading">
            <X class="h-4 w-4" />
          </button>
        </div>

        <div class="modal-body modal-body-split">
          <!-- Left: PDF Preview -->
          <div class="preview-pane">
            <PdfPreview v-if="previewUrl" :src="previewUrl" :key="previewUrl" />
            <div v-else class="no-preview">
              <div class="drop-hint">
                <Upload class="h-12 w-12 opacity-40" />
                <p>{{ t('upload.drop_text') }}</p>
              </div>
            </div>
          </div>

          <!-- Right: Form -->
          <div class="form-pane">
            <!-- Drop Zone -->
            <div class="form-section">
              <div class="section-header">
                <FileText class="section-icon" />
                <span class="section-title">{{ t('upload.file_label') || 'File' }}</span>
              </div>
              <div
                class="drop-zone"
                :class="{ 'has-file': selectedFiles.length > 0 }"
                @drop="handleDrop"
                @dragover="handleDragOver"
              >
                <input
                  type="file"
                  id="file-input"
                  class="file-input"
                  accept=".pdf"
                  multiple
                  @change="handleFileChange"
                />
                <label for="file-input" class="drop-zone-label">
                  <Upload class="h-5 w-5" />
                  <span v-if="selectedFiles.length > 0" class="file-count">
                    {{ selectedFiles.length }} {{ t('upload.files_selected') }}
                    <span v-if="totalFileSize" class="file-size">&middot; {{ totalFileSize }}</span>
                  </span>
                  <span v-else class="drop-text">
                    {{ t('upload.drop_text') }}
                  </span>
                </label>
              </div>

              <!-- File list for batch uploads -->
              <div v-if="selectedFiles.length > 1" class="file-list">
                <div v-for="(file, index) in selectedFiles" :key="index" class="file-item">
                  <FileText class="h-4 w-4 shrink-0" />
                  <span class="file-item-name">{{ file.name }}</span>
                  <span class="file-item-size">{{ formatSize(file.size) }}</span>
                  <button class="file-item-remove" @click="removeFile(index)" type="button" :disabled="isUploading">
                    <X class="h-3 w-3" />
                  </button>
                </div>
              </div>

              <div class="form-group">
                <label for="title" class="form-label">{{ t('upload.title_label') }}</label>
                <Input id="title" v-model="title" :placeholder="t('upload.title_placeholder')" :disabled="isUploading" />
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
                    <select v-model="categoryId" class="select-input" :disabled="isUploading">
                      <option :value="null">{{ t('upload.no_category') }}</option>
                      <option v-for="cat in docStore.categories" :key="cat.id" :value="cat.id">
                        {{ cat.name }}
                      </option>
                    </select>
                    <button type="button" class="btn-add" :disabled="isUploading" @click="quickAddCategory = true" title="Add category">
                      <Plus class="h-4 w-4" />
                    </button>
                  </div>
                </div>
                <div class="form-group">
                  <label class="form-label">{{ t('upload.file_type_label') }}</label>
                  <div class="select-with-add">
                    <select v-model="fileTypeId" class="select-input" :disabled="isUploading">
                      <option :value="null">{{ t('upload.no_type') }}</option>
                      <option v-for="type in docStore.fileTypes" :key="type.id" :value="type.id">
                        {{ type.name }}
                      </option>
                    </select>
                    <button type="button" class="btn-add" :disabled="isUploading" @click="quickAddType = true" title="Add file type">
                      <Plus class="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
              <div class="form-group">
                <label class="form-label">{{ t('upload.folder_label') }}</label>
                <select v-model="folderId" class="select-input" :disabled="isUploading">
                  <option :value="null">{{ t('upload.root') }}</option>
                  <option v-for="f in docStore.folders" :key="f.id" :value="f.id">
                    {{ f.name }}
                  </option>
                </select>
              </div>
              <div class="form-group">
                <label for="tags" class="form-label">{{ t('upload.tags_label') }}</label>
                <TagInput v-model="tags" :disabled="isUploading" :placeholder="t('upload.tags_placeholder')" />
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
                  id="notes"
                  v-model="notes"
                  class="textarea"
                  :placeholder="t('upload.notes_placeholder')"
                  :disabled="isUploading"
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

              <!-- Pill-style visibility selector -->
              <div class="pill-group">
                <button
                  type="button"
                  class="pill"
                  :class="{ 'pill-active': visibilityMode === 'private' }"
                  :disabled="isUploading"
                  @click="visibilityMode = 'private'"
                >
                  <Lock class="h-3.5 w-3.5" />
                  <span>{{ t('upload.private') }}</span>
                </button>
                <button
                  type="button"
                  class="pill"
                  :class="{ 'pill-active': visibilityMode === 'public' }"
                  :disabled="isUploading"
                  @click="visibilityMode = 'public'"
                >
                  <Globe class="h-3.5 w-3.5" />
                  <span>{{ t('upload.public_view') }}</span>
                </button>
                <button
                  type="button"
                  class="pill"
                  :class="{ 'pill-active': visibilityMode === 'public_edit' }"
                  :disabled="isUploading"
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
                  :disabled="isUploading"
                  @click="isReadOnly = !isReadOnly"
                >
                  <Shield class="h-3.5 w-3.5" />
                  <span>{{ t('document.is_read_only') }}</span>
                </button>
              </div>

              <label class="checkbox-label">
                <input type="checkbox" v-model="useOcr" :disabled="isUploading" />
                {{ t('upload.ocr_checkbox') }}
              </label>
            </div>

            <!-- Status Bar -->
            <div v-if="isUploading" class="status-bar status-uploading">
              <div class="status-row">
                <Loader2 class="h-4 w-4 animate-spin" />
                <span>{{ t('upload.uploading') }} {{ uploadProgress }}%</span>
              </div>
              <div class="progress-track">
                <div class="progress-fill" :style="{ width: uploadProgress + '%' }"></div>
              </div>
            </div>
            <div v-else-if="uploadSuccess" class="status-bar status-success">
              <CheckCircle2 class="h-4 w-4" />
              <span>{{ t('upload.upload_success') }}</span>
            </div>
            <div v-else-if="uploadError" class="status-bar status-error">
              <AlertCircle class="h-4 w-4 shrink-0" />
              <span>{{ uploadError }}</span>
            </div>

            <div class="modal-footer">
              <Button variant="outline" @click="handleClose" :disabled="isUploading">{{ t('common.cancel') }}</Button>
              <Button @click="handleUpload" :disabled="selectedFiles.length === 0 || isUploading">
                <Upload class="h-4 w-4 mr-2" />
                {{ isUploading ? t('upload.uploading') : t('common.upload') }}
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
}

.drop-hint {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
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

/* ---- Sections ---- */
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
  font-size: 0.8125rem;
  font-weight: 600;
  color: hsl(var(--foreground));
}

.section-icon {
  width: 1rem;
  height: 1rem;
  color: hsl(var(--muted-foreground));
}

.section-title {
  font-size: 0.8125rem;
}

/* ---- Drop Zone ---- */
.drop-zone {
  border: 2px dashed hsl(var(--border));
  border-radius: 0.5rem;
  padding: 1.25rem 1rem;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
}

.drop-zone:hover {
  border-color: hsl(var(--primary) / 0.5);
  background-color: hsl(var(--primary) / 0.02);
}

.drop-zone.has-file {
  border-color: hsl(var(--primary));
  background-color: hsl(var(--primary) / 0.05);
  padding: 0.75rem;
}

.file-input { display: none; }

.drop-zone-label {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.375rem;
  cursor: pointer;
  color: hsl(var(--muted-foreground));
  font-size: 0.875rem;
}

.file-count {
  color: hsl(var(--foreground));
  font-weight: 500;
}

.file-size {
  color: hsl(var(--muted-foreground));
  font-weight: 400;
  font-size: 0.75rem;
}

.drop-text {
  font-size: 0.875rem;
}

/* ---- File List ---- */
.file-list {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  max-height: 120px;
  overflow-y: auto;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 0.5rem;
  background-color: hsl(var(--background));
  border: 1px solid hsl(var(--border));
  border-radius: 0.375rem;
  font-size: 0.75rem;
}

.file-item-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-item-size {
  color: hsl(var(--muted-foreground));
  font-size: 0.6875rem;
  white-space: nowrap;
}

.file-item-remove {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.25rem;
  height: 1.25rem;
  border: none;
  background: transparent;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  border-radius: 0.25rem;
  transition: all 0.15s;
}
.file-item-remove:hover {
  background-color: hsl(var(--destructive) / 0.1);
  color: hsl(var(--destructive));
}

/* ---- Form Fields ---- */
.form-fields {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

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
  padding: 0.5rem;
  border: 1px solid hsl(var(--border));
  border-radius: 0.375rem;
  background-color: hsl(var(--background));
  font-size: 0.8125rem;
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

/* ---- Status Bar ---- */
.status-bar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 0.75rem;
  border-radius: 0.5rem;
  font-size: 0.8125rem;
}

.status-uploading {
  flex-direction: column;
  align-items: stretch;
  gap: 0.375rem;
  background-color: hsl(var(--muted));
  color: hsl(var(--primary));
}

.status-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.progress-track {
  height: 0.375rem;
  background-color: hsl(var(--border));
  border-radius: 9999px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background-color: hsl(var(--primary));
  border-radius: 9999px;
  transition: width 0.3s ease;
}

.status-success {
  background-color: hsl(var(--success) / 0.1);
  color: hsl(var(--success));
}

.status-error {
  background-color: hsl(var(--destructive) / 0.1);
  color: hsl(var(--destructive));
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
