<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import client from '@/api/client'
import { Folder, FileText, Users, Globe, ChevronRight, ChevronDown, Plus, Trash2 } from 'lucide-vue-next'
import FolderDialog from './FolderDialog.vue'
import { useI18n } from '@/composables/useI18n'

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
const auth = useAuthStore()
const navItems = ref<NavItem[]>([])
const isLoading = ref(false)
const showFolderDialog = ref(false)
const createParentId = ref<number | null>(null)

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

    // Shared with me
    folders.push({
      id: 'shared',
      label: t('nav.shared'),
      icon: Users,
      type: 'root',
      viewMode: 'shared',
      folderId: null,
      ownerId: null,
      children: buildFolderTree(sharedFolders, 'shared'),
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
  handleItemClick(item)
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
  if (confirm('Are you sure you want to delete this folder? All contents will be deleted.')) {
    try {
      await client.delete(`/folders/${folderId}`)
      loadNavigation()
    } catch (e) {
      alert('Failed to delete folder')
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
</script>

<template>
  <div class="navigation-tree">
    <div class="nav-header">
      <h3 class="nav-title">{{ t('nav.folders') }}</h3>
      <button class="add-folder-btn" @click="handleCreateFolder($event, null)" title="New Root Folder">
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
              title="New Subfolder"
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
            <Folder class="nav-icon h-4 w-4" />
            <span class="nav-label">{{ child.label }}</span>
            
            <div class="item-actions">
              <button 
                v-if="child.canCreate"
                class="action-btn" 
                @click="handleCreateFolder($event, child.folderId)"
                title="New Subfolder"
              >
                <Plus class="h-3 w-3" />
              </button>
              <button 
                v-if="child.canDelete"
                class="action-btn delete-btn" 
                @click="handleDeleteFolder($event, child.folderId!)"
                title="Delete Folder"
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
  font-size: 0.75rem;
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
  font-size: 0.875rem;
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
</style>
