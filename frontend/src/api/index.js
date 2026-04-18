import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// 请求拦截
api.interceptors.request.use(config => {
  const token = localStorage.getItem('user_id')
  if (token) {
    config.headers['X-User-Id'] = token
  }
  return config
})

// 响应拦截
api.interceptors.response.use(
  res => res.data,
  err => {
    console.error('API Error:', err)
    return Promise.reject(err)
  }
)

// ──────── 用户 ────────
export const userApi = {
  login: (data) => api.post('/user/login', data),
  register: (data) => api.post('/user/register', data),
  getProfile: (userId) => api.get(`/user/profile/${userId}`),
}

// ──────── 问答 ────────
export const qaApi = {
  ask: (question, userId) => api.post('/qa/ask', { question, user_id: userId }),
  getHistory: (userId, page = 1, size = 20) =>
    api.get('/qa/history', { params: { user_id: userId, page, size } }),
  rate: (id, rating) => api.post('/qa/rate', { id, rating }),
}

// ──────── 知识图谱 ────────
export const kgApi = {
  getStats: () => api.get('/kg/stats'),
  getGraph: (course) => api.get('/kg/graph', { params: { course } }),
  getNode: (name, depth = 2) => api.get(`/kg/node/${encodeURIComponent(name)}`, { params: { depth } }),
  search: (q, limit = 20) => api.get('/kg/search', { params: { q, limit } }),
  createNode: (data) => api.post('/kg/node', data),
  createRelation: (data) => api.post('/kg/relation', data),
}

// ──────── 推荐 ────────
export const recommendApi = {
  getExercises: (userId, limit = 10) =>
    api.get('/recommend/exercises', { params: { user_id: userId, limit } }),
  getLearningPath: (userId, target) =>
    api.get('/recommend/learning-path', { params: { user_id: userId, target } }),
  submitAnswer: (data) => api.post('/recommend/submit-answer', data),
  getMastery: (userId) => api.get('/recommend/mastery', { params: { user_id: userId } }),
}

export default api
