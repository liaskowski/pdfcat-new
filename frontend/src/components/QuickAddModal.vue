<script setup lang="ts">
import { ref } from 'vue'
import { X, Plus, Loader2 } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useDocumentStore } from '@/stores/documents'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()

const props = defineProps<{
  open: boolean
  title: string
  placeholder?: string
}>()

const emit = defineEmits<{
  'update:open': [open: boolean]
  created: [item: { id: number; name: string }]
}>()

const docStore = useDocumentStore()

const name = ref('')
const loading = ref(false)
const error = ref('')

async function handleCreate() {
  const val = name.value.trim()
  if (!val) return
  loading.value = true
  error.value = ''
  try {
    let result: { id: number; name: string }
    // Determine which API to call based on the title
    if (props.title.toLowerCase().includes('categor')) {
      result = await docStore.createCategory(val)
    } else {
      result = await docStore.createFileType(val)
    }
    emit('created', result)
    name.value = ''
    emit('update:open', false)
  } catch (e: any) {
    error.value = e.response?.data?.detail || 'Failed to create'
  } finally {
    loading.value = false
  }
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter') handleCreate()
  if (e.key === 'Escape') emit('update:open', false)
}

function handleClose() {
  name.value = ''
  error.value = ''
  emit('update:open', false)
}
</script>

<template>
  <Transition name="quick-modal">
    <div v-if="open" class="quick-overlay" @click.self="handleClose">
      <div class="quick-card" @click.stop>
        <div class="quick-header">
          <span class="quick-title">{{ title }}</span>
          <button class="quick-close" @click="handleClose">
            <X class="h-4 w-4" />
          </button>
        </div>
        <div class="quick-body">
          <Input
            v-model="name"
            :placeholder="placeholder || 'Name'"
            :disabled="loading"
            @keydown="handleKeydown"
            autofocus
          />
          <p v-if="error" class="quick-error">{{ error }}</p>
        </div>
        <div class="quick-footer">
          <Button variant="outline" size="sm" @click="handleClose" :disabled="loading">
            {{ t('common.cancel') }}
          </Button>
          <Button size="sm" @click="handleCreate" :disabled="!name.trim() || loading">
            <Loader2 v-if="loading" class="h-4 w-4 animate-spin mr-1" />
            <Plus v-else class="h-4 w-4 mr-1" />
            {{ t('common.create') }}
          </Button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.quick-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 60;
}
.quick-card {
  background: hsl(var(--background));
  border: 1px solid hsl(var(--border));
  border-radius: calc(var(--radius) + 2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
  width: 320px;
  max-width: 90vw;
}
.quick-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid hsl(var(--border));
}
.quick-title {
  font-size: 0.9375rem;
  font-weight: 600;
}
.quick-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.75rem;
  height: 1.75rem;
  border: none;
  background: transparent;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  border-radius: 4px;
}
.quick-close:hover {
  background: hsl(var(--accent));
  color: hsl(var(--accent-foreground));
}
.quick-body {
  padding: 1rem;
}
.quick-error {
  margin: 0.5rem 0 0;
  font-size: 0.8125rem;
  color: hsl(var(--destructive));
}
.quick-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border-top: 1px solid hsl(var(--border));
}

/* Transition */
.quick-modal-enter-active { transition: opacity 0.15s ease; }
.quick-modal-leave-active { transition: opacity 0.1s ease; }
.quick-modal-enter-from, .quick-modal-leave-to { opacity: 0; }
.quick-modal-enter-active .quick-card { transition: transform 0.15s ease; }
.quick-modal-leave-active .quick-card { transition: transform 0.1s ease; }
.quick-modal-enter-from .quick-card { transform: scale(0.95); }
.quick-modal-leave-to .quick-card { transform: scale(0.95); }
</style>
