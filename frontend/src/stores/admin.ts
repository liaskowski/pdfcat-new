import { defineStore } from 'pinia'
import { ref } from 'vue'
import client from '@/api/client'

export interface User {
  id: number
  username: string
  email: string
  is_active: boolean
  is_superuser: boolean
  created_at: string
}

export interface SystemStats {
  platform: string
  python_version: string
  database: {
    users: number
    documents: number
  }
  storage: {
    upload_dir_bytes: number
    upload_dir_path: string
  }
  system?: {
    cpu_percent: number
    ram_percent: number
    disk_usage_percent: number
  }
  timestamp: string
}

export const useAdminStore = defineStore('admin', () => {
  const users = ref<User[]>([])
  const stats = ref<SystemStats | null>(null)
  const loading = ref(false)

  async function fetchUsers() {
    loading.value = true
    try {
      const { data } = await client.get('/users/')
      users.value = data
    } finally {
      loading.value = false
    }
  }

  async function fetchStats() {
    try {
      const { data } = await client.get('/api/v1/admin/stats')
      stats.value = data
    } catch (e) {
      console.error('Failed to fetch stats', e)
    }
  }

  async function deleteUser(userId: number) {
    await client.delete(`/api/v1/admin/users/${userId}`)
    users.value = users.value.filter(u => u.id !== userId)
  }

  async function createBackup() {
    const response = await client.post('/api/v1/admin/backup', null, { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `backup_${new Date().toISOString()}.zip`)
    document.body.appendChild(link)
    link.click()
  }

  async function reindexDocuments() {
    await client.post('/api/v1/admin/reindex')
  }

  return {
    users,
    stats,
    loading,
    fetchUsers,
    fetchStats,
    deleteUser,
    createBackup,
    reindexDocuments
  }
})
