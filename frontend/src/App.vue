<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useDocumentStore } from '@/stores/documents'
import type { Document } from '@/stores/documents'
import NavigationTree from '@/components/NavigationTree.vue'
import FileGrid from '@/components/FileGrid.vue'
import PreviewPanel from '@/components/PreviewPanel.vue'
import Breadcrumbs from '@/components/Breadcrumbs.vue'
import UploadDialog from '@/components/UploadDialog.vue'
import EditDialog from '@/components/EditDialog.vue'
import SecurePdfViewer from '@/components/SecurePdfViewer.vue'
import SearchBar from '@/components/SearchBar.vue'
import AdminPanel from '@/components/AdminPanel.vue'
import ProfileDialog from '@/components/ProfileDialog.vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { LogOut, Menu, X, FileText, Shield, Moon, Sun, Languages, User } from 'lucide-vue-next'
import { useI18n } from '@/composables/useI18n'

const auth = useAuthStore()
const docStore = useDocumentStore()
const { setLocale, locale } = useI18n()

// State
const username = ref('')
const password = ref('')
const isLoggingIn = ref(false)
const isSidebarOpen = ref(true)
const isPreviewOpen = ref(true)
const showUploadDialog = ref(false)
const showEditDialog = ref(false)
const showPdfViewer = ref(false)
const showAdminPanel = ref(false)
const showProfileDialog = ref(false)
const isDark = ref(document.documentElement.classList.contains('dark'))

function toggleTheme() {
  isDark.value = !isDark.value
  if (isDark.value) {
    document.documentElement.classList.add('dark')
    localStorage.setItem('theme', 'dark')
  } else {
    document.documentElement.classList.remove('dark')
    localStorage.setItem('theme', 'light')
  }
}

function toggleLanguage() {
  const newLocale = locale.value === 'en' ? 'ru' : 'en'
  setLocale(newLocale)
}

// Navigation state
const currentViewMode = ref('my')
const currentFolderId = ref<number | null>(null)
const currentOwnerId = ref<number | null>(null)
const pathSegments = ref<Array<{ label: string; folderId?: number | null; viewMode?: string; ownerId?: number | null }>>([])

// Selected document
const selectedDocument = ref<Document | null>(null)

// Login
async function handleLogin() {
  isLoggingIn.value = true
  try {
    await auth.login(username.value, password.value)
    await docStore.fetchDocuments('my')
  } catch (e) {
    alert('Login failed')
  } finally {
    isLoggingIn.value = false
  }
}

// Navigation
function handleNavigation(viewMode: string, folderId: number | null, ownerId: number | null, labels: string[]) {
  currentViewMode.value = viewMode
  currentFolderId.value = folderId
  currentOwnerId.value = ownerId
  pathSegments.value = labels.map((label, i) => ({
    label,
    folderId: i === labels.length - 1 ? folderId : null,
    viewMode: i === labels.length - 1 ? viewMode : undefined,
    ownerId: i === labels.length - 1 ? ownerId : undefined
  }))
  
  docStore.fetchDocuments(viewMode, folderId, ownerId)
  selectedDocument.value = null
}

function handleBreadcrumbClick(segment: any) {
  const viewMode = segment.viewMode || currentViewMode.value
  const folderId = segment.folderId !== undefined ? segment.folderId : currentFolderId.value
  const ownerId = segment.ownerId !== undefined ? segment.ownerId : currentOwnerId.value
  
  docStore.fetchDocuments(viewMode, folderId, ownerId)
  selectedDocument.value = null
}

// Document actions
function handleDocumentSelect(doc: any) {
  selectedDocument.value = doc
  isPreviewOpen.value = true
}

function handleDocumentOpen(doc: any) {
  selectedDocument.value = doc
  showPdfViewer.value = true
}

function handleDocumentDelete(doc: any) {
  if (confirm(`Are you sure you want to delete "${doc.title}"?`)) {
    docStore.deleteDocument(doc.id)
    if (selectedDocument.value?.id === doc.id) {
      selectedDocument.value = null
    }
  }
}

function handleDocumentEdit(doc: any) {
  selectedDocument.value = doc
  showEditDialog.value = true
}

function handleEditTags(doc: any) {
  selectedDocument.value = doc
  showEditDialog.value = true
}

function handleTagClick(tag: string) {
  docStore.searchQuery = tag
  docStore.searchDocuments(tag)
}

function handleUploadComplete() {
  docStore.fetchDocuments(currentViewMode.value, currentFolderId.value, currentOwnerId.value)
}

function handleEditSaved() {
  docStore.fetchDocuments(currentViewMode.value, currentFolderId.value, currentOwnerId.value)
}

function toggleSidebar() {
  isSidebarOpen.value = !isSidebarOpen.value
}

// Logout
function handleLogout() {
  auth.logout()
  docStore.clearDocuments()
  selectedDocument.value = null
}

onMounted(async () => {
  const savedTheme = localStorage.getItem('theme')
  if (savedTheme === 'dark' || (!savedTheme && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
    isDark.value = true
    document.documentElement.classList.add('dark')
  }

  if (auth.isAuthenticated) {
    await auth.fetchUser()
    await Promise.all([
      docStore.fetchDocuments('my'),
      docStore.fetchMetadata(),
      docStore.fetchFolders()
    ])
    pathSegments.value = [{ label: 'My Documents', viewMode: 'my' }]
  }
})
</script>

<template>
  <div class="min-h-screen bg-background font-sans antialiased">
    <!-- Login View -->
    <div v-if="!auth.isAuthenticated" class="flex items-center justify-center min-h-screen">
      <Card class="w-87.5">
        <CardHeader>
          <CardTitle>Login to PDF Library</CardTitle>
        </CardHeader>
        <CardContent>
          <form @submit.prevent="handleLogin" class="space-y-4">
            <div class="space-y-2">
              <label for="username" class="text-sm font-medium">Username</label>
              <Input id="username" v-model="username" placeholder="admin" required />
            </div>
            <div class="space-y-2">
              <label for="password" class="text-sm font-medium">Password</label>
              <Input id="password" v-model="password" type="password" required />
            </div>
            <Button type="submit" class="w-full" :disabled="isLoggingIn">
              Login
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>

    <!-- Main Application -->
    <div v-else class="flex flex-col h-screen overflow-hidden">
      <!-- Header -->
      <header class="header">
        <div class="header-left">
          <Button variant="ghost" size="sm" @click="toggleSidebar" class="md:hidden">
            <Menu v-if="!isSidebarOpen" class="h-5 w-5" />
            <X v-else class="h-5 w-5" />
          </Button>
          <h1 class="logo">
            <FileText class="logo-icon" />
            pdfCAT
          </h1>
        </div>
        
        <div class="header-center">
          <SearchBar 
            v-model="docStore.searchQuery"
            @search="docStore.searchDocuments"
            @clear="docStore.fetchDocuments(currentViewMode, currentFolderId, currentOwnerId)"
          />
        </div>
        
        <div class="header-right">
          <Button 
            variant="ghost" 
            size="sm" 
            @click="toggleTheme" 
            :title="isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode'"
          >
            <Sun v-if="isDark" class="h-4 w-4" />
            <Moon v-else class="h-4 w-4" />
          </Button>
          <Button 
            variant="ghost" 
            size="sm" 
            @click="toggleLanguage" 
            :title="locale === 'en' ? 'Switch to Russian' : 'Switch to English'"
          >
            <Languages class="h-4 w-4" />
          </Button>
          <Button 
            v-if="auth.user?.is_superuser" 
            variant="ghost" 
            size="sm" 
            @click="showAdminPanel = true"
            title="Admin Panel"
          >
            <Shield class="h-4 w-4" />
          </Button>
          <button 
            class="user-profile-btn" 
            @click="showProfileDialog = true"
            title="User Settings"
          >
            <span class="user-name">{{ auth.user?.username }}</span>
            <User class="h-4 w-4 ml-2" />
          </button>
          <Button variant="ghost" size="sm" @click="handleLogout" title="Logout">
            <LogOut class="h-4 w-4" />
          </Button>
        </div>
      </header>

      <!-- Main Content -->
      <div class="app-body">
        <!-- Sidebar -->
        <aside 
          class="sidebar"
          :class="{ 'sidebar-closed': !isSidebarOpen }"
        >
          <NavigationTree
            :selectedFolderId="currentFolderId"
            :selectedViewMode="currentViewMode"
            @navigate="handleNavigation"
          />
        </aside>

        <!-- Center Content -->
        <main class="main-content">
          <Breadcrumbs 
            :pathSegments="pathSegments"
            @navigate="handleBreadcrumbClick"
          />
          
          <FileGrid
            :viewMode="currentViewMode"
            :folderId="currentFolderId"
            :ownerId="currentOwnerId"
            :searchQuery="docStore.searchQuery"
            @upload="showUploadDialog = true"
            @documentSelect="handleDocumentSelect"
            @documentOpen="handleDocumentOpen"
            @documentDelete="handleDocumentDelete"
          />
        </main>

        <!-- Preview Panel -->
        <aside
          v-if="isPreviewOpen"
          class="preview-panel"
        >
          <PreviewPanel
            :document="selectedDocument"
            @open="handleDocumentOpen"
            @download="handleDocumentOpen"
            @delete="handleDocumentDelete"
            @edit="handleDocumentEdit"
            @editTags="handleEditTags"
            @tagClick="handleTagClick"
            @close="isPreviewOpen = false"
          />
        </aside>
      </div>
    </div>

    <!-- Upload Dialog -->
    <UploadDialog
      v-model:open="showUploadDialog"
      @uploaded="handleUploadComplete"
    />

    <!-- Edit Dialog -->
    <EditDialog
      v-model:open="showEditDialog"
      :document="selectedDocument"
      @saved="handleEditSaved"
    />

    <!-- Admin Panel -->
    <AdminPanel 
      v-if="showAdminPanel" 
      @close="showAdminPanel = false" 
    />

    <ProfileDialog 
      v-model:open="showProfileDialog" 
    />

    <!-- PDF Viewer Modal -->
    <div v-if="showPdfViewer && selectedDocument" class="pdf-viewer-modal">
      <SecurePdfViewer
        :documentId="selectedDocument.id"
        :visible="showPdfViewer"
        @close="showPdfViewer = false"
      />
    </div>
  </div>
</template>

<style scoped>
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1.25rem;
  border-bottom: 1px solid hsl(var(--border));
  background-color: hsl(var(--background));
  height: 60px;
  flex-shrink: 0;
}

.header-left,
.header-right {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.header-center {
  flex: 1;
  display: flex;
  justify-content: center;
  max-width: 600px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.25rem;
  font-weight: 700;
  color: hsl(var(--foreground));
  margin: 0;
}

.logo-icon {
  color: hsl(var(--primary));
}

.user-name {
  font-size: 0.875rem;
  color: hsl(var(--foreground));
  font-weight: 500;
}

.user-profile-btn {
  display: flex;
  align-items: center;
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.5rem;
  border-radius: 0.375rem;
  transition: background-color 0.2s;
  color: hsl(var(--muted-foreground));
}

.user-profile-btn:hover {
  background-color: hsl(var(--accent));
  color: hsl(var(--foreground));
}

.app-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.sidebar {
  width: 260px;
  border-right: 1px solid hsl(var(--border));
  background-color: hsl(var(--background));
  overflow: hidden;
  transition: width 0.2s ease;
  flex-shrink: 0;
}

.sidebar-closed {
  width: 0;
  border-right: none;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

.preview-panel {
  width: 320px;
  border-left: 1px solid hsl(var(--border));
  background-color: hsl(var(--background));
  overflow: hidden;
  flex-shrink: 0;
  transition: width 0.2s ease;
}

.pdf-viewer-modal {
  position: fixed;
  inset: 0;
  background-color: hsl(var(--background));
  z-index: 100;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

@media (max-width: 768px) {
  .sidebar {
    position: absolute;
    left: 0;
    top: 60px;
    bottom: 0;
    z-index: 50;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }

  .sidebar-closed {
    transform: translateX(-100%);
  }

  .preview-panel {
    display: none;
  }
}
</style>
