<template>
  <div class="layout-container" v-if="userStore.loggedIn">
    <!-- 侧边栏 -->
    <aside class="sidebar">
      <div class="logo">
        <h2>DS-KG-LLM</h2>
        <p>数据结构智能学习系统</p>
      </div>
      <nav class="nav-menu">
        <router-link to="/chat" class="nav-item" active-class="active">
          <el-icon><ChatDotRound /></el-icon>
          <span>智能问答</span>
        </router-link>
        <router-link to="/knowledge" class="nav-item" active-class="active">
          <el-icon><Share /></el-icon>
          <span>知识图谱</span>
        </router-link>
        <router-link to="/exercises" class="nav-item" active-class="active">
          <el-icon><Document /></el-icon>
          <span>习题推荐</span>
        </router-link>
        <router-link to="/path" class="nav-item" active-class="active">
          <el-icon><MapLocation /></el-icon>
          <span>学习路径</span>
        </router-link>
        <router-link to="/profile" class="nav-item" active-class="active">
          <el-icon><User /></el-icon>
          <span>个人中心</span>
        </router-link>
      </nav>
    </aside>

    <!-- 主内容 -->
    <div class="main-content">
      <header class="top-bar">
        <span style="font-size:15px;font-weight:500;">
          {{ currentRouteTitle }}
        </span>
        <div style="display:flex;align-items:center;gap:12px;">
          <el-tag type="success" size="small">{{ userStore.roleLabel }}</el-tag>
          <span style="font-size:14px;">{{ userStore.username }}</span>
          <el-button type="danger" text size="small" @click="logout">退出</el-button>
        </div>
      </header>
      <div class="page-content">
        <router-view />
      </div>
    </div>
  </div>

  <!-- 未登录 -->
  <router-view v-else />
</template>

<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from './stores/user'
import { ChatDotRound, Share, Document, MapLocation, User } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const routeTitles = {
  '/chat': '智能问答',
  '/knowledge': '知识图谱',
  '/exercises': '习题推荐',
  '/path': '学习路径',
  '/profile': '个人中心',
}

const currentRouteTitle = computed(() => routeTitles[route.path] || '数据结构智能学习系统')

function logout() {
  userStore.logout()
  router.push('/login')
}
</script>
