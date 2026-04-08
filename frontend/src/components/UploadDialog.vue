<script setup lang="ts">
import { ref, computed } from 'vue'
import { X, Upload, Loader2, CheckCircle2, AlertCircle, FileText } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useDocumentStore } from '@/stores/documents'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()

const props = defineProps<{
  open: boolean
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

const isOpen = computed({
  get: () => props.open,
  set: (value) => emit('update:open', value)
})

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
    } else {
      uploadError.value = t('upload.pdf_only')
    }
  }
}

function removeFile(index: number) {
  selectedFiles.value.splice(index, 1)
  if (selectedFiles.value.length === 0) {
    title.value = ''
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
      // For batch uploads, use filename as title if only one field, otherwise use per-file name
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
}

function handleClose() {
  resetForm()
  isOpen.value = false
}
</script>

<template>
  <div v-if="isOpen" class="modal-overlay" @click.self="handleClose">
    <div class="modal-content">
      <div class="modal-header">
        <h2 class="modal-title">{{ t('upload.title') }}</h2>
        <button class="close-btn" @click="handleClose">
          <X class="h-4 w-4" />
        </button>
      </div>

      <div class="modal-body">
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
            <Upload class="h-8 w-8" />
            <span v-if="selectedFiles.length > 0" class="file-name">
              {{ selectedFiles.length }} {{ t('upload.files_selected') }}
            </span>
            <span v-else>
              <span class="drop-text">{{ t('upload.drop_text') }}</span>
            </span>
          </label>
        </div>

        <!-- File list for batch uploads -->
        <div v-if="selectedFiles.length > 1" class="file-list">
          <div v-for="(file, index) in selectedFiles" :key="index" class="file-item">
            <FileText class="h-4 w-4" />
            <span class="file-item-name">{{ file.name }}</span>
            <button class="file-item-remove" @click="removeFile(index)" type="button">
              <X class="h-3 w-3" />
            </button>
          </div>
        </div>

        <div v-if="isUploading || uploadSuccess || uploadError" class="upload-status">
          <div v-if="isUploading" class="upload-progress">
            <Loader2 class="h-4 w-4 animate-spin" />
            <span>{{ t('upload.uploading') }} {{ uploadProgress }}%</span>
          </div>
          <div v-else-if="uploadSuccess" class="upload-success">
            <CheckCircle2 class="h-4 w-4" />
            <span>{{ t('upload.upload_success') }}</span>
          </div>
          <div v-else-if="uploadError" class="upload-error">
            <AlertCircle class="h-4 w-4" />
            <span>{{ uploadError }}</span>
          </div>
        </div>

        <div class="form-fields">
          <div class="form-group">
            <label for="title" class="form-label">{{ t('upload.title_label') }}</label>
            <Input id="title" v-model="title" :placeholder="t('upload.title_placeholder')" :disabled="isUploading" />
          </div>

          <div class="form-grid">
            <div class="form-group">
              <label class="form-label">{{ t('upload.category_label') }}</label>
              <select v-model="categoryId" class="select-input" :disabled="isUploading">
                <option :value="null">{{ t('upload.no_category') }}</option>
                <option v-for="cat in docStore.categories" :key="cat.id" :value="cat.id">
                  {{ cat.name }}
                </option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">{{ t('upload.file_type_label') }}</label>
              <select v-model="fileTypeId" class="select-input" :disabled="isUploading">
                <option :value="null">{{ t('upload.no_type') }}</option>
                <option v-for="type in docStore.fileTypes" :key="type.id" :value="type.id">
                  {{ type.name }}
                </option>
              </select>
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
            <Input id="tags" v-model="tags" :placeholder="t('upload.tags_placeholder')" :disabled="isUploading" />
          </div>

          <div class="form-group">
            <label for="notes" class="form-label">{{ t('upload.notes_label') }}</label>
            <textarea
              id="notes"
              v-model="notes"
              class="textarea"
              :placeholder="t('upload.notes_placeholder')"
              :disabled="isUploading"
              rows="3"
            />
          </div>

          <div class="form-group">
            <label class="form-label">{{ t('upload.visibility') }}</label>
            <div class="checkbox-group">
              <label class="checkbox-label">
                <input type="checkbox" v-model="isPrivate" :disabled="isUploading || isPublic || isPublicEdit" />
                {{ t('upload.private') }}
              </label>
              <label class="checkbox-label">
                <input type="checkbox" v-model="isPublic" :disabled="isUploading || isPrivate || isPublicEdit" />
                {{ t('upload.public_view') }}
              </label>
              <label class="checkbox-label">
                <input type="checkbox" v-model="isPublicEdit" :disabled="isUploading || isPrivate || isPublic" />
                {{ t('upload.public_edit') }}
              </label>
            </div>
          </div>

          <div class="form-group">
            <label class="checkbox-label">
              <input type="checkbox" v-model="useOcr" :disabled="isUploading" />
              {{ t('upload.ocr_checkbox') }}
            </label>
          </div>
        </div>
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
</template>

<style scoped>
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

.modal-content {
  background-color: hsl(var(--background));
  border-radius: 0.5rem;
  width: 100%;
  max-width: 550px;
  max-height: 95vh;
  overflow-y: auto;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid hsl(var(--border));
}

.modal-title {
  font-size: 1rem;
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
}

.modal-body {
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.drop-zone {
  border: 2px dashed hsl(var(--border));
  border-radius: 0.5rem;
  padding: 1.5rem;
  text-align: center;
  cursor: pointer;
}

.drop-zone.has-file {
  border-color: hsl(var(--primary));
  background-color: hsl(var(--primary) / 0.05);
}

.file-input {
  display: none;
}

.drop-zone-label {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  color: hsl(var(--muted-foreground));
}

.file-name {
  color: hsl(var(--foreground));
  font-weight: 500;
  word-break: break-all;
}

.form-fields {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.form-label {
  font-size: 0.875rem;
  font-weight: 500;
}

.select-input {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid hsl(var(--border));
  border-radius: 0.375rem;
  background-color: hsl(var(--background));
  color: hsl(var(--foreground));
  font-size: 0.875rem;
}

.textarea {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid hsl(var(--border));
  border-radius: 0.375rem;
  background-color: hsl(var(--background));
  font-size: 0.875rem;
  resize: vertical;
}

.checkbox-group {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.875rem;
  cursor: pointer;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 1rem 1.25rem;
  border-top: 1px solid hsl(var(--border));
}

.upload-status {
  padding: 0.75rem;
  border-radius: 0.375rem;
  background-color: hsl(var(--muted));
  font-size: 0.875rem;
}

.upload-progress, .upload-success, .upload-error {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.upload-success { color: hsl(var(--success)); }
.upload-error { color: hsl(var(--destructive)); }

.file-list {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  max-height: 150px;
  overflow-y: auto;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 0.5rem;
  background-color: hsl(var(--muted));
  border-radius: 0.25rem;
  font-size: 0.8125rem;
}

.file-item-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
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
}

.file-item-remove:hover {
  background-color: hsl(var(--destructive) / 0.1);
  color: hsl(var(--destructive));
}
</style>
