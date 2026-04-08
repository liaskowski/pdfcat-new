<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useAdminStore } from '@/stores/admin'
import { Button } from '@/components/ui/button'
import Shimmer from './ui/Shimmer.vue'
import CreateUserDialog from './CreateUserDialog.vue'
import client from '@/api/client'
import { useI18n } from '@/composables/useI18n'
import {
  Users, HardDrive, Database, Activity, RefreshCw, Trash2, Shield, Download, X, UserPlus, GitMerge as GitMergeIcon
} from 'lucide-vue-next'

const emit = defineEmits(['close'])

const { t } = useI18n()

const adminStore = useAdminStore()
const activeTab = ref<'dashboard' | 'users' | 'tags'>('dashboard')
const isLoading = ref(false)
const actionMsg = ref('')
const showCreateUserDialog = ref(false)

// Tag management state
const tagList = ref<{ tag: string; count: number }[]>([])
const showMergeDialog = ref(false)
const mergeSourceTag = ref('')
const mergeTargetTag = ref('')
const mergeLoading = ref(false)
const mergeError = ref('')

onMounted(async () => {
  await adminStore.fetchStats()
  await adminStore.fetchUsers()
})

async function handleBackup() {
  isLoading.value = true
  actionMsg.value = t('admin.backup_creating')
  try {
    await adminStore.createBackup()
    actionMsg.value = t('admin.backup_success')
  } catch (e) {
    actionMsg.value = t('admin.backup_failed')
  } finally {
    isLoading.value = false
    setTimeout(() => actionMsg.value = '', 3000)
  }
}

async function handleReindex() {
  if (!confirm(t('admin.reindex_confirm'))) return
  isLoading.value = true
  actionMsg.value = t('admin.reindex_starting')
  try {
    await adminStore.reindexDocuments()
    actionMsg.value = t('admin.reindex_started')
  } catch (e) {
    actionMsg.value = t('admin.reindex_failed')
  } finally {
    isLoading.value = false
    setTimeout(() => actionMsg.value = '', 3000)
  }
}

async function handleAutoTag() {
  if (!confirm(t('admin.auto_tag_confirm'))) return
  isLoading.value = true
  actionMsg.value = t('admin.auto_tag_starting')
  try {
    await client.post('/api/v1/admin/auto-tag')
    actionMsg.value = t('admin.auto_tag_done')
    await loadTagList()
  } catch (e: any) {
    actionMsg.value = e.response?.data?.detail || t('admin.auto_tag_failed')
  } finally {
    isLoading.value = false
    setTimeout(() => actionMsg.value = '', 3000)
  }
}

async function loadTagList() {
  try {
    const { data: docs } = await client.get('/documents/', { params: { limit: 5000 } })
    const tagCounts: Record<string, number> = {}
    docs.forEach((doc: any) => {
      if (doc.tags) {
        doc.tags.split(',').forEach((t: string) => {
          const tag = t.trim()
          if (tag) tagCounts[tag] = (tagCounts[tag] || 0) + 1
        })
      }
    })
    tagList.value = Object.entries(tagCounts)
      .map(([tag, count]) => ({ tag, count }))
      .sort((a, b) => b.count - a.count)
  } catch (e) {
    console.error('Failed to load tags:', e)
  }
}

async function handleMergeTags() {
  if (!mergeSourceTag.value || !mergeTargetTag.value) {
    mergeError.value = t('admin.merge_error_required')
    return
  }
  if (mergeSourceTag.value === mergeTargetTag.value) {
    mergeError.value = t('admin.merge_error_same')
    return
  }
  mergeLoading.value = true
  mergeError.value = ''
  try {
    await client.post('/api/v1/admin/merge-tags', null, {
      params: { old_tag: mergeSourceTag.value, new_tag: mergeTargetTag.value },
    })
    actionMsg.value = t('admin.merge_success').replace('{old}', mergeSourceTag.value).replace('{new}', mergeTargetTag.value)
    showMergeDialog.value = false
    mergeSourceTag.value = ''
    mergeTargetTag.value = ''
    await loadTagList()
    setTimeout(() => actionMsg.value = '', 3000)
  } catch (e: any) {
    mergeError.value = e.response?.data?.detail || t('admin.merge_failed')
  } finally {
    mergeLoading.value = false
  }
}

// Watch tags tab to load tags on demand
watch(activeTab, (tab) => {
  if (tab === 'tags') loadTagList()
})

async function handleDeleteUser(userId: number) {
  if (!confirm(t('admin.delete_user_confirm'))) return
  try {
    await adminStore.deleteUser(userId)
  } catch (e) {
    alert(t('admin.delete_failed'))
  }
}

function formatBytes(bytes: number) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}
</script>

<template>
  <div class="admin-panel">
    <div class="admin-sidebar">
      <div class="sidebar-header">
        <Shield class="h-6 w-6 text-primary" />
        <h2>{{ t('admin.title') }}</h2>
      </div>

      <nav class="sidebar-nav">
        <button
          class="nav-item"
          :class="{ active: activeTab === 'dashboard' }"
          @click="activeTab = 'dashboard'"
        >
          <Activity class="h-4 w-4" />
          {{ t('admin.dashboard') }}
        </button>
        <button
          class="nav-item"
          :class="{ active: activeTab === 'users' }"
          @click="activeTab = 'users'"
        >
          <Users class="h-4 w-4" />
          {{ t('admin.users') }}
        </button>
        <button
          class="nav-item"
          :class="{ active: activeTab === 'tags' }"
          @click="activeTab = 'tags'"
        >
          <Database class="h-4 w-4" />
          {{ t('admin.tags') }}
        </button>
      </nav>

      <div class="sidebar-footer">
        <Button variant="ghost" class="w-full justify-start text-muted-foreground" @click="emit('close')">
          <X class="h-4 w-4 mr-2" />
          {{ t('admin.close_panel') }}
        </Button>
      </div>
    </div>

    <div class="admin-content">
      <header class="content-header">
        <h1 class="page-title">{{ activeTab === 'dashboard' ? t('admin.system_overview') : activeTab === 'users' ? t('admin.user_management') : t('admin.tag_management') }}</h1>
        <div v-if="actionMsg" class="status-msg">{{ actionMsg }}</div>
      </header>

      <main class="content-body">
        <!-- Dashboard Tab -->
        <div v-if="activeTab === 'dashboard' && !adminStore.stats" class="loading-dashboard">
          <Loader2 class="h-8 w-8 animate-spin" />
          <p>{{ t('admin.loading_stats') }}</p>
        </div>
        <div v-else-if="activeTab === 'dashboard' && adminStore.stats" class="dashboard-grid">
          <div class="stat-card">
            <div class="stat-icon bg-blue-100 text-blue-600"><Database class="h-6 w-6" /></div>
            <div class="stat-info">
              <span class="stat-label">{{ t('admin.docs_label') }}</span>
              <span v-if="adminStore.stats" class="stat-value">{{ adminStore.stats.database.documents }}</span>
              <Shimmer v-else width="60px" height="24px" />
            </div>
          </div>

          <div class="stat-card">
            <div class="stat-icon bg-green-100 text-green-600"><Users class="h-6 w-6" /></div>
            <div class="stat-info">
              <span class="stat-label">{{ t('admin.users_label') }}</span>
              <span v-if="adminStore.stats" class="stat-value">{{ adminStore.stats.database.users }}</span>
              <Shimmer v-else width="40px" height="24px" />
            </div>
          </div>

          <div class="stat-card">
            <div class="stat-icon bg-purple-100 text-purple-600"><HardDrive class="h-6 w-6" /></div>
            <div class="stat-info">
              <span class="stat-label">{{ t('admin.storage_label') }}</span>
              <span v-if="adminStore.stats" class="stat-value">{{ formatBytes(adminStore.stats.storage.upload_dir_bytes) }}</span>
              <Shimmer v-else width="80px" height="24px" />
            </div>
          </div>

          <div class="system-actions">
            <h3>{{ t('admin.system_actions') }}</h3>
            <div class="actions-grid">
              <div class="action-card">
                <h4>{{ t('admin.backup_title') }}</h4>
                <p>{{ t('admin.backup_desc') }}</p>
                <Button @click="handleBackup" :disabled="isLoading">
                  <Download class="h-4 w-4 mr-2" /> {{ t('admin.backup_btn') }}
                </Button>
              </div>

              <div class="action-card">
                <h4>{{ t('admin.reindex_title') }}</h4>
                <p>{{ t('admin.reindex_desc') }}</p>
                <Button variant="outline" @click="handleReindex" :disabled="isLoading">
                  <RefreshCw class="h-4 w-4 mr-2" /> {{ t('admin.reindex_btn') }}
                </Button>
              </div>
            </div>
          </div>
        </div>

        <!-- Users Tab -->
        <div v-else-if="activeTab === 'users'" class="users-list">
          <div class="users-header">
            <h2>{{ t('admin.registered_users') }}</h2>
            <Button @click="showCreateUserDialog = true">
              <UserPlus class="h-4 w-4 mr-2" /> {{ t('admin.create_user') }}
            </Button>
          </div>
          <div class="table-container">
            <table>
              <thead>
                <tr>
                  <th>{{ t('admin.id') }}</th>
                  <th>{{ t('admin.username') }}</th>
                  <th>{{ t('admin.email') }}</th>
                  <th>{{ t('admin.status') }}</th>
                  <th>{{ t('admin.role') }}</th>
                  <th>{{ t('admin.actions') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="user in adminStore.users" :key="user.id">
                  <td>#{{ user.id }}</td>
                  <td class="font-medium">{{ user.username }}</td>
                  <td>{{ user.email }}</td>
                  <td>
                    <span
                      class="status-badge"
                      :class="user.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'"
                    >
                      {{ user.is_active ? t('admin.active') : t('admin.inactive') }}
                    </span>
                  </td>
                  <td>{{ user.is_superuser ? t('admin.admin_role') : t('admin.user_role') }}</td>
                  <td>
                    <button
                      class="delete-btn"
                      @click="handleDeleteUser(user.id)"
                      :disabled="user.is_superuser"
                      :title="t('admin.delete_user')"
                    >
                      <Trash2 class="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Tags Tab -->
        <div v-else-if="activeTab === 'tags'" class="tags-tab">
          <div class="tags-header">
            <h2>{{ t('admin.tag_management') }}</h2>
            <div class="tags-actions">
              <Button variant="outline" @click="showMergeDialog = true" :disabled="tagList.length < 2">
                <GitMergeIcon class="h-4 w-4 mr-2" /> {{ t('admin.merge_tags') }}
              </Button>
              <Button variant="outline" @click="handleAutoTag" :disabled="isLoading">
                <RefreshCw class="h-4 w-4 mr-2" /> {{ t('admin.auto_tag') }}
              </Button>
            </div>
          </div>
          <p class="tags-description">
            {{ t('admin.tag_desc') }}
          </p>
          <div v-if="actionMsg" class="status-msg">{{ actionMsg }}</div>

          <div v-if="tagList.length > 0" class="tags-table-container">
            <table>
              <thead>
                <tr>
                  <th>{{ t('admin.tag_name') }}</th>
                  <th>{{ t('admin.tag_count') }}</th>
                  <th>{{ t('admin.tag_actions') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in tagList" :key="item.tag">
                  <td class="font-medium">{{ item.tag }}</td>
                  <td>{{ item.count }}</td>
                  <td>
                    <button class="merge-quick-btn" @click="mergeSourceTag = item.tag; showMergeDialog = true" :title="t('admin.merge_tag_btn')">
                      {{ t('admin.merge_tag_btn') }}
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else class="empty-tags">
            <Database class="h-12 w-12 opacity-20" />
            <p>{{ t('admin.no_tags_found') }}</p>
          </div>

          <!-- Merge Tags Dialog -->
          <div v-if="showMergeDialog" class="merge-dialog" @click.self="showMergeDialog = false">
            <div class="merge-dialog-content">
              <div class="merge-header">
                <h3>{{ t('admin.merge_dialog_title') }}</h3>
                <button class="close-btn" @click="showMergeDialog = false"><X class="h-4 w-4" /></button>
              </div>
              <div class="merge-body">
                <p class="merge-desc">{{ t('admin.merge_dialog_desc') }}</p>
                <div class="form-group">
                  <label class="form-label">{{ t('admin.source_tag') }}</label>
                  <select v-model="mergeSourceTag" class="select-input">
                    <option value="" disabled>{{ t('admin.select_source') }}</option>
                    <option v-for="item in tagList" :key="item.tag" :value="item.tag">{{ item.tag }} ({{ item.count }})</option>
                  </select>
                </div>
                <div class="form-group">
                  <label class="form-label">{{ t('admin.target_tag') }}</label>
                  <select v-model="mergeTargetTag" class="select-input">
                    <option value="" disabled>{{ t('admin.select_target') }}</option>
                    <option v-for="item in tagList" :key="item.tag" :value="item.tag">{{ item.tag }} ({{ item.count }})</option>
                  </select>
                </div>
                <div v-if="mergeError" class="merge-error-msg">{{ mergeError }}</div>
              </div>
              <div class="merge-footer">
                <Button variant="outline" @click="showMergeDialog = false">{{ t('common.cancel') }}</Button>
                <Button @click="handleMergeTags" :disabled="mergeLoading">
                  {{ mergeLoading ? t('admin.merging') : t('admin.merge_btn') }}
                </Button>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>

    <CreateUserDialog
      v-model:open="showCreateUserDialog"
      @created="adminStore.fetchUsers()"
    />
  </div>
</template>

<style scoped>
.admin-panel {
  position: fixed;
  inset: 0;
  background-color: hsl(var(--background));
  z-index: 100;
  display: flex;
}

.admin-sidebar {
  width: 240px;
  border-right: 1px solid hsl(var(--border));
  display: flex;
  flex-direction: column;
  background-color: hsl(var(--muted) / 0.3);
}

.sidebar-header {
  padding: 1.5rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  border-bottom: 1px solid hsl(var(--border));
}

.sidebar-header h2 {
  font-size: 1.25rem;
  font-weight: 600;
  margin: 0;
}

.sidebar-nav {
  flex: 1;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  border-radius: 0.5rem;
  border: none;
  background: transparent;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  text-align: left;
  font-weight: 500;
  transition: all 0.2s;
}

.nav-item:hover {
  background-color: hsl(var(--accent));
  color: hsl(var(--foreground));
}

.nav-item.active {
  background-color: hsl(var(--primary) / 0.1);
  color: hsl(var(--primary));
}

.sidebar-footer {
  padding: 1rem;
  border-top: 1px solid hsl(var(--border));
}

.admin-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.content-header {
  padding: 1.5rem 2rem;
  border-bottom: 1px solid hsl(var(--border));
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.page-title {
  font-size: 1.5rem;
  font-weight: 600;
  margin: 0;
}

.status-msg {
  color: hsl(var(--primary));
  font-weight: 500;
}

.content-body {
  flex: 1;
  overflow-y: auto;
  padding: 2rem;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.stat-card {
  background-color: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  border-radius: 0.75rem;
  padding: 1.5rem;
  display: flex;
  align-items: center;
  gap: 1rem;
}

.stat-icon {
  width: 3rem;
  height: 3rem;
  border-radius: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-label {
  font-size: 0.875rem;
  color: hsl(var(--muted-foreground));
}

.stat-value {
  font-size: 1.5rem;
  font-weight: 700;
}

.system-actions {
  grid-column: 1 / -1;
  margin-top: 2rem;
}

.system-actions h3 {
  font-size: 1.25rem;
  font-weight: 600;
  margin-bottom: 1rem;
}

.actions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1.5rem;
}

.action-card {
  background-color: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  border-radius: 0.75rem;
  padding: 1.5rem;
}

.action-card h4 {
  margin: 0 0 0.5rem 0;
  font-size: 1rem;
  font-weight: 600;
}

.action-card p {
  color: hsl(var(--muted-foreground));
  margin-bottom: 1.5rem;
  font-size: 0.875rem;
}

.table-container {
  border: 1px solid hsl(var(--border));
  border-radius: 0.75rem;
  overflow: hidden;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th {
  background-color: hsl(var(--muted) / 0.5);
  text-align: left;
  padding: 0.75rem 1.5rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: hsl(var(--muted-foreground));
  border-bottom: 1px solid hsl(var(--border));
}

td {
  padding: 1rem 1.5rem;
  font-size: 0.875rem;
  border-bottom: 1px solid hsl(var(--border));
}

tr:last-child td {
  border-bottom: none;
}

.status-badge {
  display: inline-flex;
  padding: 0.25rem 0.625rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 500;
}

.delete-btn {
  color: hsl(var(--muted-foreground));
  padding: 0.5rem;
  border-radius: 0.375rem;
  border: none;
  background: transparent;
  cursor: pointer;
  transition: all 0.2s;
}

.delete-btn:hover:not(:disabled) {
  background-color: hsl(var(--destructive) / 0.1);
  color: hsl(var(--destructive));
}

.delete-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.users-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.users-header h2 {
  font-size: 1.125rem;
  font-weight: 600;
  margin: 0;
}

.tags-tab {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.tags-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.tags-header h2 {
  font-size: 1.125rem;
  font-weight: 600;
  margin: 0;
}

.tags-description {
  font-size: 0.875rem;
  color: hsl(var(--muted-foreground));
  line-height: 1.5;
}

.tags-actions {
  display: flex;
  gap: 0.5rem;
}

.tags-table-container {
  border: 1px solid hsl(var(--border));
  border-radius: 0.5rem;
  overflow: hidden;
  max-height: 500px;
  overflow-y: auto;
}

.tags-table-container table {
  width: 100%;
  border-collapse: collapse;
}

.tags-table-container th {
  background-color: hsl(var(--muted) / 0.5);
  text-align: left;
  padding: 0.625rem 1rem;
  font-size: 0.8125rem;
  font-weight: 500;
  color: hsl(var(--muted-foreground));
  border-bottom: 1px solid hsl(var(--border));
  position: sticky;
  top: 0;
  z-index: 1;
}

.tags-table-container td {
  padding: 0.5rem 1rem;
  font-size: 0.8125rem;
  border-bottom: 1px solid hsl(var(--border));
}

.tags-table-container tr:last-child td {
  border-bottom: none;
}

.tags-table-container tr:hover {
  background-color: hsl(var(--accent) / 0.3);
}

.merge-quick-btn {
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  border: 1px solid hsl(var(--border));
  border-radius: 0.25rem;
  background: transparent;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
}

.merge-quick-btn:hover {
  background-color: hsl(var(--accent));
  color: hsl(var(--foreground));
}

.empty-tags {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  color: hsl(var(--muted-foreground));
  gap: 0.75rem;
}

.empty-tags p {
  font-size: 0.875rem;
}

.merge-dialog {
  position: fixed;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
  padding: 1rem;
}

.merge-dialog-content {
  background-color: hsl(var(--background));
  border-radius: 0.5rem;
  width: 100%;
  max-width: 450px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  overflow: hidden;
}

.merge-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid hsl(var(--border));
}

.merge-header h3 {
  font-size: 1rem;
  font-weight: 600;
  margin: 0;
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

.merge-body {
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.merge-desc {
  font-size: 0.8125rem;
  color: hsl(var(--muted-foreground));
  margin: 0;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.form-label {
  font-size: 0.8125rem;
  font-weight: 500;
}

.select-input {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid hsl(var(--border));
  border-radius: 0.375rem;
  background-color: hsl(var(--background));
  color: hsl(var(--foreground));
  font-size: 0.8125rem;
}

.merge-error-msg {
  padding: 0.5rem;
  border-radius: 0.25rem;
  background-color: hsl(var(--destructive) / 0.1);
  color: hsl(var(--destructive));
  font-size: 0.8125rem;
}

.merge-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 1rem 1.25rem;
  border-top: 1px solid hsl(var(--border));
}

.loading-dashboard {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem;
  gap: 1rem;
  color: hsl(var(--muted-foreground));
}
</style>
