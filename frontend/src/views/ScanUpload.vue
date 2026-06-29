<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { paperApi, scanApi } from '../api'

const router = useRouter()

const papers = ref([])
const selectedPaper = ref(null)
const uploading = ref(false)
const fileList = ref([])
const studentId = ref('')
const studentName = ref('')

// 最近上传的答题卡列表
const sheets = ref([])

// 响应式: 移动端切换为卡片列表
const isMobile = ref(false)
function checkMobile() {
  isMobile.value = window.innerWidth < 768
}

onMounted(async () => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
  await loadPapers()
  await loadSheets()
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
})

async function loadPapers() {
  const { data } = await paperApi.list()
  papers.value = data
  if (data.length && !selectedPaper.value) {
    selectedPaper.value = data[0].id
  }
}

async function loadSheets() {
  const { data } = await scanApi.listSheets()
  sheets.value = data
}

async function handleUpload() {
  if (!selectedPaper.value) {
    ElMessage.warning('请先选择试卷')
    return
  }
  if (!fileList.value.length) {
    ElMessage.warning('请选择答题卡图片')
    return
  }

  uploading.value = true
  try {
    // MVP: 单文件上传(可扩展批量)
    const file = fileList.value[0].raw
    const { data } = await scanApi.upload(
      selectedPaper.value, file,
      studentId.value, studentName.value
    )
    ElMessage.success(`判分完成！得分 ${data.total_score}`)
    fileList.value = []
    studentId.value = ''
    studentName.value = ''
    await loadSheets()
    // 跳转到结果详情
    router.push(`/results/${data.id}`)
  } catch (e) {
    ElMessage.error('判分失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    uploading.value = false
  }
}

// 文件选择控制(不自动上传)
function handleChange(file, files) {
  fileList.value = files.slice(-1) // 只保留最后一个
}

function handleRemove() {
  fileList.value = []
}

function statusTag(status) {
  return { pending: 'info', grading: 'warning', graded: 'success',
           reviewed: 'success', error: 'danger' }[status] || 'info'
}
</script>

<template>
  <div>
    <el-card>
      <template #header>
        <strong>扫描上传 + 自动判分</strong>
      </template>

      <el-form label-width="100px" class="scan-form">
        <el-form-item label="选择试卷">
          <el-select v-model="selectedPaper" placeholder="请选择试卷" class="field-paper">
            <el-option
              v-for="p in papers"
              :key="p.id"
              :label="`${p.name} (满分${p.total_score})`"
              :value="p.id"
            />
          </el-select>
          <span v-if="!papers.length" class="no-paper-tip">
            暂无试卷，请先到「试卷管理」创建
          </span>
        </el-form-item>

        <el-form-item label="学生学号">
          <el-input v-model="studentId" placeholder="选填" class="field-short" />
        </el-form-item>
        <el-form-item label="学生姓名">
          <el-input v-model="studentName" placeholder="选填" class="field-short" />
        </el-form-item>

        <el-form-item label="答题卡图片">
          <el-upload
            drag
            :auto-upload="false"
            :on-change="handleChange"
            :on-remove="handleRemove"
            accept=".jpg,.jpeg,.png,.webp,.bmp"
            :limit="1"
          >
            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
            <div class="el-upload__text">拖拽图片到此处，或<em>点击选择</em></div>
            <template #tip>
              <div class="el-upload__tip">支持 jpg/png/webp，单张答题卡</div>
            </template>
          </el-upload>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="uploading" @click="handleUpload" class="btn-submit">
            上传并判分
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 最近判分列表 -->
    <el-card class="recent-card">
      <template #header>
        <strong>最近判分</strong>
      </template>
      <!-- 桌面端: 表格 -->
      <el-table :data="sheets" stripe v-show="!isMobile">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="student_name" label="学生" width="120">
          <template #default="{ row }">
            {{ row.student_name || row.student_id || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="total_score" label="得分" width="100" />
        <el-table-column label="需复核" width="90">
          <template #default="{ row }">
            <el-tag v-if="row.needs_review" type="warning" size="small">是</el-tag>
            <span v-else style="color:#67c23a;">否</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="时间" width="180">
          <template #default="{ row }">
            {{ new Date(row.created_at).toLocaleString('zh-CN') }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button size="small" @click="router.push(`/results/${row.id}`)">
              查看详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 移动端: 卡片列表 -->
      <div v-show="isMobile" class="sheet-cards">
        <div v-for="row in sheets" :key="row.id" class="sheet-card" @click="router.push(`/results/${row.id}`)">
          <div class="sheet-card-head">
            <span class="sheet-student">{{ row.student_name || row.student_id || '未署名' }}</span>
            <el-tag :type="statusTag(row.status)" size="small">{{ row.status }}</el-tag>
          </div>
          <div class="sheet-card-body">
            <span class="sheet-score">得分 <b>{{ row.total_score }}</b></span>
            <el-tag v-if="row.needs_review" type="warning" size="small">需复核</el-tag>
            <span v-else class="review-no">无需复核</span>
          </div>
          <div class="sheet-card-time">{{ new Date(row.created_at).toLocaleString('zh-CN') }}</div>
        </div>
        <el-empty v-if="!sheets.length" description="暂无判分记录" :image-size="80" />
      </div>
    </el-card>
  </div>
</template>

<style scoped>
/* 桌面端: 固定宽度 */
.field-paper { width: 320px; }
.field-short { width: 200px; }
.recent-card { margin-top: 20px; }
.no-paper-tip { color: #e6a23c; margin-left: 12px; }

/* 移动端: 全宽 + 卡片列表 */
@media (max-width: 768px) {
  .scan-form :deep(.el-form-item__label) { width: auto !important; padding-right: 8px; }
  .field-paper,
  .field-short { width: 100%; }
  .no-paper-tip { display: block; margin: 4px 0 0 0; }
  .recent-card { margin-top: 12px; }

  .sheet-cards { display: flex; flex-direction: column; gap: 10px; }
  .sheet-card {
    background: #fff;
    border: 1px solid #ebeef5;
    border-radius: 8px;
    padding: 12px;
    cursor: pointer;
    transition: box-shadow .2s;
  }
  .sheet-card:active { box-shadow: 0 0 0 2px #409eff33; }
  .sheet-card-head {
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 8px;
  }
  .sheet-student { font-size: 15px; font-weight: 600; color: #303133; }
  .sheet-card-body {
    display: flex; align-items: center; gap: 10px; margin-bottom: 6px;
  }
  .sheet-score { font-size: 14px; color: #606266; }
  .sheet-score b { color: #409eff; font-size: 18px; }
  .review-no { color: #67c23a; font-size: 13px; }
  .sheet-card-time { font-size: 12px; color: #909399; }
}
</style>
