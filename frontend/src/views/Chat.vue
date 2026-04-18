<template>
  <div class="chat-container">
    <div class="chat-messages" ref="messagesRef">
      <!-- 欢迎消息 -->
      <div class="chat-msg assistant" v-if="messages.length === 0">
        <div class="chat-avatar">🤖</div>
        <div class="chat-bubble">
          你好！我是数据结构课程智能助教，基于知识图谱与大语言模型为你提供精准答疑。
          <br /><br />
          你可以问我：
          <br />• 什么是二叉搜索树？
          <br />• 快速排序和归并排序有什么区别？
          <br />• 图的广度优先搜索是如何实现的？
          <br />• 什么是动态规划？
        </div>
      </div>

      <div v-for="(msg, idx) in messages" :key="idx" :class="['chat-msg', msg.role]">
        <div class="chat-avatar">{{ msg.role === 'user' ? '👤' : '🤖' }}</div>
        <div class="chat-bubble">
          <div v-html="formatMsg(msg.content)"></div>
          <!-- 检索到的知识点 -->
          <div v-if="msg.role === 'assistant' && msg.nodes && msg.nodes.length" style="margin-top:8px;">
            <el-tag v-for="n in msg.nodes" :key="n" size="small" type="info" style="margin:2px 4px 2px 0;"
              @click="$router.push('/knowledge')" class="clickable-tag">
              📌 {{ n }}
            </el-tag>
          </div>
        </div>
      </div>

      <!-- 加载中 -->
      <div class="chat-msg assistant" v-if="loading">
        <div class="chat-avatar">🤖</div>
        <div class="chat-bubble">
          <span class="typing-dots">正在思考中</span>
        </div>
      </div>
    </div>

    <div class="chat-input-area">
      <div style="display:flex;gap:8px;">
        <el-input
          v-model="inputText"
          type="textarea"
          :rows="2"
          placeholder="输入你的数据结构问题..."
          @keydown.enter.exact.prevent="sendMessage"
          :disabled="loading"
          resize="none"
        />
        <el-button type="primary" :loading="loading" @click="sendMessage" style="height:auto;"
          :icon="Promotion">
          发送
        </el-button>
      </div>
      <div style="display:flex;justify-content:space-between;margin-top:8px;">
        <div style="display:flex;gap:8px;">
          <el-tag v-for="q in quickQuestions" :key="q" class="clickable-tag" @click="quickAsk(q)" size="small">
            {{ q }}
          </el-tag>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { useUserStore } from '../stores/user'
import { qaApi } from '../api'
import { ElMessage } from 'element-plus'
import { Promotion } from '@element-plus/icons-vue'

const userStore = useUserStore()
const messages = ref([])
const inputText = ref('')
const loading = ref(false)
const messagesRef = ref(null)

const quickQuestions = [
  '什么是二叉搜索树？',
  '快速排序的原理？',
  '栈和队列的区别？',
  '动态规划入门',
]

function scrollToBottom() {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}

function formatMsg(text) {
  if (!text) return ''
  return text
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre style="background:#f5f5f5;padding:12px;border-radius:8px;overflow-x:auto;margin:8px 0;"><code>$2</code></pre>')
    .replace(/`([^`]+)`/g, '<code style="background:#f0f0f0;padding:2px 6px;border-radius:4px;">$1</code>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br/>')
}

function quickAsk(q) {
  inputText.value = q
  sendMessage()
}

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || loading.value) return

  messages.value.push({ role: 'user', content: text })
  inputText.value = ''
  loading.value = true
  scrollToBottom()

  try {
    const res = await qaApi.ask(text, Number(userStore.userId) || 1)
    if (res.code === 200) {
      messages.value.push({
        role: 'assistant',
        content: res.data.answer,
        nodes: res.data.retrieved_nodes || [],
      })
    } else {
      messages.value.push({
        role: 'assistant',
        content: '抱歉，服务暂时不可用，请稍后重试。',
      })
    }
  } catch (e) {
    messages.value.push({
      role: 'assistant',
      content: '网络连接失败，请确保后端服务已启动（端口5000）。',
    })
  }

  loading.value = false
  scrollToBottom()
}
</script>

<style scoped>
.clickable-tag {
  cursor: pointer;
  transition: all 0.2s;
}
.clickable-tag:hover {
  opacity: 0.8;
  transform: scale(1.02);
}
.typing-dots::after {
  content: '...';
  animation: dots 1.5s infinite;
}
@keyframes dots {
  0%, 20% { content: '.'; }
  40% { content: '..'; }
  60%, 100% { content: '...'; }
}
</style>
