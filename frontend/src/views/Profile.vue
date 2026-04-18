<template>
  <div>
    <h2 class="page-title">👤 个人中心</h2>

    <div class="stat-cards" v-if="profile">
      <div class="stat-card">
        <div class="stat-value">{{ profile.total_qa }}</div>
        <div class="stat-label">提问次数</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ profile.total_exercises }}</div>
        <div class="stat-label">做题数量</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ (profile.correct_rate * 100).toFixed(1) }}%</div>
        <div class="stat-label">正确率</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ profile.role === 'student' ? '学生' : profile.role }}</div>
        <div class="stat-label">身份角色</div>
      </div>
    </div>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">
      <!-- 用户信息 -->
      <div class="page-card">
        <h3 style="margin-bottom:16px;">基本信息</h3>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="用户名">{{ profile?.username }}</el-descriptions-item>
          <el-descriptions-item label="角色">{{ profile?.role === 'student' ? '学生' : profile?.role }}</el-descriptions-item>
          <el-descriptions-item label="注册时间">{{ profile?.created_at }}</el-descriptions-item>
        </el-descriptions>
      </div>

      <!-- 知识点掌握度 -->
      <div class="page-card">
        <h3 style="margin-bottom:16px;">知识点掌握度（Top 10 薄弱）</h3>
        <div v-for="m in masteryTop10" :key="m.kp_id" style="margin-bottom:12px;">
          <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
            <span style="font-size:13px;">{{ m.name }}</span>
            <span style="font-size:13px;color:#909399;">{{ (m.mastery * 100).toFixed(0) }}%</span>
          </div>
          <el-progress :percentage="m.mastery * 100" :stroke-width="12"
            :color="masteryColor(m.mastery)" />
        </div>
        <el-empty v-if="!masteryTop10.length" description="暂无学习数据" :image-size="40" />
      </div>
    </div>

    <!-- 问答历史 -->
    <div class="page-card" style="margin-top:20px;">
      <h3 style="margin-bottom:16px;">💬 最近问答记录</h3>
      <el-table :data="historyList" stripe size="small" v-loading="historyLoading">
        <el-table-column prop="created_at" label="时间" width="160" />
        <el-table-column prop="question" label="问题" min-width="300" show-overflow-tooltip />
        <el-table-column label="评分" width="120">
          <template #default="{ row }">
            <el-rate v-model="row.rating" :max="5" @change="rateHistory(row)" />
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!historyLoading && !historyList.length" description="暂无问答记录" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useUserStore } from '../stores/user'
import { userApi, qaApi, recommendApi } from '../api'
import { ElMessage } from 'element-plus'

const userStore = useUserStore()
const profile = ref(null)
const masteryTop10 = ref([])
const historyList = ref([])
const historyLoading = ref(false)

function masteryColor(mastery) {
  if (mastery >= 0.8) return '#67c23a'
  if (mastery >= 0.5) return '#e6a23c'
  return '#f56c6c'
}

async function loadProfile() {
  try {
    const res = await userApi.getProfile(Number(userStore.userId) || 1)
    if (res.code === 200) profile.value = res.data
  } catch (e) { /* ignore */ }
}

async function loadMastery() {
  try {
    const res = await recommendApi.getMastery(Number(userStore.userId) || 1)
    if (res.code === 200) masteryTop10.value = res.data.slice(0, 10)
  } catch (e) { /* ignore */ }
}

async function loadHistory() {
  historyLoading.value = true
  try {
    const res = await qaApi.getHistory(Number(userStore.userId) || 1)
    if (res.code === 200) historyList.value = res.data.list
  } catch (e) { /* ignore */ }
  historyLoading.value = false
}

async function rateHistory(row) {
  try {
    await qaApi.rate(row.id, row.rating)
    ElMessage.success('评分已保存')
  } catch (e) { ElMessage.error('评分失败') }
}

onMounted(() => {
  loadProfile()
  loadMastery()
  loadHistory()
})
</script>
