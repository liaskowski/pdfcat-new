<script setup lang="ts">
import { ref, computed } from 'vue'
import { X, FolderPlus } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useDocumentStore } from '@/stores/documents'

const props = defineProps<{
  open: boolean
  parentId?: number | null
}>()

const emit = defineEmits<{
  'update:open': [open: boolean]
  created: []
}>()

const docStore = useDocumentStore()
const folderName = ref('')
const isPublic = ref(false)
const isCreating = ref(false)
const error = ref<string | null>(null)

const isOpen = computed({
  get: () => props.open,
  set: (value) => emit('update:open', value)
})

async function handleCreate() {
  if (!folderName.value.trim()) return

  isCreating.value = true
  error.value = null

  try {
    await docStore.createFolder(folderName.value, props.parentId, isPublic.value)
    folderName.value = ''
    isPublic.value = false
    emit('created')
    isOpen.value = false
  } catch (e: any) {
    error.value = 'Failed to create folder'
  } finally {
    isCreating.value = false
  }
}

function handleClose() {
  isOpen.value = false
  folderName.value = ''
  error.value = null
}
</script>

<template>
  <div v-if="isOpen" class="modal-overlay" @click.self="handleClose">
    <div class="modal-content">
      <div class="modal-header">
        <h2 class="modal-title">New Folder</h2>
        <button class="close-btn" @click="handleClose">
          <X class="h-4 w-4" />
        </button>
      </div>

      <div class="modal-body">
        <div class="form-group">
          <label class="form-label">Folder Name</label>
          <Input 
            v-model="folderName" 
            placeholder="Enter folder name" 
            @keydown.enter="handleCreate"
            autoFocus
          />
        </div>

        <div class="form-group">
          <label class="checkbox-label">
            <input type="checkbox" v-model="isPublic" />
            Public (Shared)
          </label>
        </div>

        <p v-if="error" class="error-text">{{ error }}</p>
      </div>

      <div class="modal-footer">
        <Button variant="outline" @click="handleClose">Cancel</Button>
        <Button @click="handleCreate" :disabled="!folderName.trim() || isCreating">
          <FolderPlus class="h-4 w-4 mr-2" />
          Create
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
  max-width: 400px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem;
  border-bottom: 1px solid hsl(var(--border));
}

.modal-title { font-size: 1rem; font-weight: 600; margin: 0; }

.close-btn {
  border: none;
  background: transparent;
  cursor: pointer;
  color: hsl(var(--muted-foreground));
}

.modal-body { padding: 1.25rem; display: flex; flex-direction: column; gap: 1rem; }

.form-group { display: flex; flex-direction: column; gap: 0.5rem; }
.form-label { font-size: 0.875rem; font-weight: 500; }

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  cursor: pointer;
}

.error-text { color: hsl(var(--destructive)); font-size: 0.875rem; margin: 0; }

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 1rem;
  border-top: 1px solid hsl(var(--border));
}
</style>
