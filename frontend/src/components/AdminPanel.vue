<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAdminStore } from '@/stores/admin'
import { Button } from '@/components/ui/button'
import { 
  Users, HardDrive, Database, Activity, RefreshCw, Trash2, Shield, Download, X
} from 'lucide-vue-next'

const emit = defineEmits(['close'])

const adminStore = useAdminStore()
const activeTab = ref<'dashboard' | 'users'>('dashboard')
const isLoading = ref(false)
const actionMsg = ref('')

onMounted(async () => {
  await adminStore.fetchStats()
  await adminStore.fetchUsers()
})

async function handleBackup() {
  isLoading.value = true
  actionMsg.value = 'Creating backup...'
  try {
    await adminStore.createBackup()
    actionMsg.value = 'Backup downloaded successfully'
  } catch (e) {
    actionMsg.value = 'Backup failed'
  } finally {
    isLoading.value = false
    setTimeout(() => actionMsg.value = '', 3000)
  }
}

async function handleReindex() {
  if (!confirm('This will reprocess all documents. Are you sure?')) return
  isLoading.value = true
  actionMsg.value = 'Starting reindex...'
  try {
    await adminStore.reindexDocuments()
    actionMsg.value = 'Reindexing started in background'
  } catch (e) {
    actionMsg.value = 'Reindex failed'
  } finally {
    isLoading.value = false
    setTimeout(() => actionMsg.value = '', 3000)
  }
}

async function handleDeleteUser(userId: number) {
  if (!confirm('Delete this user and ALL their documents? This cannot be undone.')) return
  try {
    await adminStore.deleteUser(userId)
  } catch (e) {
    alert('Failed to delete user')
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
        <h2>Admin Console</h2>
      </div>
      
      <nav class="sidebar-nav">
        <button 
          class="nav-item" 
          :class="{ active: activeTab === 'dashboard' }"
          @click="activeTab = 'dashboard'"
        >
          <Activity class="h-4 w-4" />
          Dashboard
        </button>
        <button 
          class="nav-item" 
          :class="{ active: activeTab === 'users' }"
          @click="activeTab = 'users'"
        >
          <Users class="h-4 w-4" />
          Users
        </button>
      </nav>

      <div class="sidebar-footer">
        <Button variant="ghost" class="w-full justify-start text-muted-foreground" @click="emit('close')">
          <X class="h-4 w-4 mr-2" />
          Close Panel
        </Button>
      </div>
    </div>

    <div class="admin-content">
      <header class="content-header">
        <h1 class="page-title">{{ activeTab === 'dashboard' ? 'System Overview' : 'User Management' }}</h1>
        <div v-if="actionMsg" class="status-msg">{{ actionMsg }}</div>
      </header>

      <main class="content-body">
        <!-- Dashboard Tab -->
        <div v-if="activeTab === 'dashboard' && adminStore.stats" class="dashboard-grid">
          <div class="stat-card">
            <div class="stat-icon bg-blue-100 text-blue-600"><Database class="h-6 w-6" /></div>
            <div class="stat-info">
              <span class="stat-label">Documents</span>
              <span class="stat-value">{{ adminStore.stats.database.documents }}</span>
            </div>
          </div>
          
          <div class="stat-card">
            <div class="stat-icon bg-green-100 text-green-600"><Users class="h-6 w-6" /></div>
            <div class="stat-info">
              <span class="stat-label">Users</span>
              <span class="stat-value">{{ adminStore.stats.database.users }}</span>
            </div>
          </div>
          
          <div class="stat-card">
            <div class="stat-icon bg-purple-100 text-purple-600"><HardDrive class="h-6 w-6" /></div>
            <div class="stat-info">
              <span class="stat-label">Storage</span>
              <span class="stat-value">{{ formatBytes(adminStore.stats.storage.upload_dir_bytes) }}</span>
            </div>
          </div>

          <div class="system-actions">
            <h3>System Actions</h3>
            <div class="actions-grid">
              <div class="action-card">
                <h4>Data Backup</h4>
                <p>Export database and files as ZIP archive.</p>
                <Button @click="handleBackup" :disabled="isLoading">
                  <Download class="h-4 w-4 mr-2" /> Download Backup
                </Button>
              </div>
              
              <div class="action-card">
                <h4>Reindex Content</h4>
                <p>Re-run OCR and text extraction for all files.</p>
                <Button variant="outline" @click="handleReindex" :disabled="isLoading">
                  <RefreshCw class="h-4 w-4 mr-2" /> Start Reindexing
                </Button>
              </div>
            </div>
          </div>
        </div>

        <!-- Users Tab -->
        <div v-else-if="activeTab === 'users'" class="users-list">
          <div class="table-container">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Username</th>
                  <th>Email</th>
                  <th>Status</th>
                  <th>Role</th>
                  <th>Actions</th>
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
                      {{ user.is_active ? 'Active' : 'Inactive' }}
                    </span>
                  </td>
                  <td>{{ user.is_superuser ? 'Admin' : 'User' }}</td>
                  <td>
                    <button 
                      class="delete-btn" 
                      @click="handleDeleteUser(user.id)"
                      :disabled="user.is_superuser"
                      title="Delete User"
                    >
                      <Trash2 class="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
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
</style>
