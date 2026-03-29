<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'

const props = defineProps<{
  modelValue: boolean
  x: number
  y: number
  items: Array<{
    label: string
    icon?: any
    action?: () => void
    disabled?: boolean
    danger?: boolean
    separator?: boolean
  }>
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  close: []
}>()

const menuRef = ref<HTMLElement | null>(null)

// Adjust position to keep within viewport
const style = computed(() => {
  if (!menuRef.value) return { top: `${props.y}px`, left: `${props.x}px` }
  
  let top = props.y
  let left = props.x
  
  // Simple check (can be improved with useElementBounding)
  if (left + 200 > window.innerWidth) left = window.innerWidth - 210
  if (top + 300 > window.innerHeight) top = window.innerHeight - 310
  
  return {
    top: `${top}px`,
    left: `${left}px`
  }
})

function handleClickOutside(event: MouseEvent) {
  if (props.modelValue && menuRef.value && !menuRef.value.contains(event.target as Node)) {
    emit('update:modelValue', false)
    emit('close')
  }
}

function handleItemClick(item: any) {
  if (item.disabled || !item.action) return
  item.action()
  emit('update:modelValue', false)
  emit('close')
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  document.addEventListener('contextmenu', handleClickOutside) // Close on other right clicks
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  document.removeEventListener('contextmenu', handleClickOutside)
})
</script>

<template>
  <div v-if="modelValue" ref="menuRef" class="context-menu" :style="style">
    <template v-for="(item, index) in items" :key="index">
      <div v-if="item.separator" class="menu-separator"></div>
      <button
        v-else
        class="menu-item"
        :class="{ 'disabled': item.disabled, 'danger': item.danger }"
        @click="handleItemClick(item)"
      >
        <component :is="item.icon" v-if="item.icon" class="menu-icon" />
        <span class="menu-label">{{ item.label }}</span>
      </button>
    </template>
  </div>
</template>

<style scoped>
.context-menu {
  position: fixed;
  z-index: 9999;
  background-color: hsl(var(--popover));
  border: 1px solid hsl(var(--border));
  border-radius: 0.5rem;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  min-width: 180px;
  padding: 0.25rem;
  display: flex;
  flex-direction: column;
}

.menu-item {
  display: flex;
  align-items: center;
  width: 100%;
  padding: 0.5rem 0.75rem;
  text-align: left;
  background: transparent;
  border: none;
  border-radius: 0.25rem;
  cursor: pointer;
  font-size: 0.875rem;
  color: hsl(var(--popover-foreground));
  transition: background-color 0.15s;
}

.menu-item:hover:not(.disabled) {
  background-color: hsl(var(--accent));
  color: hsl(var(--accent-foreground));
}

.menu-item.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.menu-item.danger {
  color: hsl(var(--destructive));
}

.menu-item.danger:hover:not(.disabled) {
  background-color: hsl(var(--destructive) / 0.1);
}

.menu-icon {
  width: 1rem;
  height: 1rem;
  margin-right: 0.5rem;
  opacity: 0.7;
}

.menu-separator {
  height: 1px;
  background-color: hsl(var(--border));
  margin: 0.25rem 0;
}
</style>
