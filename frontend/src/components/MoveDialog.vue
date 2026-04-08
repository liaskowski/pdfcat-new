<script setup lang="ts">
import { ref, computed } from 'vue'
import { X, Folder, Loader2, CheckCircle2, AlertCircle } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { useDocumentStore } from '@/stores/documents'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()

const props = defineProps<{
  open: boolean
  selectedIds: Set<number>
}>()

const emit = defineEmits<{
  'update:open': [value: boolean]
  moved: []
}>()

const docStore = useDocumentStore()
const selectedFolderId = ref<number | null>(null)
const isMoving = ref(false)
const moveError = ref<string | null>(null)
const moveSuccess = ref(false)

const availableFolders = computed(() => docStore.folders)

async function handleMove() {
  moveError.value = null
  moveSuccess.value = false
  isMoving.value = true

  try {
    const ids = Array.from(props.selectedIds)
    await Promise.all(
      ids.map(id => docStore.updateDocument(id, { folder_id: selectedFolderId.value }))
    )
    moveSuccess.value = true
    setTimeout(() => {
      emit('moved')
      emit('update:open', false)
      selectedFolderId.value = null
    }, 800)
  } catch (e: any) {
    moveError.value = e.response?.data?.detail || 'Failed to move documents'
  } finally {
    isMoving.value = false
  }
}

function handleClose() {
  selectedFolderId.value = null
  moveError.value = null
  moveSuccess.value = false
  emit('update:open', false)
}
</script>

<template>
  <div v-if="open" class="modal-overlay" @click.self="handleClose">
    <div class="modal-content">
      <div class="modal-header">
        <h2 class="modal-title">
          <Folder class="h-5 w-5 mr-2" />
          {{ t('move.title') }}
        </h2>
        <button class="close-btn" @click="handleClose">
          <X class="h-4 w-4" />
        </button>
      </div>

      <div class="modal-body">
        <div v-if="moveSuccess" class="upload-success">
          <CheckCircle2 class="h-5 w-5" />
          <span>{{ t('move.success') }}</span>
        </div>

        <div v-else-if="moveError" class="upload-error">
          <AlertCircle class="h-5 w-5" />
          <span>{{ moveError }}</span>
        </div>

        <div v-else>
          <p class="mb-3 text-sm text-muted-foreground">{{ t('move.select_destination') }}</p>
          <select v-model="selectedFolderId" class="select-input">
            <option :value="null">{{ t('move.root') }}</option>
            <option v-for="folder in availableFolders" :key="folder.id" :value="folder.id">
              {{ folder.name }}
            </option>
          </select>
        </div>
      </div>

      <div class="modal-footer">
        <Button variant="outline" @click="handleClose" :disabled="isMoving">
          {{ moveSuccess ? t('move.close') : t('move.cancel') }}
        </Button>
        <Button
          v-if="!moveSuccess"
          @click="handleMove"
          :disabled="isMoving || selectedIds.size === 0"
        >
          <Loader2 v-if="isMoving" class="h-4 w-4 mr-2 animate-spin" />
          <Folder v-else class="h-4 w-4 mr-2" />
          {{ isMoving ? t('move.moving') : t('move.move_btn') }}
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
  max-width: 450px;
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
  display: flex;
  align-items: center;
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

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 1rem 1.25rem;
  border-top: 1px solid hsl(var(--border));
}

.upload-success, .upload-error {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  border-radius: 0.375rem;
  font-size: 0.875rem;
}

.upload-success {
  background-color: hsl(var(--success) / 0.1);
  color: hsl(var(--success));
}

.upload-error {
  background-color: hsl(var(--destructive) / 0.1);
  color: hsl(var(--destructive));
}
</style>
