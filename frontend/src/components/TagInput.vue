<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { X, Plus, Hash } from 'lucide-vue-next'
import { useDocumentStore } from '@/stores/documents'

const props = defineProps<{
  modelValue: string
  disabled?: boolean
  placeholder?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const docStore = useDocumentStore()

const inputRef = ref<HTMLInputElement>()
const inputText = ref('')
const showDropdown = ref(false)
const selectedIndex = ref(-1)
const localTags = ref<string[]>([])

// Инициализация из modelValue (comma-separated строка)
watch(() => props.modelValue, (val) => {
  if (val === undefined || val === null) return
  const parsed = val.split(',').map(t => t.trim()).filter(Boolean)
  if (JSON.stringify(parsed) !== JSON.stringify(localTags.value)) {
    localTags.value = parsed
  }
}, { immediate: true })

// Синхронизация localTags → modelValue
watch(localTags, () => {
  emit('update:modelValue', localTags.value.join(', '))
}, { deep: true })

// Автокомплит
const suggestions = ref<string[]>([])
const loading = ref(false)

async function fetchSuggestions(query: string) {
  if (!query.trim()) {
    const results = await docStore.fetchTags('')
    // Фильтруем уже выбранные теги, даже при пустом query
    suggestions.value = results.filter(
      s => !localTags.value.some(t => t.toLowerCase() === s.toLowerCase())
    )
    showDropdown.value = suggestions.value.length > 0
    return
  }
  loading.value = true
  try {
    const results = await docStore.fetchTags(query)
    // Добавляем ввод пользователя как вариант, если его нет в результатах
    const q = query.trim().toLowerCase()
    const existing = new Set(results.map(r => r.toLowerCase()))
    if (q && !existing.has(q)) {
      results.unshift(query.trim())
    }
    suggestions.value = results.filter(
      s => !localTags.value.some(t => t.toLowerCase() === s.toLowerCase())
    )
    showDropdown.value = suggestions.value.length > 0
    selectedIndex.value = -1
  } finally {
    loading.value = false
  }
}

let debounceTimer: ReturnType<typeof setTimeout> | null = null

function onInput(e: Event) {
  const val = (e.target as HTMLInputElement).value
  inputText.value = val
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => fetchSuggestions(val), 100)
}

function selectTag(tag: string) {
  const lower = tag.toLowerCase()
  if (!localTags.value.some(t => t.toLowerCase() === lower)) {
    localTags.value = [...localTags.value, tag]
  }
  inputText.value = ''
  suggestions.value = []
  showDropdown.value = false
  inputRef.value?.focus()
}

function removeTag(index: number) {
  localTags.value = localTags.value.filter((_, i) => i !== index)
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && inputText.value.trim()) {
    e.preventDefault()
    if (selectedIndex.value >= 0 && selectedIndex.value < suggestions.value.length) {
      selectTag(suggestions.value[selectedIndex.value])
    } else {
      selectTag(inputText.value.trim())
    }
  } else if (e.key === 'ArrowDown') {
    e.preventDefault()
    if (showDropdown.value) {
      selectedIndex.value = Math.min(
        selectedIndex.value + 1,
        suggestions.value.length - 1
      )
    }
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    selectedIndex.value = Math.max(selectedIndex.value - 1, -1)
  } else if (e.key === 'Backspace' && !inputText.value && localTags.value.length > 0) {
    localTags.value = localTags.value.slice(0, -1)
  } else if (e.key === 'Escape') {
    showDropdown.value = false
  } else if (e.key === ',') {
    e.preventDefault()
    const val = inputText.value.trim()
    if (val) selectTag(val)
  }
}

function onBlur() {
  // Hide dropdown after a short delay so click events on dropdown items can fire
  setTimeout(() => { showDropdown.value = false }, 200)
}

function onFocus() {
  fetchSuggestions(inputText.value)
}

onMounted(() => {
  // Не открываем дропдаун при монтировании
})
</script>

<template>
  <div class="tag-input-wrapper" :class="{ 'is-disabled': disabled }">
    <div class="tag-chips" @click="inputRef?.focus()">
      <span v-for="(tag, i) in localTags" :key="i" class="tag-chip">
        <Hash class="h-3 w-3 tag-hash" />
        <span class="tag-text">{{ tag }}</span>
        <button
          type="button"
          class="tag-remove"
          :disabled="disabled"
          @click.stop="removeTag(i)"
        >
          <X class="h-3 w-3" />
        </button>
      </span>
      <input
        ref="inputRef"
        type="text"
        class="tag-input-field"
        :value="inputText"
        :disabled="disabled"
        :placeholder="localTags.length === 0 ? (placeholder || 'tag1, tag2, tag3') : ''"
        @input="onInput"
        @keydown="onKeydown"
        @focus="onFocus"
        @blur="onBlur"
      />
    </div>

    <!-- Dropdown -->
    <Transition name="dropdown">
      <div v-if="showDropdown && suggestions.length > 0" class="tag-dropdown">
        <div
          v-for="(s, i) in suggestions"
          :key="i"
          class="tag-dropdown-item"
          :class="{ 'is-selected': i === selectedIndex }"
          @mousedown.prevent="selectTag(s)"
        >
          <Hash class="h-3.5 w-3.5 shrink-0" />
          <span>{{ s }}</span>
          <Plus v-if="!docStore.allTags.includes(s)" class="h-3 w-3 ml-auto new-badge" />
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.tag-input-wrapper {
  position: relative;
  width: 100%;
}
.tag-input-wrapper.is-disabled {
  opacity: 0.5;
  pointer-events: none;
}

.tag-chips {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.375rem;
  min-height: 2.25rem;
  padding: 0.3125rem 0.5rem;
  border: 1px solid hsl(var(--border));
  border-radius: calc(var(--radius) - 2px);
  background: transparent;
  cursor: text;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.tag-chips:focus-within {
  border-color: hsl(var(--ring));
  box-shadow: 0 0 0 1px hsl(var(--ring));
}

.tag-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.125rem;
  padding: 0.125rem 0.375rem;
  background: hsl(var(--secondary));
  border-radius: calc(var(--radius) - 2px);
  font-size: 0.8125rem;
  line-height: 1.4;
  white-space: nowrap;
}
.tag-hash {
  color: hsl(var(--muted-foreground));
  opacity: 0.5;
}
.tag-text {
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.tag-remove {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1rem;
  height: 1rem;
  margin-left: 0.125rem;
  border: none;
  background: transparent;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  border-radius: 2px;
  padding: 0;
}
.tag-remove:hover {
  color: hsl(var(--foreground));
  background: hsl(var(--accent));
}

.tag-input-field {
  flex: 1;
  min-width: 80px;
  border: none;
  outline: none;
  background: transparent;
  font-size: 0.875rem;
  padding: 0.125rem 0;
  color: hsl(var(--foreground));
  min-height: 1.5rem;
}
.tag-input-field::placeholder {
  color: hsl(var(--muted-foreground));
}

/* Dropdown */
.tag-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  z-index: 100;
  margin-top: 2px;
  background: hsl(var(--popover));
  border: 1px solid hsl(var(--border));
  border-radius: calc(var(--radius) - 2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  max-height: 200px;
  overflow-y: auto;
}
.tag-dropdown-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
  cursor: pointer;
  color: hsl(var(--popover-foreground));
  transition: background-color 0.1s;
}
.tag-dropdown-item:hover,
.tag-dropdown-item.is-selected {
  background: hsl(var(--accent));
  color: hsl(var(--accent-foreground));
}
.new-badge {
  color: hsl(var(--primary));
}

/* Transition */
.dropdown-enter-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.dropdown-leave-active {
  transition: opacity 0.1s ease;
}
.dropdown-enter-from {
  opacity: 0;
  transform: translateY(-4px);
}
.dropdown-leave-to {
  opacity: 0;
}
</style>
