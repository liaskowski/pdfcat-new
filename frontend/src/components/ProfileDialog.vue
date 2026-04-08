<script setup lang="ts">
import { ref, computed } from 'vue'
import { X, User, Lock, Save, Loader2, CheckCircle2, AlertCircle } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import client from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()

const props = defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  'update:open': [open: boolean]
}>()

const auth = useAuthStore()
const activeTab = ref<'profile' | 'security'>('profile')
const isSaving = ref(false)
const message = ref<{ type: 'success' | 'error', text: string } | null>(null)

// Password fields
const oldPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')

// Avatar
const avatarFile = ref<File | null>(null)
const avatarPreview = ref<string | null>(auth.user?.avatar_url || null)
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// Editable profile fields
const username = ref(auth.user?.username || '')
const email = ref(auth.user?.email || '')

const isOpen = computed({
  get: () => props.open,
  set: (value) => emit('update:open', value)
})

function handleAvatarChange(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files && input.files.length > 0) {
    const file = input.files[0]
    avatarFile.value = file
    avatarPreview.value = URL.createObjectURL(file)
  }
}

async function handleSaveProfile() {
  isSaving.value = true
  message.value = null
  try {
    if (avatarFile.value) {
      const formData = new FormData()
      formData.append('file', avatarFile.value)
      await client.post('/users/me/avatar', formData)
      await auth.fetchUser() // Refresh user data
    }

    // Update username and email
    await client.patch('/users/me', {
      username: username.value,
      email: email.value,
    })

    await auth.fetchUser() // Refresh
    message.value = { type: 'success', text: t('profile.profile_updated') }
  } catch (e: any) {
    message.value = { type: 'error', text: t('profile.profile_update_failed') }
  } finally {
    isSaving.value = false
  }
}

async function handleChangePassword() {
  if (newPassword.value !== confirmPassword.value) {
    message.value = { type: 'error', text: t('auth.passwords_no_match') }
    return
  }

  isSaving.value = true
  message.value = null
  try {
    await client.post('/users/me/password', {
      old_password: oldPassword.value,
      new_password: newPassword.value
    })

    message.value = { type: 'success', text: t('profile.password_changed') }
    oldPassword.value = ''
    newPassword.value = ''
    confirmPassword.value = ''
  } catch (e: any) {
    message.value = { type: 'error', text: e.response?.data?.detail || t('profile.password_change_failed') }
  } finally {
    isSaving.value = false
  }
}

function handleClose() {
  isOpen.value = false
  message.value = null
  activeTab.value = 'profile'
}
</script>

<template>
  <div v-if="isOpen" class="modal-overlay" @click.self="handleClose">
    <div class="modal-content">
      <div class="modal-header">
        <h2 class="modal-title">{{ t('profile.title') }}</h2>
        <button class="close-btn" @click="handleClose">
          <X class="h-4 w-4" />
        </button>
      </div>

      <div class="modal-body">
        <div class="tabs">
          <button
            class="tab-btn"
            :class="{ active: activeTab === 'profile' }"
            @click="activeTab = 'profile'"
          >
            <User class="h-4 w-4 mr-2" />
            {{ t('profile.profile_tab') }}
          </button>
          <button
            class="tab-btn"
            :class="{ active: activeTab === 'security' }"
            @click="activeTab = 'security'"
          >
            <Lock class="h-4 w-4 mr-2" />
            {{ t('profile.security_tab') }}
          </button>
        </div>

        <div v-if="message" class="message" :class="message.type">
          <CheckCircle2 v-if="message.type === 'success'" class="h-4 w-4 mr-2" />
          <AlertCircle v-else class="h-4 w-4 mr-2" />
          {{ message.text }}
        </div>

        <!-- Profile Tab -->
        <div v-if="activeTab === 'profile'" class="tab-content">
          <div class="avatar-section">
            <div class="avatar-preview">
              <img
                v-if="avatarPreview"
                :src="avatarPreview.startsWith('blob') ? avatarPreview : `${API_BASE_URL}/${avatarPreview}`"
                alt="Avatar"
                class="avatar-img"
              />
              <div v-else class="avatar-placeholder">
                <User class="h-12 w-12 text-muted-foreground" />
              </div>
            </div>
            <div class="avatar-actions">
              <label class="btn-outline">
                {{ t('profile.change_avatar') }}
                <input type="file" accept="image/*" class="hidden" @change="handleAvatarChange" />
              </label>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">{{ t('profile.username') }}</label>
            <Input v-model="username" :placeholder="t('profile.username')" />
          </div>

          <div class="form-group">
            <label class="form-label">{{ t('profile.email') }}</label>
            <Input v-model="email" type="email" :placeholder="t('profile.email')" />
          </div>

          <div class="actions">
            <Button @click="handleSaveProfile" :disabled="isSaving">
              <Loader2 v-if="isSaving" class="h-4 w-4 mr-2 animate-spin" />
              <Save v-else class="h-4 w-4 mr-2" />
              {{ t('profile.save_changes') }}
            </Button>
          </div>
        </div>

        <!-- Security Tab -->
        <div v-if="activeTab === 'security'" class="tab-content">
          <div class="form-group">
            <label class="form-label">{{ t('profile.current_password') }}</label>
            <Input v-model="oldPassword" type="password" />
          </div>

          <div class="form-group">
            <label class="form-label">{{ t('profile.new_password') }}</label>
            <Input v-model="newPassword" type="password" />
          </div>

          <div class="form-group">
            <label class="form-label">{{ t('profile.confirm_password') }}</label>
            <Input v-model="confirmPassword" type="password" />
          </div>

          <div class="actions">
            <Button @click="handleChangePassword" :disabled="isSaving || !oldPassword || !newPassword">
              <Loader2 v-if="isSaving" class="h-4 w-4 mr-2 animate-spin" />
              <Save v-else class="h-4 w-4 mr-2" />
              {{ t('profile.change_password_btn') }}
            </Button>
          </div>
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
  max-width: 450px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  overflow: hidden;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid hsl(var(--border));
}

.modal-title { font-size: 1.125rem; font-weight: 600; margin: 0; }

.close-btn {
  border: none;
  background: transparent;
  cursor: pointer;
  color: hsl(var(--muted-foreground));
}

.modal-body { padding: 0; display: flex; flex-direction: column; }

.tabs {
  display: flex;
  border-bottom: 1px solid hsl(var(--border));
  background-color: hsl(var(--muted) / 0.3);
}

.tab-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  border: none;
  background: transparent;
  cursor: pointer;
  font-weight: 500;
  color: hsl(var(--muted-foreground));
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}

.tab-btn:hover { background-color: hsl(var(--accent)); color: hsl(var(--foreground)); }
.tab-btn.active { color: hsl(var(--primary)); border-bottom-color: hsl(var(--primary)); background-color: hsl(var(--background)); }

.tab-content { padding: 1.5rem; display: flex; flex-direction: column; gap: 1.25rem; }

.avatar-section { display: flex; align-items: center; gap: 1.5rem; margin-bottom: 0.5rem; }
.avatar-preview {
  width: 5rem; height: 5rem;
  border-radius: 50%;
  overflow: hidden;
  border: 2px solid hsl(var(--border));
  background-color: hsl(var(--muted));
  display: flex;
  align-items: center;
  justify-content: center;
}
.avatar-img { width: 100%; height: 100%; object-fit: cover; }

.btn-outline {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.5rem 1rem;
  border: 1px solid hsl(var(--border));
  border-radius: 0.375rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  background-color: hsl(var(--background));
  transition: all 0.2s;
}
.btn-outline:hover { background-color: hsl(var(--accent)); }
.hidden { display: none; }

.form-group { display: flex; flex-direction: column; gap: 0.5rem; }
.form-label { font-size: 0.875rem; font-weight: 500; }

.actions { margin-top: 0.5rem; display: flex; justify-content: flex-end; }

.message {
  margin: 1rem 1rem 0;
  padding: 0.75rem;
  border-radius: 0.375rem;
  display: flex;
  align-items: center;
  font-size: 0.875rem;
}
.message.success { background-color: hsl(var(--success) / 0.1); color: hsl(var(--success)); }
.message.error { background-color: hsl(var(--destructive) / 0.1); color: hsl(var(--destructive)); }
</style>
