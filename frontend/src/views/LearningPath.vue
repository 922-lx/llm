<template>
  <div>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
      <h2 class="page-title" style="margin-bottom:0;">🗺️ 学习路径规划</h2>
      <el-button type="primary" @click="loadPath" :icon="Refresh">刷新路径</el-button>
    </div>

    <div class="page-card">
      <div style="display:flex;gap:12px;margin-bottom:20px;align-items:center;">
        <span style="font-size:14px;color:#606266;">目标知识点：</span>
        <el-input v-model="targetKp" placeholder="可选：输入目标知识点" style="width:240px;"
          clearable @keyup.enter="loadPath" />
      </div>

      <div v-if="pathData.path && pathData.path.length" class="path-steps">
        <div v-for="(step, idx) in pathData.path" :key="idx"
          :class="['path-step', stepClass(idx)]">

          <div class="step-dot">{{ step.status === 'done' ? '✓' : idx + 1 }}</div>

          <div class="step-content">
            <div class="step-title">{{ step.name }}</div>
            <div class="step-desc">
              <template v-if="step.status === 'done'">
                <span style="color:#67c23a;font-weight:500;">已完成 ✓</span>
              </template>
              <template v-else-if="step.status === 'current'">
                当前学习重点 ·
                <el-link type="primary" @click="askAbout(step.name)">点击提问</el-link>
                <el-button type="success" size="small" style="margin-left:8px;" @click="markComplete(idx)">
                  标记完成
                </el-button>
              </template>
              <template v-else>
                <span style="color:#909399;">🔒 待解锁（完成上一个知识点后解锁）</span>
              </template>
            </div>
          </div>

          <div v-if="idx < pathData.path.length - 1"
            style="color:#dcdfe6;font-size:20px;align-self:center;">
            ↓
          </div>
        </div>
      </div>

      <el-empty v-else-if="!loading" description="暂无学习路径数据" />

      <div v-if="pathData.weak_points && pathData.weak_points.length" style="margin-top:24px;">
        <h4 style="margin-bottom:12px;">⚠️ 薄弱知识点</h4>
        <el-tag v-for="wp in pathData.weak_points" :key="wp" type="danger" size="large"
          style="margin:4px;" @click="askAbout(wp)" class="clickable-tag">
          {{ wp }}
        </el-tag>
      </div>
    </div>

    <!-- 学习进度图表 -->
    <div class="page-card" style="margin-top:20px;">
      <h3 style="margin-bottom:16px;">📊 学习进度概览</h3>
      <div ref="progressChart" style="height:300px;"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { recommendApi } from '../api'
import { Refresh } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'

const router = useRouter()
const userStore = useUserStore()
const targetKp = ref('')
const pathData = ref({ path: [], weak_points: [], total_steps: 0 })
const loading = ref(false)
const progressChart = ref(null)

// 本地记录已完成的知识点（持久化到 localStorage）
const LOCAL_STORAGE_KEY = 'ds-learning-completed'

function getLocalCompleted() {
  try {
    return new Set(JSON.parse(localStorage.getItem(LOCAL_STORAGE_KEY) || '[]'))
  } catch {
    return new Set()
  }
}

function saveLocalCompleted(completedSet) {
  localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify([...completedSet]))
}

function stepClass(idx) {
  const steps = pathData.value.path
  if (!steps[idx]) return 'pending'
  if (steps[idx].status === 'done') return 'completed'
  if (steps[idx].status === 'current') return 'current'
  return 'pending'
}

function askAbout(name) {
  router.push({ path: '/chat', query: { q: name } })
}

function markComplete(idx) {
  const steps = pathData.value.path
  if (!steps[idx] || steps[idx].status !== 'current') return

  // 标记当前为完成
  steps[idx].status = 'done'

  // 解锁下一个：如果下一个存在且是 pending，则变为 current
  if (idx + 1 < steps.length && steps[idx + 1].status === 'pending') {
    steps[idx + 1].status = 'current'
  }

  // 保存到本地
  const completed = getLocalCompleted()
  completed.add(steps[idx].name)
  saveLocalCompleted(completed)

  ElMessage.success(`"${steps[idx].name}" 已标记为完成！下一个：${steps[idx + 1]?.name || '已全部完成'}`)

  // 更新进度图表
  nextTick(renderProgressChart)
}

async function loadPath() {
  loading.value = true
  try {
    const res = await recommendApi.getLearningPath(
      Number(userStore.userId) || 1,
      targetKp.value || undefined
    )
    console.log('[Path] 学习路径数据:', res)
    if (res.code === 200) {
      const mastered = await getMasteredSet()
      const localCompleted = getLocalCompleted()
      const path = (res.data.path || []).map((name, idx) => {
        if (mastered.has(name) || localCompleted.has(name)) {
          return { name, status: 'done' }
        }
        return { name, status: 'pending' }
      })

      // 串行解锁：找到第一个 pending，标记为 current
      let hasCurrent = false
      for (let i = 0; i < path.length; i++) {
        if (path[i].status === 'done') {
          continue
        }
        if (!hasCurrent) {
          path[i].status = 'current'
          hasCurrent = true
        }
        // 其余保持 pending
      }

      pathData.value = { ...res.data, path }
      nextTick(renderProgressChart)
    } else {
      ElMessage.warning('加载路径返回: ' + (res.message || '未知错误'))
    }
  } catch (e) {
    console.error('[Path] 加载失败:', e)
    ElMessage.error('加载学习路径失败: ' + (e.message || '网络错误'))
  }
  loading.value = false
}

async function getMasteredSet() {
  try {
    const res = await recommendApi.getMastery(Number(userStore.userId) || 1)
    if (res.code === 200) {
      return new Set(res.data.filter(m => m.mastery >= 0.8).map(m => m.name))
    }
  } catch (e) { /* ignore */ }
  return new Set()
}

function renderProgressChart() {
  if (!progressChart.value) return
  const chart = echarts.init(progressChart.value)

  const steps = pathData.value.path || []
  const done = steps.filter(s => s.status === 'done').length
  const total = steps.length
  const pct = total ? Math.round(done / total * 100) : 0

  // 根据实际路径分类
  const catMap = {
    '线性结构': ['数组', '链表', '栈', '队列'],
    '递归基础': ['递归'],
    '树形结构': ['树', '二叉树', '二叉搜索树', 'AVL树', '红黑树', '堆'],
    '图结构': ['图', 'BFS', 'DFS'],
    '排序算法': ['排序算法', '冒泡排序', '选择排序', '插入排序', '归并排序', '快速排序', '堆排序'],
    '查找算法': ['查找算法', '顺序查找', '二分查找', '哈希查找'],
    '算法设计': ['动态规划', '贪心算法', '分治算法'],
  }

  const categories = Object.keys(catMap)
  const values = categories.map(cat => {
    const kps = catMap[cat]
    const completedInCat = kps.filter(kp => {
      const step = steps.find(s => s.name === kp)
      return step && step.status === 'done'
    }).length
    return kps.length ? Math.round(completedInCat / kps.length * 100) : 0
  })

  chart.setOption({
    tooltip: { trigger: 'axis' },
    radar: {
      indicator: categories.map(c => ({ name: c, max: 100 })),
      shape: 'circle',
      splitArea: { areaStyle: { color: ['rgba(102,126,234,0.05)', 'rgba(102,126,234,0.1)'] } },
    },
    series: [{
      type: 'radar',
      data: [{
        value: values,
        name: '学习进度',
        areaStyle: { color: 'rgba(102,126,234,0.3)' },
        lineStyle: { color: '#667eea', width: 2 },
        itemStyle: { color: '#667eea' },
      }],
    }],
    graphic: [{
      type: 'text',
      left: 'center',
      bottom: 10,
      style: {
        text: `总进度：${done}/${total}（${pct}%）`,
        fontSize: 14,
        fill: '#606266',
      },
    }],
  })
}

onMounted(() => {
  loadPath()
  window.addEventListener('resize', () => progressChart.value && echarts.getInstanceByDom(progressChart.value)?.resize())
})
</script>

<style scoped>
.clickable-tag { cursor: pointer; transition: all 0.2s; }
.clickable-tag:hover { transform: scale(1.05); }
</style>
