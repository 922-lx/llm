<template>
  <div>
    <div class="stat-cards" v-if="stats">
      <div class="stat-card clickable" @click="showNodesDialog">
        <div class="stat-value">{{ stats.node_count || 0 }}</div>
        <div class="stat-label">知识点节点</div>
        <div class="stat-hint">点击查看详情</div>
      </div>
      <div class="stat-card clickable" @click="showRelationsDialog">
        <div class="stat-value">{{ stats.relation_count || 0 }}</div>
        <div class="stat-label">关联关系</div>
        <div class="stat-hint">点击查看详情</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ Object.keys(stats.course_stats || {}).length }}</div>
        <div class="stat-label">课程覆盖</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">5</div>
        <div class="stat-label">关系类型</div>
      </div>
    </div>

    <div class="kg-container">
      <!-- 图谱画布 -->
      <div class="kg-canvas page-card" style="padding:0;">
        <div style="padding:16px 20px;display:flex;align-items:center;gap:12px;border-bottom:1px solid #ebeef5;">
          <el-input v-model="searchKey" placeholder="搜索知识点..." style="width:280px;"
            clearable @keyup.enter="handleSearch">
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="loadFullGraph">刷新图谱</el-button>
          <el-select v-model="selectedCourse" placeholder="课程筛选" style="width:140px;" clearable @change="loadFullGraph">
            <el-option label="数据结构" value="数据结构" />
            <el-option label="算法设计" value="算法设计" />
          </el-select>
        </div>
        <div id="kg-chart" ref="chartRef"></div>
      </div>

      <!-- 右侧详情面板 -->
      <div class="kg-sidebar-panel page-card" style="padding:20px;">
        <h3 style="margin-bottom:16px;">
          <el-icon><InfoFilled /></el-icon> 节点详情
        </h3>

        <div v-if="selectedNode" style="margin-bottom:20px;">
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="名称">{{ selectedNode.label }}</el-descriptions-item>
            <el-descriptions-item label="类别">
              <el-tag :type="categoryTagType(selectedNode.category)" size="small">
                {{ categoryLabel(selectedNode.category) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="难度">
              <el-rate v-model="selectedNode.difficulty" disabled />
            </el-descriptions-item>
            <el-descriptions-item label="描述" v-if="selectedNode.description">
              {{ selectedNode.description }}
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <el-empty v-else description="点击图谱节点查看详情" :image-size="60" />

        <el-divider />

        <h3 style="margin-bottom:12px;">
          <el-icon><Connection /></el-icon> 关联关系
        </h3>
        <div v-if="relatedLinks.length">
          <div v-for="(link, i) in relatedLinks" :key="i" style="margin-bottom:8px;padding:8px;background:#f5f7fa;border-radius:8px;font-size:13px;">
            <span>{{ link.source }}</span>
            <el-tag size="small" style="margin:0 6px;">{{ relLabel(link.relation) }}</el-tag>
            <span>{{ link.target }}</span>
          </div>
        </div>
        <el-empty v-else description="暂无关联关系" :image-size="40" />

        <el-divider />

        <!-- 关系类型图例 -->
        <h3 style="margin-bottom:12px;">
          <el-icon><Memo /></el-icon> 关系类型
        </h3>
        <div style="display:flex;flex-wrap:wrap;gap:6px;">
          <el-tag v-for="r in relationTypes" :key="r.value" :color="r.color" effect="dark" size="small" style="border:none;">
            {{ r.label }}
          </el-tag>
        </div>
      </div>
    </div>

    <!-- 知识点节点详情弹窗 -->
    <el-dialog v-model="nodesDialogVisible" title="知识点节点列表" width="720px" top="5vh">
      <div style="margin-bottom:12px;">
        <el-input v-model="nodeFilterKey" placeholder="输入关键词过滤..." clearable size="small" style="width:240px;" />
      </div>
      <el-table :data="filteredNodes" border stripe size="small" max-height="60vh"
        :default-sort="{ prop: 'category', order: 'ascending' }">
        <el-table-column type="index" label="#" width="50" />
        <el-table-column prop="label" label="知识点名称" min-width="140" sortable />
        <el-table-column prop="category" label="类别" width="100" sortable>
          <template #default="{ row }">
            <el-tag :type="categoryTagType(row.category)" size="small">
              {{ categoryLabel(row.category) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="difficulty" label="难度" width="120" sortable>
          <template #default="{ row }">
            {{ '★'.repeat(row.difficulty || 1) }}
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <span style="color:#909399;font-size:13px;">共 {{ filteredNodes.length }} 个知识点节点</span>
      </template>
    </el-dialog>

    <!-- 关联关系详情弹窗 -->
    <el-dialog v-model="relationsDialogVisible" title="关联关系列表" width="820px" top="5vh">
      <div style="margin-bottom:12px;display:flex;gap:10px;">
        <el-input v-model="relationFilterKey" placeholder="输入关键词过滤..." clearable size="small" style="width:240px;" />
        <el-select v-model="relationTypeFilter" placeholder="关系类型筛选" clearable size="small" style="width:140px;">
          <el-option v-for="r in relationTypes" :key="r.value" :label="r.label" :value="r.value" />
        </el-select>
      </div>
      <el-table :data="filteredRelations" border stripe size="small" max-height="60vh"
        :default-sort="{ prop: 'relation', order: 'ascending' }">
        <el-table-column type="index" label="#" width="50" />
        <el-table-column prop="source" label="起始节点" min-width="120" sortable />
        <el-table-column prop="relation" label="关系类型" width="100" sortable>
          <template #default="{ row }">
            <el-tag size="small" :color="relColor(row.relation)" effect="dark" style="border:none;">
              {{ relLabel(row.relation) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="target" label="目标节点" min-width="120" sortable />
      </el-table>
      <template #footer>
        <span style="color:#909399;font-size:13px;">共 {{ filteredRelations.length }} 条关联关系</span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { kgApi } from '../api'
import { Search, InfoFilled, Connection, Memo } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'

const chartRef = ref(null)
const searchKey = ref('')
const selectedCourse = ref('')
const selectedNode = ref(null)
const stats = ref(null)
const graphData = ref({ nodes: [], links: [] })
const relatedLinks = ref([])
const loading = ref(false)
let chart = null

// 弹窗状态
const nodesDialogVisible = ref(false)
const relationsDialogVisible = ref(false)
const nodeFilterKey = ref('')
const relationFilterKey = ref('')
const relationTypeFilter = ref('')

// 过滤后的节点和关系
const filteredNodes = computed(() => {
  const key = (nodeFilterKey.value || '').toLowerCase()
  const nodes = graphData.value.nodes || []
  if (!key) return nodes
  return nodes.filter(n =>
    (n.label || '').toLowerCase().includes(key) ||
    (n.category || '').toLowerCase().includes(key)
  )
})

const filteredRelations = computed(() => {
  const key = (relationFilterKey.value || '').toLowerCase()
  const type = relationTypeFilter.value
  const links = graphData.value.links || []
  return links.filter(l => {
    if (key && !(l.source || '').toLowerCase().includes(key) &&
        !(l.target || '').toLowerCase().includes(key) &&
        !(relLabel(l.relation) || '').toLowerCase().includes(key)) {
      return false
    }
    if (type && l.relation !== type) return false
    return true
  })
})

function showNodesDialog() {
  // 如果图谱数据还没加载，先加载
  if (!graphData.value.nodes.length) {
    loadFullGraph().then(() => { nodesDialogVisible.value = true })
  } else {
    nodesDialogVisible.value = true
  }
}

function showRelationsDialog() {
  if (!graphData.value.links.length) {
    loadFullGraph().then(() => { relationsDialogVisible.value = true })
  } else {
    relationsDialogVisible.value = true
  }
}

const relationTypes = [
  { value: 'CONTAINS', label: '包含', color: '#409eff' },
  { value: 'BELONGS_TO', label: '属于', color: '#67c23a' },
  { value: 'DERIVED_FROM', label: '派生', color: '#e6a23c' },
  { value: 'RELATED', label: '相关', color: '#909399' },
  { value: 'IMPLEMENTS', label: '实现', color: '#f56c6c' },
  { value: 'COMPARE', label: '对比', color: '#b37feb' },
  { value: 'PREREQUISITE', label: '前置', color: '#36cfc9' },
]

function relLabel(type) {
  const found = relationTypes.find(r => r.value === type)
  return found ? found.label : type
}

function relColor(type) {
  const found = relationTypes.find(r => r.value === type)
  return found ? found.color : '#909399'
}

function categoryLabel(cat) {
  const map = { DS: '数据结构', ALGO: '算法', CONCEPT: '概念', METHOD: '方法', PRINCIPLE: '原理' }
  return map[cat] || cat
}

function categoryTagType(cat) {
  const map = { DS: '', ALGO: 'success', CONCEPT: 'warning', METHOD: 'danger', PRINCIPLE: 'info' }
  return map[cat] || ''
}

function categoryColor(cat) {
  const map = { DS: '#409eff', ALGO: '#67c23a', CONCEPT: '#e6a23c', METHOD: '#f56c6c', PRINCIPLE: '#909399' }
  return map[cat] || '#409eff'
}

async function loadStats() {
  try {
    const res = await kgApi.getStats()
    if (res.code === 200) stats.value = res.data
  } catch (e) {
    console.error('加载统计失败:', e)
  }
}

async function loadFullGraph() {
  loading.value = true
  try {
    const res = await kgApi.getGraph(selectedCourse.value || undefined)
    console.log('[KG] 图谱数据返回:', res)
    if (res.code === 200) {
      graphData.value = res.data
      console.log('[KG] 节点数:', res.data.nodes?.length, '关系数:', res.data.links?.length)
      renderChart()
    } else {
      ElMessage.warning('加载图谱返回: ' + (res.message || '未知错误'))
    }
  } catch (e) {
    console.error('加载图谱失败:', e)
    ElMessage.error('加载图谱失败: ' + (e.message || '网络错误'))
  }
  loading.value = false
}

async function handleSearch() {
  if (!searchKey.value.trim()) {
    loadFullGraph()
    return
  }
  try {
    const res = await kgApi.search(searchKey.value)
    if (res.code === 200 && res.data.length > 0) {
      // 搜索第一个节点的子图
      const nodeRes = await kgApi.getNode(res.data[0].name, 2)
      if (nodeRes.code === 200) {
        graphData.value = nodeRes.data
        renderChart()
      }
    } else {
      graphData.value = { nodes: [], links: [] }
      renderChart()
    }
  } catch (e) {
    console.error('搜索失败:', e)
  }
}

function renderChart() {
  if (!chartRef.value) return
  if (!chart) {
    chart = echarts.init(chartRef.value)
    window.addEventListener('resize', () => chart?.resize())
  }

  const { nodes, links } = graphData.value
  const nodeMap = {}
  nodes.forEach(n => { nodeMap[n.id] = n })

  const catColors = {}
  const categories = [...new Set(nodes.map(n => n.category || '概念'))]
  const colorPalette = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399', '#b37feb', '#36cfc9']
  categories.forEach((c, i) => {
    catColors[c] = colorPalette[i % colorPalette.length]
  })

  const option = {
    tooltip: {
      trigger: 'item',
      formatter: (params) => {
        if (params.dataType === 'node') {
          const n = params.data
          return `<strong>${n.name}</strong><br/>类别：${categoryLabel(n.category)}<br/>难度：${'★'.repeat(n.difficulty || 1)}`
        }
        return `${params.data.source} → ${relLabel(params.data.relationType)} → ${params.data.target}`
      },
    },
    legend: {
      data: categories.map(c => categoryLabel(c)),
      bottom: 10,
      textStyle: { fontSize: 12 },
    },
    series: [{
      type: 'graph',
      layout: 'force',
      data: nodes.map(n => ({
        ...n,
        id: n.id,
        name: n.label,
        symbolSize: Math.max(30, 20 + (n.difficulty || 1) * 6),
        category: categories.indexOf(n.category || '概念'),
        itemStyle: { color: catColors[n.category || '概念'] || '#409eff' },
        label: {
          show: true,
          fontSize: 11,
          color: '#303133',
        },
        _rawCategory: n.category,
      })),
      links: links.map(l => ({
        source: l.source,
        target: l.target,
        lineStyle: {
          color: '#c0c4cc',
          width: 1.5,
          curveness: 0.1,
        },
        label: {
          show: false,
          formatter: relLabel(l.relation),
        },
        relationType: l.relation,
      })),
      categories: categories.map(c => ({
        name: categoryLabel(c),
        itemStyle: { color: catColors[c] },
      })),
      roam: true,
      draggable: true,
      force: {
        repulsion: 300,
        gravity: 0.1,
        edgeLength: [80, 200],
        layoutAnimation: true,
      },
      emphasis: {
        focus: 'adjacency',
        lineStyle: { width: 3 },
      },
      lineStyle: { opacity: 0.6 },
      animationDuration: 1500,
    }],
  }

  chart.setOption(option, true)

  // 点击节点事件
  chart.off('click')
  chart.on('click', (params) => {
    if (params.dataType === 'node') {
      const clickedNode = params.data
      // 还原 category 为原始字符串值用于显示
      selectedNode.value = {
        ...clickedNode,
        category: clickedNode._rawCategory || clickedNode.category,
      }
      const nodeName = clickedNode.id
      relatedLinks.value = links.filter(
        l => l.source === nodeName || l.target === nodeName
      )
    }
  })
}

onMounted(() => {
  loadStats()
  loadFullGraph()
})
</script>

<style scoped>
.stat-card.clickable {
  cursor: pointer;
  transition: all 0.25s;
}
.stat-card.clickable:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 16px rgba(0,0,0,0.12);
}
.stat-hint {
  font-size: 11px;
  color: #c0c4cc;
  margin-top: 2px;
}
</style>
