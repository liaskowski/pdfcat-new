<script setup lang="ts">
import { ref, computed } from 'vue'
import { X, Upload, Loader2, CheckCircle2, AlertCircle } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useDocumentStore } from '@/stores/documents'

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

const selectedFile = ref<File | null>(null)
const isUploading = ref(false)
const uploadProgress = ref(0)
const uploadError = ref<string | null>(null)
const uploadSuccess = ref(false)

const isOpen = computed({
  get: () => props.open,
  set: (value) => emit('update:open', value)
})

function handleFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files && input.files.length > 0) {
    selectedFile.value = input.files[0]
    if (!title.value) {
      title.value = selectedFile.value.name.replace('.pdf', '')
    }
    uploadError.value = null
    uploadSuccess.value = false
  }
}

function handleDrop(event: DragEvent) {
  event.preventDefault()
  if (event.dataTransfer?.files && event.dataTransfer.files.length > 0) {
    const file = event.dataTransfer.files[0]
    if (file.name.endsWith('.pdf')) {
      selectedFile.value = file
      if (!title.value) {
        title.value = file.name.replace('.pdf', '')
      }
      uploadError.value = null
      uploadSuccess.value = false
    } else {
      uploadError.value = 'Please upload a PDF file'
    }
  }
}

function handleDragOver(event: DragEvent) {
  event.preventDefault()
}

async function handleUpload() {
  if (!selectedFile.value) {
    uploadError.value = 'Please select a file'
    return
  }

  isUploading.value = true
  uploadProgress.value = 0
  uploadError.value = null
  uploadSuccess.value = false

  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    formData.append('title', title.value || selectedFile.value.name)
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

    // Simulate progress
    const progressInterval = setInterval(() => {
      uploadProgress.value = Math.min(uploadProgress.value + 10, 90)
    }, 200)

    const data = await docStore.uploadDocument(formData)

    clearInterval(progressInterval)
    uploadProgress.value = 100
    uploadSuccess.value = true
    
    setTimeout(() => {
      emit('uploaded', data)
      resetForm()
      isOpen.value = false
    }, 1000)

  } catch (error: any) {
    uploadError.value = error.response?.data?.detail || error.message || 'Upload failed'
    uploadProgress.value = 0
  } finally {
    isUploading.value = false
  }
}

function resetForm() {
  selectedFile.value = null
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
        <h2 class="modal-title">Upload PDF</h2>
        <button class="close-btn" @click="handleClose">
          <X class="h-4 w-4" />
        </button>
      </div>

      <div class="modal-body">
        <div
          class="drop-zone"
          :class="{ 'has-file': selectedFile }"
          @drop="handleDrop"
          @dragover="handleDragOver"
        >
          <input
            type="file"
            id="file-input"
            class="file-input"
            accept=".pdf"
            @change="handleFileChange"
          />
          <label for="file-input" class="drop-zone-label">
            <Upload class="h-8 w-8" />
            <span v-if="selectedFile" class="file-name">{{ selectedFile.name }}</span>
            <span v-else>
              <span class="drop-text">Drop your PDF here or click to browse</span>
            </span>
          </label>
        </div>

        <div v-if="isUploading || uploadSuccess || uploadError" class="upload-status">
          <div v-if="isUploading" class="upload-progress">
            <Loader2 class="h-4 w-4 animate-spin" />
            <span>Uploading... {{ uploadProgress }}%</span>
          </div>
          <div v-else-if="uploadSuccess" class="upload-success">
            <CheckCircle2 class="h-4 w-4" />
            <span>Upload successful!</span>
          </div>
          <div v-else-if="uploadError" class="upload-error">
            <AlertCircle class="h-4 w-4" />
            <span>{{ uploadError }}</span>
          </div>
        </div>

        <div class="form-fields">
          <div class="form-group">
            <label for="title" class="form-label">Title</label>
            <Input id="title" v-model="title" placeholder="Document title" :disabled="isUploading" />
          </div>

          <div class="form-grid">
            <div class="form-group">
              <label class="form-label">Category</label>
              <select v-model="categoryId" class="select-input" :disabled="isUploading">
                <option :value="null">No Category</option>
                <option v-for="cat in docStore.categories" :key="cat.id" :value="cat.id">
                  {{ cat.name }}
                </option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">File Type</label>
              <select v-model="fileTypeId" class="select-input" :disabled="isUploading">
                <option :value="null">No Type</option>
                <option v-for="type in docStore.fileTypes" :key="type.id" :value="type.id">
                  {{ type.name }}
                </option>
              </select>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">Folder</label>
            <select v-model="folderId" class="select-input" :disabled="isUploading">
              <option :value="null">Root Directory</option>
              <option v-for="f in docStore.folders" :key="f.id" :value="f.id">
                {{ f.name }}
              </option>
            </select>
          </div>

          <div class="form-group">
            <label for="tags" class="form-label">Tags (comma-separated)</label>
            <Input id="tags" v-model="tags" placeholder="tag1, tag2, tag3" :disabled="isUploading" />
          </div>

          <div class="form-group">
            <label for="notes" class="form-label">Notes</label>
            <textarea
              id="notes"
              v-model="notes"
              class="textarea"
              placeholder="Optional notes..."
              :disabled="isUploading"
              rows="3"
            />
          </div>

          <div class="form-group">
            <label class="form-label">Visibility</label>
            <div class="checkbox-group">
              <label class="checkbox-label">
                <input type="checkbox" v-model="isPrivate" :disabled="isUploading || isPublic || isPublicEdit" />
                Private
              </label>
              <label class="checkbox-label">
                <input type="checkbox" v-model="isPublic" :disabled="isUploading || isPrivate || isPublicEdit" />
                Public (View)
              </label>
              <label class="checkbox-label">
                <input type="checkbox" v-model="isPublicEdit" :disabled="isUploading || isPrivate || isPublic" />
                Public (Edit)
              </label>
            </div>
          </div>

          <div class="form-group">
            <label class="checkbox-label">
              <input type="checkbox" v-model="useOcr" :disabled="isUploading" />
              Use OCR for text extraction
            </label>
          </div>
        </div>
      </div>

      <div class="modal-footer">
        <Button variant="outline" @click="handleClose" :disabled="isUploading">Cancel</Button>
        <Button @click="handleUpload" :disabled="!selectedFile || isUploading">
          <Upload class="h-4 w-4 mr-2" />
          {{ isUploading ? 'Uploading...' : 'Upload' }}
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
</style>
