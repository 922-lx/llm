<template>
  <div class="login-page">
    <div class="login-card">
      <h2 style="text-align:center;margin-bottom:8px;">数据结构智能学习系统</h2>
      <p style="text-align:center;color:#909399;margin-bottom:32px;font-size:14px;">
        知识图谱 + 大语言模型 · 智能问答 · 个性化推荐
      </p>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="登录" name="login">
          <el-form :model="loginForm" @submit.prevent="handleLogin">
            <el-form-item>
              <el-input v-model="loginForm.username" placeholder="用户名" prefix-icon="User" size="large" />
            </el-form-item>
            <el-form-item>
              <el-input v-model="loginForm.password" type="password" placeholder="密码" prefix-icon="Lock" size="large"
                show-password @keyup.enter="handleLogin" />
            </el-form-item>
            <el-button type="primary" size="large" style="width:100%;" :loading="loading" @click="handleLogin">
              登 录
            </el-button>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="注册" name="register">
          <el-form :model="regForm" @submit.prevent="handleRegister">
            <el-form-item>
              <el-input v-model="regForm.username" placeholder="用户名" prefix-icon="User" size="large" />
            </el-form-item>
            <el-form-item>
              <el-input v-model="regForm.password" type="password" placeholder="密码" prefix-icon="Lock" size="large"
                show-password />
            </el-form-item>
            <el-form-item>
              <el-select v-model="regForm.role" style="width:100%;" size="large">
                <el-option label="学生" value="student" />
                <el-option label="教师" value="teacher" />
              </el-select>
            </el-form-item>
            <el-button type="success" size="large" style="width:100%;" :loading="loading" @click="handleRegister">
              注 册
            </el-button>
          </el-form>
        </el-tab-pane>
      </el-tabs>

      <p style="text-align:center;margin-top:16px;font-size:12px;color:#c0c4cc;">
        测试账号: student1 / 123456
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { userApi } from '../api'
import { ElMessage } from 'element-plus'

const router = useRouter()
const userStore = useUserStore()
const activeTab = ref('login')
const loading = ref(false)

const loginForm = ref({ username: '', password: '' })
const regForm = ref({ username: '', password: '', role: 'student' })

async function handleLogin() {
  if (!loginForm.value.username || !loginForm.value.password) {
    return ElMessage.warning('请输入用户名和密码')
  }
  loading.value = true
  try {
    const res = await userApi.login(loginForm.value)
    if (res.code === 200) {
      userStore.setLogin(res.data)
      ElMessage.success('登录成功')
      router.push('/chat')
    } else {
      ElMessage.error(res.message || '登录失败')
    }
  } catch (e) {
    ElMessage.error('网络错误，请检查后端服务是否启动')
  }
  loading.value = false
}

async function handleRegister() {
  if (!regForm.value.username || !regForm.value.password) {
    return ElMessage.warning('请输入用户名和密码')
  }
  loading.value = true
  try {
    const res = await userApi.register(regForm.value)
    if (res.code === 200) {
      ElMessage.success('注册成功，请登录')
      activeTab.value = 'login'
      loginForm.value.username = regForm.value.username
    } else {
      ElMessage.error(res.message || '注册失败')
    }
  } catch (e) {
    ElMessage.error('网络错误')
  }
  loading.value = false
}
</script>
