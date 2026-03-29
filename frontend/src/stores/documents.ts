import { defineStore } from 'pinia'
import { ref } from 'vue'
import client from '@/api/client'

export interface Category {
  id: number
  name: string
}

export interface FileType {
  id: number
  name: string
}

export interface FileHistory {
  id: number
  version: number
  filename: string
  change_date: string
  changed_by: string
  notes?: string
}

export interface Document {
  id: number
  title: string
  filename: string
  upload_date: string
  owner_id: number
  owner_username?: string
  owner_email?: string
  owner_avatar_url?: string
  file_size?: number
  tags?: string
  category_id?: number
  category?: Category
  file_type_id?: number
  file_type?: FileType
  folder_id?: number | null
  notes?: string
  is_private: boolean
  is_public: boolean
  is_public_edit: boolean
  is_read_only: boolean
  encryption_key?: string
  ocr_status?: string
}

export interface Folder {
  id: number
  name: string
  parent_id: number | null
  owner_id: number
  is_public: boolean
  created_at?: string
}

export const useDocumentStore = defineStore('documents', () => {
  const documents = ref<Document[]>([])
  const folders = ref<Folder[]>([])
  const categories = ref<Category[]>([])
  const fileTypes = ref<FileType[]>([])
  const loading = ref(false)
  const searchQuery = ref('')
  const currentViewMode = ref('my')
  const currentFolderId = ref<number | null>(null)
  const currentOwnerId = ref<number | null>(null)

  // Document Methods
  async function fetchDocuments(viewMode = 'my', folderId: number | null = null, ownerId: number | null = null) {
    loading.value = true
    try {
      const { data } = await client.get('/documents/', {
        params: { 
          view_mode: viewMode,
          folder_id: folderId,
          owner_id: ownerId,
          limit: 500
        }
      })
      documents.value = data
      currentViewMode.value = viewMode
      currentFolderId.value = folderId
      currentOwnerId.value = ownerId
    } finally {
      loading.value = false
    }
  }

  async function uploadDocument(formData: FormData) {
    const { data } = await client.post('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    documents.value.unshift(data)
    return data
  }

  async function updateDocument(documentId: number, data: Partial<Document>) {
    const { data: updated } = await client.put(`/documents/${documentId}`, data)
    const index = documents.value.findIndex(d => d.id === documentId)
    if (index !== -1) {
      documents.value[index] = { ...documents.value[index], ...updated }
    }
    return updated
  }

  async function deleteDocument(documentId: number) {
    await client.delete(`/documents/${documentId}`)
    documents.value = documents.value.filter(d => d.id !== documentId)
  }

  async function duplicateDocument(documentId: number, folderId?: number) {
    const params = folderId ? { folder_id: folderId } : {}
    const { data } = await client.post(`/documents/${documentId}/duplicate`, null, { params })
    documents.value.unshift(data)
    return data
  }

  async function fetchDocumentHistory(documentId: number): Promise<FileHistory[]> {
    const { data } = await client.get(`/documents/${documentId}/history`)
    return data
  }

  // Folder Methods
  async function fetchFolders(ownerId?: number, publicOnly = false) {
    try {
      const params: any = {}
      if (ownerId !== undefined) params.owner_id = ownerId
      if (publicOnly) params.public_only = true
      
      const { data } = await client.get('/folders/', { params })
      folders.value = data
      return data
    } catch (error) {
      console.error('Failed to fetch folders:', error)
      return []
    }
  }

  async function createFolder(name: string, parentId: number | null = null, isPublic = false) {
    const { data } = await client.post('/folders/', {
      name,
      parent_id: parentId,
      is_public: isPublic
    })
    folders.value.push(data)
    return data
  }

  async function updateFolder(folderId: number, data: Partial<Folder>) {
    const { data: updated } = await client.patch(`/folders/${folderId}`, data)
    const index = folders.value.findIndex(f => f.id === folderId)
    if (index !== -1) {
      folders.value[index] = updated
    }
    return updated
  }

  async function deleteFolder(folderId: number) {
    await client.delete(`/folders/${folderId}`)
    folders.value = folders.value.filter(f => f.id !== folderId)
  }

  // Categories & Types
  async function fetchMetadata() {
    try {
      const [cats, types] = await Promise.all([
        client.get('/categories/'),
        client.get('/file_types/')
      ])
      categories.value = cats.data
      fileTypes.value = types.data
    } catch (error) {
      console.error('Failed to fetch metadata:', error)
    }
  }

  // Search
  async function searchDocuments(q: string) {
    loading.value = true
    try {
      const { data } = await client.get('/search', { params: { q } })
      documents.value = data
      return data
    } finally {
      loading.value = false
    }
  }

  async function getSuggestions(q: string): Promise<string[]> {
    const { data } = await client.get('/suggestions', { params: { q } })
    return data
  }

  function clearDocuments() {
    documents.value = []
  }

  return { 
    documents, 
    folders,
    categories,
    fileTypes,
    loading, 
    searchQuery,
    currentViewMode,
    currentFolderId,
    currentOwnerId,
    fetchDocuments, 
    fetchFolders,
    createFolder,
    updateFolder,
    deleteFolder,
    uploadDocument, 
    updateDocument,
    deleteDocument,
    duplicateDocument,
    fetchDocumentHistory,
    fetchMetadata,
    searchDocuments,
    getSuggestions,
    clearDocuments
  }
})
