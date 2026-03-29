import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import client from '@/api/client'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<any>(null)
  const token = ref(localStorage.getItem('token'))
  const isAuthenticated = computed(() => !!token.value)

  async function login(username: string, password: string) {
    const formData = new FormData()
    formData.append('username', username)
    formData.append('password', password)

    const { data } = await client.post('/auth/token', formData)
    token.value = data.access_token
    localStorage.setItem('token', data.access_token)
    await fetchUser()
  }

  async function fetchUser() {
    if (!token.value) return
    try {
      const { data } = await client.get('/users/me')
      user.value = data
    } catch (e) {
      logout()
    }
  }

  function logout() {
    user.value = null
    token.value = null
    localStorage.removeItem('token')
  }

  return { user, token, isAuthenticated, login, fetchUser, logout }
})
