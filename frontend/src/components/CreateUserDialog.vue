<script setup lang="ts">
import { ref } from 'vue'
import { X, UserPlus, Loader2, CheckCircle2, AlertCircle } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import client from '@/api/client'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ 'update:open': [boolean]; created: [] }>()

const username = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const isAdmin = ref(false)
const isActive = ref(true)
const isLoading = ref(false)
const error = ref('')
const success = ref(false)

async function handleCreate() {
  error.value = ''
  success.value = false

  if (!username.value.trim() || !email.value.trim() || !password.value) {
    error.value = t('admin.create_user_fields_required')
    return
  }
  if (password.value !== confirmPassword.value) {
    error.value = t('auth.passwords_no_match')
    return
  }
  if (password.value.length < 6) {
    error.value = t('auth.password_min_length')
    return
  }

  isLoading.value = true
  try {
    const formData = new FormData()
    formData.append('username', username.value.trim())
    formData.append('email', email.value.trim())
    formData.append('password', password.value)
    formData.append('is_superuser', isAdmin.value.toString())
    formData.append('is_active', isActive.value.toString())

    await client.post('/users', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })

    success.value = true
    setTimeout(() => {
      emit('created')
      emit('update:open', false)
      resetForm()
    }, 800)
  } catch (e: any) {
    error.value = e.response?.data?.detail || t('admin.create_user_failed')
  } finally {
    isLoading.value = false
  }
}

function resetForm() {
  username.value = ''
  email.value = ''
  password.value = ''
  confirmPassword.value = ''
  isAdmin.value = false
  isActive.value = true
  error.value = ''
  success.value = false
}

function handleClose() {
  resetForm()
  emit('update:open', false)
}
</script>

<template>
  <div v-if="open" class="modal-overlay" @click.self="handleClose">
    <div class="modal-content">
      <div class="modal-header">
        <h2 class="modal-title">
          <UserPlus class="h-5 w-5 mr-2" />
          {{ t('admin.create_user') }}
        </h2>
        <button class="close-btn" @click="handleClose">
          <X class="h-4 w-4" />
        </button>
      </div>

      <div class="modal-body">
        <div v-if="success" class="message success">
          <CheckCircle2 class="h-4 w-4 mr-2" />
          {{ t('admin.create_user_success') }}
        </div>

        <div v-if="error" class="message error">
          <AlertCircle class="h-4 w-4 mr-2" />
          {{ error }}
        </div>

        <div class="form-group">
          <label class="form-label">{{ t('admin.username') }}</label>
          <Input v-model="username" :placeholder="t('admin.username')" :disabled="isLoading" />
        </div>

        <div class="form-group">
          <label class="form-label">{{ t('admin.email') }}</label>
          <Input v-model="email" type="email" :placeholder="t('auth.email')" :disabled="isLoading" />
        </div>

        <div class="form-group">
          <label class="form-label">{{ t('auth.password') }}</label>
          <Input v-model="password" type="password" :placeholder="t('auth.password_min_length')" :disabled="isLoading" />
        </div>

        <div class="form-group">
          <label class="form-label">{{ t('auth.confirm_password') }}</label>
          <Input v-model="confirmPassword" type="password" :placeholder="t('auth.enter_code_hint')" :disabled="isLoading" />
        </div>

        <div class="checkbox-group">
          <label class="checkbox-label">
            <input type="checkbox" v-model="isAdmin" :disabled="isLoading" />
            {{ t('admin.admin_role') }}
          </label>
          <label class="checkbox-label">
            <input type="checkbox" v-model="isActive" :disabled="isLoading" />
            {{ t('admin.active') }}
          </label>
        </div>

        <Button class="w-full" @click="handleCreate" :disabled="isLoading">
          <Loader2 v-if="isLoading" class="h-4 w-4 mr-2 animate-spin" />
          <UserPlus v-else class="h-4 w-4 mr-2" />
          {{ isLoading ? t('admin.creating_user') : t('admin.create_user') }}
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
  max-width: 420px;
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
  display: flex;
  flex-direction: column;
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

.checkbox-group {
  display: flex;
  gap: 1rem;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.875rem;
  cursor: pointer;
}

.message {
  padding: 0.75rem;
  border-radius: 0.375rem;
  display: flex;
  align-items: center;
  font-size: 0.875rem;
}

.message.success {
  background-color: hsl(var(--success) / 0.1);
  color: hsl(var(--success));
}

.message.error {
  background-color: hsl(var(--destructive) / 0.1);
  color: hsl(var(--destructive));
}
</style>
