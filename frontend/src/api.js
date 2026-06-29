import axios from 'axios'

// 后端 API 客户端 (开发环境经 vite proxy 转发到 8000)
const api = axios.create({
  baseURL: '/api',
  timeout: 60000, // 判分可能耗时，给足超时
})

// ===== 试卷 =====
export const paperApi = {
  list: () => api.get('/papers'),
  get: (id) => api.get(`/papers/${id}`),
  create: (data) => api.post('/papers', data),
  delete: (id) => api.delete(`/papers/${id}`),
}

// ===== 扫描判分 =====
export const scanApi = {
  // 上传答题卡并判分
  upload: (paperId, file, studentId = '', studentName = '') => {
    const form = new FormData()
    form.append('paper_id', paperId)
    form.append('file', file)
    if (studentId) form.append('student_id', studentId)
    if (studentName) form.append('student_name', studentName)
    return api.post('/scan/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  listSheets: (paperId) =>
    api.get('/sheets', { params: paperId ? { paper_id: paperId } : {} }),
  getSheet: (id) => api.get(`/sheets/${id}`),
  getResults: (id) => api.get(`/sheets/${id}/results`),
  // 图片 URL (直接用 <img :src="...">)
  imageUrl: (sheetId, kind) => `/api/images/${sheetId}/${kind}`,
}

// ===== 复核 =====
export const reviewApi = {
  pending: () => api.get('/review/pending'),
  update: (resultId, data) => api.put(`/review/${resultId}`, data),
}

// ===== 统计 =====
export const statApi = {
  paper: (paperId) => api.get(`/stats/papers/${paperId}`),
}

export default api
