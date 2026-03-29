<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { X, Save, Loader2, CheckCircle2, AlertCircle } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useDocumentStore, type Document } from '@/stores/documents'

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

const isOpen = computed({
  get: () => props.open,
  set: (value) => emit('update:open', value)
})

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
      category_id: categoryId.value || undefined, // undefined to avoid sending null if not changed (though here we want explicit null support if API allows, but let's stick to partial)
      file_type_id: fileTypeId.value || undefined,
      folder_id: folderId.value, // Allow moving to root (null)
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
    saveError.value = error.response?.data?.detail || error.message || 'Save failed'
  } finally {
    isSaving.value = false
  }
}

function handleClose() {
  saveError.value = null
  saveSuccess.value = false
  isOpen.value = false
}
</script>

<template>
  <div v-if="isOpen" class="modal-overlay" @click.self="handleClose">
    <div class="modal-content">
      <div class="modal-header">
        <h2 class="modal-title">Edit Document</h2>
        <button class="close-btn" @click="handleClose">
          <X class="h-4 w-4" />
        </button>
      </div>

      <div class="modal-body">
        <div class="doc-info">
          <p class="filename">{{ document?.filename }}</p>
        </div>

        <div v-if="isSaving || saveSuccess || saveError" class="save-status">
          <div v-if="isSaving" class="saving">
            <Loader2 class="h-4 w-4 animate-spin" />
            <span>Saving...</span>
          </div>
          <div v-else-if="saveSuccess" class="success">
            <CheckCircle2 class="h-4 w-4" />
            <span>Saved successfully!</span>
          </div>
          <div v-else-if="saveError" class="error">
            <AlertCircle class="h-4 w-4" />
            <span>{{ saveError }}</span>
          </div>
        </div>

        <div class="form-fields">
          <div class="form-group">
            <label for="edit-title" class="form-label">Title</label>
            <Input id="edit-title" v-model="title" placeholder="Document title" :disabled="isSaving" />
          </div>

          <div class="form-grid">
            <div class="form-group">
              <label class="form-label">Category</label>
              <select v-model="categoryId" class="select-input" :disabled="isSaving">
                <option :value="null">No Category</option>
                <option v-for="cat in docStore.categories" :key="cat.id" :value="cat.id">
                  {{ cat.name }}
                </option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">File Type</label>
              <select v-model="fileTypeId" class="select-input" :disabled="isSaving">
                <option :value="null">No Type</option>
                <option v-for="type in docStore.fileTypes" :key="type.id" :value="type.id">
                  {{ type.name }}
                </option>
              </select>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">Folder</label>
            <select v-model="folderId" class="select-input" :disabled="isSaving">
              <option :value="null">Root Directory</option>
              <option v-for="f in docStore.folders" :key="f.id" :value="f.id">
                {{ f.name }}
              </option>
            </select>
          </div>

          <div class="form-group">
            <label for="edit-tags" class="form-label">Tags (comma-separated)</label>
            <Input id="edit-tags" v-model="tags" placeholder="tag1, tag2, tag3" :disabled="isSaving" />
          </div>

          <div class="form-group">
            <label for="edit-notes" class="form-label">Notes</label>
            <textarea
              id="edit-notes"
              v-model="notes"
              class="textarea"
              placeholder="Optional notes..."
              :disabled="isSaving"
              rows="3"
            />
          </div>

          <div class="form-group">
            <label class="form-label">Visibility</label>
            <div class="checkbox-group">
              <label class="checkbox-label">
                <input type="checkbox" v-model="isPrivate" :disabled="isSaving || isPublic || isPublicEdit" />
                Private
              </label>
              <label class="checkbox-label">
                <input type="checkbox" v-model="isPublic" :disabled="isSaving || isPrivate || isPublicEdit" />
                Public (View)
              </label>
              <label class="checkbox-label">
                <input type="checkbox" v-model="isPublicEdit" :disabled="isSaving || isPrivate || isPublic" />
                Public (Edit)
              </label>
            </div>
          </div>

          <div class="form-group">
            <label class="checkbox-label">
              <input type="checkbox" v-model="isReadOnly" :disabled="isSaving" />
              Read-only
            </label>
          </div>
        </div>
      </div>

      <div class="modal-footer">
        <Button variant="outline" @click="handleClose" :disabled="isSaving">Cancel</Button>
        <Button @click="handleSave" :disabled="isSaving">
          <Save class="h-4 w-4 mr-2" />
          {{ isSaving ? 'Saving...' : 'Save Changes' }}
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

.doc-info {
  padding: 0.75rem;
  background-color: hsl(var(--muted));
  border-radius: 0.375rem;
}

.filename {
  font-size: 0.875rem;
  color: hsl(var(--muted-foreground));
  margin: 0;
  font-family: monospace;
  word-break: break-all;
}

.save-status {
  padding: 0.75rem;
  border-radius: 0.375rem;
  font-size: 0.875rem;
}

.saving {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: hsl(var(--primary));
}

.success {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: hsl(var(--success));
}

.error {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: hsl(var(--destructive));
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
</style>
