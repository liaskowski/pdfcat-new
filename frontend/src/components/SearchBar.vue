<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { Search, X, Loader2 } from 'lucide-vue-next'
import { useDocumentStore } from '@/stores/documents'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()

const props = defineProps<{
  modelValue: string
  placeholder?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  search: [query: string]
  clear: []
}>()

const docStore = useDocumentStore()
const localQuery = ref(props.modelValue)
const suggestions = ref<string[]>([])
const showSuggestions = ref(false)
const isLoading = ref(false)
const searchContainerRef = ref<HTMLElement | null>(null)
let debounceTimer: any = null

watch(() => props.modelValue, (newVal) => {
  localQuery.value = newVal
})

function handleInput() {
  emit('update:modelValue', localQuery.value)

  if (debounceTimer) clearTimeout(debounceTimer)

  if (localQuery.value.trim().length > 1) {
    debounceTimer = setTimeout(async () => {
      isLoading.value = true
      try {
        suggestions.value = await docStore.getSuggestions(localQuery.value)
        showSuggestions.value = suggestions.value.length > 0
      } catch (e) {
        console.error(e)
      } finally {
        isLoading.value = false
      }
    }, 300)
  } else {
    suggestions.value = []
    showSuggestions.value = false
  }
}

function handleSearch(query?: string) {
  const q = query || localQuery.value
  if (q.trim()) {
    emit('search', q.trim())
    showSuggestions.value = false
  }
}

function selectSuggestion(suggestion: string) {
  localQuery.value = suggestion
  emit('update:modelValue', suggestion)
  handleSearch(suggestion)
}

function handleClear() {
  localQuery.value = ''
  emit('update:modelValue', '')
  emit('clear')
  suggestions.value = []
  showSuggestions.value = false
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter') {
    handleSearch()
  } else if (e.key === 'Escape') {
    showSuggestions.value = false
  }
}

// Close suggestions on click outside
function handleClickOutside(event: MouseEvent) {
  if (searchContainerRef.value && !searchContainerRef.value.contains(event.target as Node)) {
    showSuggestions.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<template>
  <div ref="searchContainerRef" class="search-container">
    <div class="search-bar">
      <Search class="search-icon h-4 w-4" />
      <input
        type="text"
        class="search-input"
        :value="localQuery"
        :placeholder="placeholder || t('common.search_documents')"
        @input="e => { localQuery = (e.target as HTMLInputElement).value; handleInput() }"
        @keydown="handleKeydown"
        @focus="handleInput"
      />
      <div v-if="isLoading" class="loading-indicator">
        <Loader2 class="h-3 w-3 animate-spin" />
      </div>
      <button
        v-if="localQuery"
        class="clear-btn"
        @click="handleClear"
        type="button"
      >
        <X class="h-3 w-3" />
      </button>
    </div>

    <!-- Suggestions Dropdown -->
    <div v-if="showSuggestions" class="suggestions-dropdown">
      <button
        v-for="(suggestion, index) in suggestions"
        :key="index"
        class="suggestion-item"
        @click="selectSuggestion(suggestion)"
      >
        <Search class="h-3 w-3 mr-2 opacity-50" />
        {{ suggestion }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.search-container {
  position: relative;
  width: 100%;
}

.search-bar {
  position: relative;
  display: flex;
  align-items: center;
  width: 100%;
}

.search-icon {
  position: absolute;
  left: 0.75rem;
  color: hsl(var(--muted-foreground));
  pointer-events: none;
}

.search-input {
  width: 100%;
  padding: 0.5rem 2.5rem 0.5rem 2.25rem;
  border: 1px solid hsl(var(--border));
  border-radius: 0.375rem;
  background-color: hsl(var(--background));
  color: hsl(var(--foreground));
  font-size: 0.875rem;
  transition: all 0.15s ease;
}

.search-input:focus {
  outline: none;
  border-color: hsl(var(--primary));
  box-shadow: 0 0 0 2px hsl(var(--primary) / 0.1);
}

.search-input::placeholder {
  color: hsl(var(--muted-foreground));
}

.loading-indicator {
  position: absolute;
  right: 2.25rem;
  color: hsl(var(--muted-foreground));
  pointer-events: none;
}

.clear-btn {
  position: absolute;
  right: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.5rem;
  height: 1.5rem;
  border: none;
  background: transparent;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  border-radius: 0.25rem;
  transition: all 0.15s ease;
}

.clear-btn:hover {
  background-color: hsl(var(--accent));
  color: hsl(var(--foreground));
}

.suggestions-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  margin-top: 0.25rem;
  background-color: hsl(var(--background));
  border: 1px solid hsl(var(--border));
  border-radius: 0.375rem;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  z-index: 50;
  max-height: 300px;
  overflow-y: auto;
}

.suggestion-item {
  display: flex;
  align-items: center;
  width: 100%;
  padding: 0.5rem 0.75rem;
  border: none;
  background: transparent;
  text-align: left;
  font-size: 0.875rem;
  color: hsl(var(--foreground));
  cursor: pointer;
}

.suggestion-item:hover {
  background-color: hsl(var(--accent));
}
</style>
