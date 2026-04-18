<template>
  <div>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
      <h2 class="page-title" style="margin-bottom:0;">📚 个性化习题推荐</h2>
      <el-button type="primary" @click="refreshExercises" :icon="Refresh" :loading="loading">换一批</el-button>
    </div>

    <div class="stat-cards" v-if="masteryData.length">
      <div class="stat-card">
        <div class="stat-value">{{ masteryData.length }}</div>
        <div class="stat-label">已学知识点</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ masteredCount }}</div>
        <div class="stat-label">已掌握</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ weakCount }}</div>
        <div class="stat-label">需加强</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ masteryRate }}%</div>
        <div class="stat-label">掌握率</div>
      </div>
    </div>

    <div v-loading="loading">
      <div v-for="(ex, idx) in exerciseList" :key="ex.id + '-' + refreshKey" class="exercise-card">
        <!-- 题目头部 -->
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px;">
          <div style="display:flex;gap:6px;flex-shrink:0;">
            <el-tag :type="typeTag(ex.type)" size="small">{{ ex.type }}</el-tag>
            <el-tag type="warning" size="small">难度 {{ '★'.repeat(ex.difficulty) }}</el-tag>
            <el-tag v-if="ex.course" size="small" type="info">{{ ex.course }}</el-tag>
          </div>
          <el-tag v-if="ex.answered" :type="ex.isCorrect ? 'success' : 'danger'" size="small">
            {{ ex.isCorrect === true ? '✓ 回答正确' : ex.isCorrect === false ? '✗ 回答错误' : '已查看答案' }}
          </el-tag>
          <el-tag v-else type="info" size="small">未作答</el-tag>
        </div>

        <!-- 题干 -->
        <div class="ex-title">{{ ex.title }}</div>

        <!-- ====== 选择题 ====== -->
        <template v-if="ex.type === '选择' && ex.options && ex.options.length">
          <div class="ex-options">
            <div
              v-for="opt in ex.options" :key="opt.label"
              :class="getChoiceClass(idx, opt.label)"
              @click="!ex.answered && pickChoice(idx, opt.label)"
            >
              <span class="opt-label">{{ opt.label }}</span>
              <span class="opt-text">{{ opt.text }}</span>
              <span v-if="ex.answered && opt.label === ex.correctOption" style="margin-left:auto;color:#67c23a;">✓</span>
              <span v-if="ex.answered && opt.label === ex.userChoice && opt.label !== ex.correctOption" style="margin-left:auto;color:#f56c6c;">✗</span>
            </div>
          </div>
          <div v-if="!ex.answered && ex.userChoice" style="margin-top:12px;">
            <el-button type="primary" @click="submitChoice(idx)">提交答案</el-button>
          </div>
        </template>

        <!-- ====== 填空题 ====== -->
        <template v-if="ex.type === '填空' && !ex.answered">
          <div style="margin-top:14px;display:flex;gap:10px;align-items:center;flex-wrap:wrap;">
            <el-input
              v-model="ex.userInput"
              placeholder="请在此输入答案..."
              size="large"
              clearable
              style="width:400px;"
              @keyup.enter="submitFill(idx)"
            />
            <el-button type="primary" size="large" @click="submitFill(idx)"
              :disabled="!ex.userInput || !ex.userInput.trim()">
              提交答案
            </el-button>
          </div>
        </template>

        <!-- ====== 编程/简答题 ====== -->
        <template v-if="(ex.type === '编程' || ex.type === '简答') && !ex.answered">
          <div style="margin-top:14px;">
            <el-input
              v-model="ex.userInput"
              type="textarea"
              :rows="4"
              :placeholder="ex.type === '编程' ? '请写出你的代码或思路...' : '请输入你的回答...'"
              style="width:100%;max-width:640px;"
            />
            <div style="margin-top:10px;display:flex;gap:8px;">
              <el-button type="primary" @click="submitText(idx)"
                :disabled="!ex.userInput || !ex.userInput.trim()">
                提交答案
              </el-button>
              <el-button @click="skipEx(idx)">跳过，直接看答案</el-button>
            </div>
          </div>
        </template>

        <!-- ====== 作答后：答案+解析+反馈 ====== -->
        <div v-if="ex.answered" class="ex-result">
          <div class="result-section">
            <div class="result-label">📌 参考答案</div>
            <div class="result-content">{{ ex.answer || '暂无参考答案' }}</div>
          </div>
          <div v-if="ex.analysis" class="result-section">
            <div class="result-label">💡 解析</div>
            <div class="result-content">{{ ex.analysis }}</div>
          </div>
          <div v-if="ex.userDisplay" class="result-section">
            <div class="result-label">📝 你的回答</div>
            <div class="result-content">{{ ex.userDisplay }}</div>
          </div>
          <div style="margin-top:12px;display:flex;gap:8px;">
            <el-button size="small" type="success" @click="markCorrect(ex.id)">
              这道我做对了 ✓
            </el-button>
            <el-button size="small" type="danger" @click="markWrong(ex.id)">
              这道我做错了 ✗
            </el-button>
          </div>
        </div>
      </div>

      <el-empty v-if="!loading && exerciseList.length === 0" description="暂无推荐习题，请先使用问答功能积累学习记录" />
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useUserStore } from '../stores/user'
import { recommendApi } from '../api'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'

const userStore = useUserStore()
const loading = ref(false)
const refreshKey = ref(0)
const exerciseList = reactive([])   // 用 reactive 确保内部属性变更也是响应式的
const masteryData = ref([])

const masteredCount = computed(() => masteryData.value.filter(m => m.mastery >= 0.8).length)
const weakCount = computed(() => masteryData.value.filter(m => m.mastery < 0.5).length)
const masteryRate = computed(() => {
  if (!masteryData.value.length) return 0
  return Math.round(masteryData.value.reduce((s, m) => s + m.mastery, 0) / masteryData.value.length * 100)
})

function typeTag(type) {
  const map = { '选择': '', '填空': 'success', '编程': 'warning', '简答': 'info' }
  return map[type] || ''
}

// ─── 选择题逻辑 ───
function pickChoice(idx, label) {
  exerciseList[idx].userChoice = label
}

function getChoiceClass(idx, label) {
  const ex = exerciseList[idx]
  if (!ex.answered) {
    return 'ex-option ' + (ex.userChoice === label ? 'ex-option-selected' : 'ex-option-default')
  }
  if (label === ex.correctOption) return 'ex-option ex-option-correct'
  if (label === ex.userChoice) return 'ex-option ex-option-wrong'
  return 'ex-option ex-option-default'
}

function submitChoice(idx) {
  const ex = exerciseList[idx]
  if (!ex.userChoice) return
  // 解析正确选项
  const ans = (ex.answer || '').trim()
  let correct = ''
  const m = ans.match(/^([A-D])[\.\。\s]/i)
  if (m) {
    correct = m[1].toUpperCase()
  } else if (/^[A-D]$/i.test(ans)) {
    correct = ans.toUpperCase()
  } else {
    for (const opt of (ex.options || [])) {
      if (ans.includes(opt.text) || opt.text.includes(ans)) {
        correct = opt.label
        break
      }
    }
  }
  ex.correctOption = correct
  ex.isCorrect = ex.userChoice.toUpperCase() === correct
  ex.userDisplay = ex.userChoice
  ex.answered = true
}

// ─── 填空题逻辑 ───
function submitFill(idx) {
  const ex = exerciseList[idx]
  if (!ex.userInput || !ex.userInput.trim()) return
  ex.userDisplay = ex.userInput.trim()
  ex.answered = true
  ex.isCorrect = null
}

// ─── 编程/简答逻辑 ───
function submitText(idx) {
  const ex = exerciseList[idx]
  if (!ex.userInput || !ex.userInput.trim()) return
  ex.userDisplay = ex.userInput.trim()
  ex.answered = true
  ex.isCorrect = null
}

function skipEx(idx) {
  const ex = exerciseList[idx]
  ex.userDisplay = ''
  ex.answered = true
  ex.isCorrect = null
}

// ─── 数据加载 ───
async function refreshExercises() {
  refreshKey.value++
  await loadExercises()
}

async function loadExercises() {
  loading.value = true
  exerciseList.splice(0, exerciseList.length) // 清空
  try {
    const userId = Number(userStore.userId) || 1
    const res = await recommendApi.getExercises(userId, 10)
    console.log('[Exercises] 数据返回:', res)
    if (res.code === 200 && Array.isArray(res.data)) {
      for (const item of res.data) {
        exerciseList.push({
          id: item.id,
          title: item.title || '',
          type: item.type || '',
          difficulty: item.difficulty || 1,
          course: item.course || '',
          answer: item.answer || '',
          analysis: item.analysis || '',
          options: item.options || [],
          // 交互状态
          answered: false,
          isCorrect: null,
          userChoice: null,
          correctOption: null,
          userInput: '',
          userDisplay: '',
        })
      }
    } else {
      ElMessage.warning('加载习题返回: ' + (res.message || '未知错误'))
    }
  } catch (e) {
    console.error('[Exercises] 加载失败:', e)
    ElMessage.error('加载习题失败: ' + (e.message || '网络错误'))
  }
  loading.value = false
}

async function loadMastery() {
  try {
    const res = await recommendApi.getMastery(Number(userStore.userId) || 1)
    if (res.code === 200) masteryData.value = res.data
  } catch (e) {
    console.error('[Exercises] 加载掌握度失败:', e)
  }
}

async function markCorrect(exerciseId) {
  try {
    await recommendApi.submitAnswer({
      user_id: Number(userStore.userId) || 1,
      exercise_id: exerciseId,
      is_correct: true,
      time_spent: 0,
    })
    ElMessage.success('已记录！推荐将根据你的掌握情况动态调整')
    loadMastery()
  } catch (e) { ElMessage.error('提交失败') }
}

async function markWrong(exerciseId) {
  try {
    await recommendApi.submitAnswer({
      user_id: Number(userStore.userId) || 1,
      exercise_id: exerciseId,
      is_correct: false,
      time_spent: 0,
    })
    ElMessage.info('已记录，后续会推荐更多相关习题')
    loadMastery()
  } catch (e) { ElMessage.error('提交失败') }
}

onMounted(() => {
  loadExercises()
  loadMastery()
})
</script>

<style scoped>
.ex-title {
  font-size: 15px;
  line-height: 1.6;
  margin-bottom: 8px;
  font-weight: 500;
}

.ex-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 12px;
}

.ex-option {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 14px;
  line-height: 1.5;
}

.ex-option-default {
  background: #f5f7fa;
  border: 1px solid #ebeef5;
}
.ex-option-default:hover {
  background: #ecf5ff;
  border-color: #409eff;
}

.ex-option-selected {
  background: #ecf5ff;
  border: 2px solid #409eff;
  color: #409eff;
  font-weight: 500;
}

.ex-option-correct {
  background: #f0f9eb;
  border: 2px solid #67c23a;
  color: #67c23a;
  font-weight: 500;
}

.ex-option-wrong {
  background: #fef0f0;
  border: 2px solid #f56c6c;
  color: #f56c6c;
}

.opt-label {
  font-weight: 600;
  flex-shrink: 0;
  width: 20px;
}

.opt-text {
  flex: 1;
}

.ex-result {
  margin-top: 16px;
  padding: 16px;
  background: #fafbfc;
  border-radius: 8px;
  border: 1px solid #ebeef5;
}

.result-section {
  margin-bottom: 12px;
}

.result-section:last-child {
  margin-bottom: 0;
}

.result-label {
  font-size: 13px;
  font-weight: 600;
  color: #606266;
  margin-bottom: 4px;
}

.result-content {
  font-size: 14px;
  color: #303133;
  line-height: 1.6;
  white-space: pre-wrap;
}
</style>
