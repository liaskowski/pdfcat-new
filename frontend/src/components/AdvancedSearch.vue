<script setup lang="ts">
import { ref } from 'vue'
import { X } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()

const props = defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  'update:open': [value: boolean]
  search: [filters: any]
}>()

const dateFrom = ref('')
const dateTo = ref('')
const tags = ref('')
const hasNotes = ref(false)

function handleSearch() {
  emit('search', {
    dateFrom: dateFrom.value,
    dateTo: dateTo.value,
    tags: tags.value,
    hasNotes: hasNotes.value
  })
  emit('update:open', false)
}

function handleReset() {
  dateFrom.value = ''
  dateTo.value = ''
  tags.value = ''
  hasNotes.value = false
}
</script>

<template>
  <div v-if="open" class="adv-search-popover">
    <div class="popover-header">
      <h3>{{ t('filters.advanced') }}</h3>
      <button class="close-btn" @click="$emit('update:open', false)">
        <X class="h-4 w-4" />
      </button>
    </div>

    <div class="popover-body">
      <div class="form-group">
        <label>{{ t('filters.date_range') }}</label>
        <div class="date-range">
          <Input type="date" v-model="dateFrom" />
          <span>-</span>
          <Input type="date" v-model="dateTo" />
        </div>
      </div>

      <div class="form-group">
        <label>{{ t('filters.tags') }}</label>
        <Input v-model="tags" :placeholder="t('filters.tags_placeholder')" />
      </div>

      <div class="form-group">
        <label class="checkbox-label">
          <input type="checkbox" v-model="hasNotes" />
          {{ t('filters.has_notes') }}
        </label>
      </div>
    </div>

    <div class="popover-footer">
      <Button variant="ghost" size="sm" @click="handleReset">{{ t('filters.reset') }}</Button>
      <Button size="sm" @click="handleSearch">{{ t('filters.apply_filters') }}</Button>
    </div>
  </div>
</template>

<style scoped>
.adv-search-popover {
  position: absolute;
  top: 100%;
  right: 0;
  width: 300px;
  background-color: hsl(var(--popover));
  border: 1px solid hsl(var(--border));
  border-radius: 0.5rem;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
  z-index: 50;
  margin-top: 0.5rem;
  display: flex;
  flex-direction: column;
}

.popover-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid hsl(var(--border));
}

.popover-header h3 { margin: 0; font-size: 0.875rem; font-weight: 600; }

.close-btn { background: none; border: none; cursor: pointer; color: hsl(var(--muted-foreground)); }

.popover-body { padding: 1rem; display: flex; flex-direction: column; gap: 1rem; }

.form-group { display: flex; flex-direction: column; gap: 0.375rem; }
.form-group label { font-size: 0.75rem; font-weight: 500; color: hsl(var(--muted-foreground)); }

.date-range { display: flex; align-items: center; gap: 0.5rem; }

.checkbox-label { display: flex; align-items: center; gap: 0.5rem; font-size: 0.875rem; cursor: pointer; color: hsl(var(--foreground)); }

.popover-footer { padding: 0.75rem 1rem; border-top: 1px solid hsl(var(--border)); display: flex; justify-content: space-between; }
</style>
