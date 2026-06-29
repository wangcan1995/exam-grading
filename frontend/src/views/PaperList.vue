<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { paperApi, statApi } from '../api'

const papers = ref([])
const dialogVisible = ref(false)
const form = ref({ name: '', subject: '', grade: '', description: '' })

// 响应式: 移动端切换为卡片列表
const isMobile = ref(false)
function checkMobile() {
  isMobile.value = window.innerWidth < 768
}

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
  load()
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
})

async function load() {
  const { data } = await paperApi.list()
  papers.value = data
}

async function handleCreate() {
  if (!form.value.name) {
    ElMessage.warning('请填写试卷名称')
    return
  }
  try {
    await paperApi.create({ ...form.value, template_json: [] })
    ElMessage.success('试卷已创建(需后续配置答题卡模板)')
    dialogVisible.value = false
    form.value = { name: '', subject: '', grade: '', description: '' }
    await load()
  } catch (e) {
    ElMessage.error('创建失败: ' + (e.response?.data?.detail || e.message))
  }
}

async function handleDelete(id) {
  await ElMessageBox.confirm('确定删除该试卷？关联的答题卡记录也会一并删除', '确认', {
    type: 'warning',
  })
  await paperApi.delete(id)
  ElMessage.success('已删除')
  await load()
}

async function viewStats(id) {
  try {
    const { data } = await statApi.paper(id)
    const msg = data.count === 0
      ? '该试卷暂无判分数据'
      : `人数: ${data.count} | 平均分: ${data.average} | 最高: ${data.max_score} | 最低: ${data.min_score} | 及格率: ${(data.pass_rate*100).toFixed(0)}%`
    ElMessageBox.alert(msg, `${data.paper_name} - 成绩统计`)
  } catch (e) {
    ElMessage.error('查询统计失败')
  }
}
</script>

<template>
  <el-card>
    <template #header>
      <div class="card-head">
        <strong>试卷管理</strong>
        <el-button type="primary" @click="dialogVisible = true" class="btn-create">+ 新建试卷</el-button>
      </div>
    </template>

    <!-- 桌面端: 表格 -->
    <el-table :data="papers" stripe v-show="!isMobile">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="name" label="试卷名称" />
      <el-table-column prop="subject" label="学科" width="100" />
      <el-table-column prop="grade" label="年级" width="100" />
      <el-table-column prop="question_count" label="题目数" width="90" />
      <el-table-column prop="total_score" label="满分" width="80" />
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button size="small" @click="viewStats(row.id)">统计</el-button>
          <el-button size="small" type="danger" @click="handleDelete(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 移动端: 卡片列表 -->
    <div v-show="isMobile" class="paper-cards">
      <div v-for="row in papers" :key="row.id" class="paper-card">
        <div class="paper-card-head">
          <span class="paper-name">{{ row.name }}</span>
          <span class="paper-score">满分 {{ row.total_score }}</span>
        </div>
        <div class="paper-card-meta">
          <span v-if="row.subject">学科: {{ row.subject }}</span>
          <span v-if="row.grade">年级: {{ row.grade }}</span>
          <span>题目数: {{ row.question_count || 0 }}</span>
        </div>
        <div class="paper-card-actions">
          <el-button size="small" @click="viewStats(row.id)">统计</el-button>
          <el-button size="small" type="danger" @click="handleDelete(row.id)">删除</el-button>
        </div>
      </div>
      <el-empty v-if="!papers.length" description="暂无试卷，点右上角创建" :image-size="80" />
    </div>

    <el-alert
      class="tip-alert"
      type="info" :closable="false"
      title="提示: 答题卡模板(选项坐标)目前通过脚本生成，可视化编辑器将在第 4 期实现。"
    />
  </el-card>

  <!-- 新建试卷对话框 -->
  <el-dialog v-model="dialogVisible" title="新建试卷" :width="isMobile ? '92%' : '480px'">
    <el-form :model="form" label-width="90px">
      <el-form-item label="试卷名称">
        <el-input v-model="form.name" placeholder="例: 2025期中数学" />
      </el-form-item>
      <el-form-item label="学科">
        <el-input v-model="form.subject" placeholder="选填" />
      </el-form-item>
      <el-form-item label="年级">
        <el-input v-model="form.grade" placeholder="选填" />
      </el-form-item>
      <el-form-item label="描述">
        <el-input v-model="form.description" type="textarea" :rows="2" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" @click="handleCreate">创建</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.card-head { display:flex; justify-content:space-between; align-items:center; }
.tip-alert { margin-top: 16px; }

@media (max-width: 768px) {
  .card-head strong { font-size: 15px; }
  .btn-create { padding: 8px 12px; }
  .tip-alert { margin-top: 12px; }

  .paper-cards { display: flex; flex-direction: column; gap: 10px; }
  .paper-card {
    background: #fff;
    border: 1px solid #ebeef5;
    border-radius: 8px;
    padding: 12px;
  }
  .paper-card-head {
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 8px;
  }
  .paper-name { font-size: 15px; font-weight: 600; color: #303133; }
  .paper-score { color: #409eff; font-weight: 600; }
  .paper-card-meta {
    display: flex; flex-wrap: wrap; gap: 12px;
    font-size: 13px; color: #606266; margin-bottom: 10px;
  }
  .paper-card-actions { display: flex; gap: 8px; }
}
</style>
