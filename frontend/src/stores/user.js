import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useUserStore = defineStore('user', () => {
  const userId = ref(localStorage.getItem('user_id') || '')
  const username = ref(localStorage.getItem('username') || '')
  const role = ref(localStorage.getItem('role') || '')

  const loggedIn = computed(() => !!userId.value)
  const roleLabel = computed(() => {
    const map = { student: '学生', teacher: '教师', admin: '管理员' }
    return map[role.value] || role.value
  })

  function setLogin(data) {
    userId.value = String(data.id)
    username.value = data.username
    role.value = data.role
    localStorage.setItem('user_id', userId.value)
    localStorage.setItem('username', username.value)
    localStorage.setItem('role', role.value)
    localStorage.setItem('user', JSON.stringify(data))
  }

  function logout() {
    userId.value = ''
    username.value = ''
    role.value = ''
    localStorage.removeItem('user_id')
    localStorage.removeItem('username')
    localStorage.removeItem('role')
    localStorage.removeItem('user')
  }

  return { userId, username, role, loggedIn, roleLabel, setLogin, logout }
})
