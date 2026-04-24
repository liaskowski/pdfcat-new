<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import client from '@/api/client'
import { Folder, FileText, Users, Globe, ChevronRight, ChevronDown, Plus, Trash2, User } from 'lucide-vue-next'
import FolderDialog from './FolderDialog.vue'
import { useI18n } from '@/composables/useI18n'
import { useToast } from '@/composables/useToast'

interface PublicUser {
  id: number
  username: string
  email?: string
  avatar_url?: string
}

interface NavItem {
  id: string
  label: string
  icon: any
  type: 'root' | 'folder' | 'shared' | 'user'
  folderId?: number | null
  ownerId?: number | null
  viewMode?: string
  count?: number
  children?: NavItem[]
  isExpanded?: boolean
  canCreate?: boolean
  canDelete?: boolean
  avatarUrl?: string
}

const props = defineProps<{
  selectedFolderId?: number | null
  selectedViewMode?: string
}>()

const emit = defineEmits<{
  navigate: [viewMode: string, folderId: number | null, ownerId: number | null, path: string[]]
  folderCreate: []
  folderRefresh: []
}>()

const { t } = useI18n()
const toast = useToast()
const auth = useAuthStore()
const navItems = ref<NavItem[]>([])
const isLoading = ref(false)
const showFolderDialog = ref(false)
const createParentId = ref<number | null>(null)
const publicUsers = ref<PublicUser[]>([])
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const renamingFolderId = ref<number | null>(null)
const renameFolderName = ref('')
let lastClickTime = 0

async function loadNavigation() {
  isLoading.value = true
  try {
    const user = auth.user
    if (!user) return

    // Load my folders
    const myFoldersResponse = await client.get('/folders/', {
      params: { owner_id: user.id }
    })
    const myFolders: any[] = myFoldersResponse.data

    // Load shared folders
    const sharedFoldersResponse = await client.get('/folders/', {
      params: { public_only: true }
    })
    const sharedFolders: any[] = sharedFoldersResponse.data

    // Load public users
    try {
      const usersResponse = await client.get('/users/public')
      publicUsers.value = usersResponse.data
    } catch (e) {
      console.warn('Failed to load public users:', e)
      publicUsers.value = []
    }

    // Build tree structure
    const folders: NavItem[] = []

    // My Documents root
    folders.push({
      id: 'my-documents',
      label: t('nav.my_documents'),
      icon: FileText,
      type: 'root',
      viewMode: 'my',
      folderId: null,
      ownerId: null,
      children: buildFolderTree(myFolders, 'my'),
      isExpanded: true,
      canCreate: true
    })

    // Shared with Me
    const sharedChildren = buildFolderTree(sharedFolders, 'shared')

    // Add users as children
    const userItems: NavItem[] = publicUsers.value.map(u => ({
      id: `user-${u.id}`,
      label: u.username,
      icon: User,
      type: 'user' as const,
      viewMode: 'shared' as const,
      folderId: null,
      ownerId: u.id,
      avatarUrl: u.avatar_url,
    }))

    if (userItems.length > 0) {
      // Add a separator/heading for users
      sharedChildren.push({
        id: 'shared-users-separator',
        label: 'Users',
        icon: Users,
        type: 'root' as const,
        viewMode: undefined,
        folderId: null,
        ownerId: null,
        children: userItems,
        isExpanded: false,
      })
    }

    folders.push({
      id: 'shared',
      label: t('nav.shared'),
      icon: Users,
      type: 'root',
      viewMode: 'shared',
      folderId: null,
      ownerId: null,
      children: sharedChildren,
      isExpanded: false
    })

    // Community
    folders.push({
      id: 'community',
      label: t('nav.community'),
      icon: Globe,
      type: 'root',
      viewMode: 'community',
      folderId: null,
      ownerId: null,
      isExpanded: false
    })

    navItems.value = folders
  } catch (error) {
    console.error('Failed to load navigation:', error)
  } finally {
    isLoading.value = false
  }
}

function buildFolderTree(folders: any[], viewMode: string, parentId: number | null = null): NavItem[] {
  const children: NavItem[] = []
  
  const folderChildren = folders.filter(f => f.parent_id === parentId)
  
  for (const folder of folderChildren) {
    const node: NavItem = {
      id: `folder-${folder.id}`,
      label: folder.name,
      icon: Folder,
      type: 'folder',
      folderId: folder.id,
      ownerId: folder.owner_id,
      viewMode,
      children: buildFolderTree(folders, viewMode, folder.id),
      isExpanded: false,
      canCreate: viewMode === 'my',
      canDelete: viewMode === 'my' // Only delete own folders
    }
    children.push(node)
  }
  
  return children
}

function handleItemClick(item: NavItem) {
  if (item.children && item.children.length > 0) {
    item.isExpanded = !item.isExpanded
  }
  
  emit('navigate', item.viewMode || 'my', item.folderId || null, item.ownerId || null, [item.label])
}

function handleFolderClick(e: Event, item: NavItem) {
  e.stopPropagation()
  // Debounce: if this might be part of a double-click, delay navigation
  const now = Date.now()
  if (now - lastClickTime < 300) {
    return // Likely a double-click — skip navigation
  }
  lastClickTime = now

  // Delayed navigation to allow for possible second click
  setTimeout(() => {
    // If rename was started, don't navigate
    if (renamingFolderId.value === item.folderId) return
    handleItemClick(item)
  }, 300)
}

function toggleExpand(item: NavItem) {
  item.isExpanded = !item.isExpanded
}

function isSelected(item: NavItem): boolean {
  return props.selectedFolderId === item.folderId && 
         props.selectedViewMode === item.viewMode
}

function handleCreateFolder(e: Event, parentId: number | null = null) {
  e.stopPropagation()
  createParentId.value = parentId
  showFolderDialog.value = true
}

async function handleDeleteFolder(e: Event, folderId: number) {
  e.stopPropagation()
  if (confirm(t('folder.delete_confirm'))) {
    try {
      await client.delete(`/folders/${folderId}`)
      loadNavigation()
    } catch (e) {
      toast.error(t('folder.delete_failed'))
    }
  }
}

onMounted(() => {
  loadNavigation()
})

watch(() => auth.user, () => {
  if (auth.user) {
    loadNavigation()
  }
})

defineExpose({
  refresh: loadNavigation
})

function startRenameFolder(e: Event, item: NavItem) {
  e.stopPropagation()
  if (item.type !== 'folder' || !item.folderId) return
  renamingFolderId.value = item.folderId
  renameFolderName.value = item.label
}

async function saveFolderRename() {
  const folderId = renamingFolderId.value
  const newName = renameFolderName.value.trim()
  if (!folderId || !newName) { cancelFolderRename(); return }

  try {
    await client.patch(`/folders/${folderId}`, { name: newName })
    await loadNavigation()
  } catch (e) {
    console.error('Failed to rename folder:', e)
  } finally {
    renamingFolderId.value = null
  }
}

function cancelFolderRename() {
  renamingFolderId.value = null
}
</script>

<template>
  <div class="navigation-tree">
    <div class="nav-header">
      <h3 class="nav-title">{{ t('nav.folders') }}</h3>
      <button class="add-folder-btn" @click="handleCreateFolder($event, null)" :title="t('folder.new_root_folder')">
        <Plus class="h-4 w-4" />
      </button>
    </div>
    
    <div v-if="isLoading" class="loading">
      <div class="spinner"></div>
    </div>
    
    <div v-else class="nav-content">
      <div v-for="item in navItems" :key="item.id" class="nav-section">
        <div 
          class="nav-item root-item"
          :class="{ active: isSelected(item), expanded: item.isExpanded }"
          @click="handleItemClick(item)"
        >
          <button 
            v-if="item.children && item.children.length > 0"
            class="expand-btn"
            @click.stop="toggleExpand(item)"
          >
            <ChevronDown v-if="item.isExpanded" class="h-4 w-4" />
            <ChevronRight v-else class="h-4 w-4" />
          </button>
          <component :is="item.icon" class="nav-icon h-4 w-4" />
          <span class="nav-label">{{ item.label }}</span>
          
          <div class="item-actions">
            <button 
              v-if="item.canCreate"
              class="action-btn" 
              @click="handleCreateFolder($event, item.folderId)"
              :title="t('folder.new_subfolder')"
            >
              <Plus class="h-3 w-3" />
            </button>
          </div>
        </div>
        
        <div v-if="item.isExpanded && item.children" class="nav-children">
          <div
            v-for="child in item.children"
            :key="child.id"
            class="nav-item child-item"
            :class="{ active: isSelected(child), expanded: child.isExpanded }"
            @click="handleFolderClick($event, child)"
          >
            <button
              v-if="child.children && child.children.length > 0"
              class="expand-btn"
              @click.stop="toggleExpand(child)"
            >
              <ChevronDown v-if="child.isExpanded" class="h-4 w-4" />
              <ChevronRight v-else class="h-4 w-4" />
            </button>

            <!-- User avatar -->
            <template v-if="child.type === 'user'">
              <div class="user-avatar">
                <img v-if="child.avatarUrl" :src="`${API_BASE_URL}/${child.avatarUrl}`" :alt="child.label" class="avatar-img" />
                <User v-else class="h-4 w-4" />
              </div>
            </template>
            <!-- Folder icon -->
            <Folder v-else class="nav-icon h-4 w-4" />

            <span
              class="nav-label"
              :class="{ 'can-rename': child.type === 'folder' }"
              @dblclick="startRenameFolder($event, child)"
            >{{ child.label }}</span>

            <!-- Inline rename input for folders -->
            <input
              v-if="child.type === 'folder' && renamingFolderId === child.folderId"
              v-model="renameFolderName"
              class="folder-rename-input"
              @keydown.enter="saveFolderRename"
              @keydown.escape="cancelFolderRename"
              @blur="saveFolderRename"
            />

            <div class="item-actions" v-if="!(child.type === 'folder' && renamingFolderId === child.folderId)">
              <button 
                v-if="child.canCreate"
                class="action-btn" 
                @click="handleCreateFolder($event, child.folderId)"
                :title="t('folder.new_subfolder')"
              >
                <Plus class="h-3 w-3" />
              </button>
              <button 
                v-if="child.canDelete"
                class="action-btn delete-btn"
                @click="handleDeleteFolder($event, child.folderId!)"
                :title="t('folder.delete_folder')"
              >
                <Trash2 class="h-3 w-3" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <FolderDialog 
      v-model:open="showFolderDialog" 
      :parentId="createParentId"
      @created="loadNavigation"
    />
  </div>
</template>

<style scoped>
.navigation-tree {
  width: 100%;
  height: 100%;
  overflow-y: auto;
  padding: 0.75rem;
}

.nav-header {
  padding: 0.5rem 0.75rem;
  margin-bottom: 0.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.nav-title {
  font-size: 0.8125rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: hsl(var(--muted-foreground));
}

.add-folder-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.5rem;
  height: 1.5rem;
  border: none;
  background: transparent;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  border-radius: 0.25rem;
}

.add-folder-btn:hover {
  background-color: hsl(var(--accent));
  color: hsl(var(--foreground));
}

.loading {
  display: flex;
  justify-content: center;
  padding: 2rem;
}

.spinner {
  width: 1.5rem;
  height: 1.5rem;
  border: 2px solid hsl(var(--border));
  border-top-color: hsl(var(--primary));
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.nav-content {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.nav-section {
  display: flex;
  flex-direction: column;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  border-radius: 0.375rem;
  cursor: pointer;
  transition: all 0.15s ease;
  font-size: 0.9375rem;
  color: hsl(var(--foreground));
  position: relative;
}

.nav-item:hover {
  background-color: hsl(var(--accent));
}

.nav-item.active {
  background-color: hsl(var(--secondary));
  font-weight: 500;
}

.nav-item.root-item {
  font-weight: 500;
}

.nav-item.child-item {
  padding-left: 1.75rem;
}

.expand-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.25rem;
  height: 1.25rem;
  border: none;
  background: transparent;
  cursor: pointer;
  color: hsl(var(--muted-foreground));
  border-radius: 0.25rem;
}

.expand-btn:hover {
  background-color: hsl(var(--accent));
}

.nav-icon {
  color: hsl(var(--muted-foreground));
}

.nav-item.active .nav-icon {
  color: hsl(var(--primary));
}

.nav-label {
  flex: 1;
  text-align: left;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.nav-children {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.item-actions {
  display: none;
  align-items: center;
  gap: 0.25rem;
}

.nav-item:hover .item-actions {
  display: flex;
}

.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.25rem;
  height: 1.25rem;
  border: none;
  background: transparent;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  border-radius: 0.25rem;
}

.action-btn:hover {
  background-color: hsl(var(--background));
  color: hsl(var(--foreground));
}

.delete-btn:hover {
  color: hsl(var(--destructive));
}

.user-avatar {
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 50%;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: hsl(var(--muted));
  flex-shrink: 0;
}

.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.user-avatar .h-4 {
  color: hsl(var(--muted-foreground));
}

.can-rename {
  cursor: text;
}

.folder-rename-input {
  flex: 1;
  padding: 0.125rem 0.375rem;
  font-size: 0.875rem;
  border: 1px solid hsl(var(--primary));
  border-radius: 0.25rem;
  background-color: hsl(var(--background));
  color: hsl(var(--foreground));
  outline: none;
  box-shadow: 0 0 0 2px hsl(var(--primary) / 0.2);
  min-width: 0;
}
</style>
