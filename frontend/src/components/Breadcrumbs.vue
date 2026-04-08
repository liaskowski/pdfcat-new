<script setup lang="ts">
import { ChevronRight, Home } from 'lucide-vue-next'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()

interface PathSegment {
  label: string
  folderId?: number | null
  viewMode?: string
  ownerId?: number | null
}

const props = defineProps<{
  pathSegments: PathSegment[]
}>()

const emit = defineEmits<{
  navigate: [segment: PathSegment]
}>()

function handleSegmentClick(segment: PathSegment) {
  emit('navigate', segment)
}
</script>

<template>
  <div class="breadcrumbs">
    <button
      class="breadcrumb-item home"
      @click="handleSegmentClick({ label: t('nav.my_documents'), folderId: null, viewMode: 'my', ownerId: null })"
    >
      <Home class="h-4 w-4" />
    </button>
    
    <template v-for="(segment, index) in pathSegments" :key="index">
      <ChevronRight class="h-4 w-4 separator" />
      <button
        class="breadcrumb-item"
        :class="{ current: index === pathSegments.length - 1 }"
        @click="handleSegmentClick(segment)"
      >
        {{ segment.label }}
      </button>
    </template>
  </div>
</template>

<style scoped>
.breadcrumbs {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.5rem 1rem;
  border-bottom: 1px solid hsl(var(--border));
  background-color: hsl(var(--background));
  font-size: 0.875rem;
}

.breadcrumb-item {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  border: none;
  background: transparent;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  border-radius: 0.25rem;
  transition: all 0.15s ease;
}

.breadcrumb-item:hover {
  background-color: hsl(var(--accent));
  color: hsl(var(--foreground));
}

.breadcrumb-item.current {
  color: hsl(var(--foreground));
  font-weight: 500;
  cursor: default;
}

.breadcrumb-item.current:hover {
  background-color: transparent;
}

.breadcrumb-item.home {
  padding: 0.25rem;
}

.separator {
  color: hsl(var(--muted-foreground));
  flex-shrink: 0;
}
</style>
