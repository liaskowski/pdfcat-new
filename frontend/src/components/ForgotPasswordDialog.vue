<script setup lang="ts">
import { ref } from 'vue'
import { X, Mail, Key, Loader2, CheckCircle2, AlertCircle } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import client from '@/api/client'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ 'update:open': [boolean] }>()

const step = ref<'email' | 'code'>('email')
const email = ref('')
const code = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const isLoading = ref(false)
const message = ref<{ type: 'success' | 'error'; text: string } | null>(null)

async function handleSendCode() {
  if (!email.value.trim()) {
    message.value = { type: 'error', text: t('auth.please_enter_email') }
    return
  }
  isLoading.value = true
  message.value = null
  try {
    await client.post('/auth/forgot-password', { email: email.value })
    message.value = { type: 'success', text: t('auth.recovery_code_sent') }
    step.value = 'code'
  } catch (e: any) {
    message.value = { type: 'error', text: e.response?.data?.detail || t('auth.recovery_send_failed') }
  } finally {
    isLoading.value = false
  }
}

async function handleResetPassword() {
  if (newPassword.value !== confirmPassword.value) {
    message.value = { type: 'error', text: t('auth.passwords_no_match') }
    return
  }
  if (newPassword.value.length < 6) {
    message.value = { type: 'error', text: t('auth.password_min_length') }
    return
  }
  isLoading.value = true
  message.value = null
  try {
    await client.post('/auth/reset-password', {
      email: email.value,
      code: code.value,
      new_password: newPassword.value,
    })
    message.value = { type: 'success', text: t('auth.reset_success') }
    setTimeout(() => {
      emit('update:open', false)
      resetForm()
    }, 1500)
  } catch (e: any) {
    message.value = { type: 'error', text: e.response?.data?.detail || t('auth.reset_failed') }
  } finally {
    isLoading.value = false
  }
}

function resetForm() {
  step.value = 'email'
  email.value = ''
  code.value = ''
  newPassword.value = ''
  confirmPassword.value = ''
  message.value = null
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
          <Key class="h-5 w-5 mr-2" />
          {{ step === 'email' ? t('auth.reset_password') : t('auth.enter_recovery_code') }}
        </h2>
        <button class="close-btn" @click="handleClose">
          <X class="h-4 w-4" />
        </button>
      </div>

      <div class="modal-body">
        <div v-if="message" class="message" :class="message.type">
          <CheckCircle2 v-if="message.type === 'success'" class="h-4 w-4 mr-2" />
          <AlertCircle v-else class="h-4 w-4 mr-2" />
          {{ message.text }}
        </div>

        <div v-if="step === 'email'">
          <p class="mb-3 text-sm text-muted-foreground">{{ t('auth.enter_email_hint') }}</p>
          <div class="form-group">
            <label class="form-label">{{ t('auth.email') }}</label>
            <Input v-model="email" type="email" :placeholder="t('auth.enter_email_hint')" />
          </div>
          <Button class="w-full mt-4" @click="handleSendCode" :disabled="isLoading">
            <Loader2 v-if="isLoading" class="h-4 w-4 mr-2 animate-spin" />
            <Mail v-else class="h-4 w-4 mr-2" />
            {{ isLoading ? t('auth.sending') : t('auth.send_code') }}
          </Button>
        </div>

        <div v-else>
          <div class="form-group">
            <label class="form-label">{{ t('auth.recovery_code') }}</label>
            <Input v-model="code" :placeholder="t('auth.enter_code_hint')" />
          </div>
          <div class="form-group">
            <label class="form-label">{{ t('auth.new_password') }}</label>
            <Input v-model="newPassword" type="password" :placeholder="t('auth.new_password')" />
          </div>
          <div class="form-group">
            <label class="form-label">{{ t('auth.confirm_new_password') }}</label>
            <Input v-model="confirmPassword" type="password" :placeholder="t('auth.confirm_new_password')" />
          </div>
          <Button class="w-full mt-4" @click="handleResetPassword" :disabled="isLoading">
            <Loader2 v-if="isLoading" class="h-4 w-4 mr-2 animate-spin" />
            <Key v-else class="h-4 w-4 mr-2" />
            {{ isLoading ? t('auth.resetting') : t('auth.reset_password_btn') }}
          </Button>
        </div>
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
