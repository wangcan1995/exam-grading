<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { scanApi } from '../api'

const route = useRoute()
const sheetId = Number(route.params.id)

const sheet = ref(null)
const results = ref([])
const loading = ref(true)
const imageTab = ref('original')

// 响应式: 移动端左右分栏改为上下堆叠、逐题表格改为卡片
const isMobile = ref(false)
function checkMobile() {
  isMobile.value = window.innerWidth < 768
}

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
  loadData()
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
})

async function loadData() {
  loading.value = true
  try {
    const [s, r] = await Promise.all([
      scanApi.getSheet(sheetId),
      scanApi.getResults(sheetId),
    ])
    sheet.value = s.data
    results.value = r.data
  } catch (e) {
    ElMessage.error('加载失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

// fill_ratio → 进度条百分比
function fillPercent(detail, option) {
  const o = detail?.options?.find((x) => x.option === option)
  return o ? Math.round(o.fill_ratio * 100) : 0
}
</script>

<template>
  <div v-loading="loading">
    <el-page-header @back="$router.push('/scan')" content="判分结果详情" class="page-header" />

    <!-- 移动端: 总分置顶醒目展示 -->
    <el-card v-if="isMobile && sheet" class="mobile-score-card">
      <div class="mobile-score-num">{{ sheet.total_score }}</div>
      <div class="mobile-score-label">总分 · {{ sheet.status }}</div>
    </el-card>

    <el-row :gutter="isMobile ? 0 : 20" v-if="sheet">
      <!-- 左侧: 图片对比 -->
      <el-col :xs="24" :sm="14">
        <el-card :class="{ 'result-card': true, 'mt-mobile': isMobile }">
          <template #header>
            <strong>答题卡图像</strong>
          </template>
          <el-tabs v-model="imageTab">
            <el-tab-pane label="原始图" name="original">
              <img
                v-if="sheet.original_path"
                :src="scanApi.imageUrl(sheet.id, 'original')"
                class="sheet-img"
              />
            </el-tab-pane>
            <el-tab-pane label="矫正后" name="processed">
              <img
                v-if="sheet.processed_path"
                :src="scanApi.imageUrl(sheet.id, 'processed')"
                class="sheet-img"
              />
              <el-alert
                v-else type="info" :closable="false"
                title="尚未生成矫正图"
              />
            </el-tab-pane>
          </el-tabs>
        </el-card>
      </el-col>

      <!-- 右侧: 判分汇总 -->
      <el-col :xs="24" :sm="10">
        <el-card :class="{ 'result-card': true, 'mt-mobile': isMobile, 'summary-card-desktop': !isMobile }">
          <template #header><strong>判分汇总</strong></template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="学生">
              {{ sheet.student_name || sheet.student_id || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="sheet.status === 'graded' ? 'success' : 'warning'" size="small">
                {{ sheet.status }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="总分" v-if="!isMobile">
              <span class="total-score">
                {{ sheet.total_score }}
              </span>
            </el-descriptions-item>
            <el-descriptions-item label="是否需复核">
              <el-tag :type="sheet.needs_review ? 'warning' : 'success'" size="small">
                {{ sheet.needs_review ? '有题需复核' : '全部自动判分' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="判分时间">
              {{ sheet.graded_at ? new Date(sheet.graded_at).toLocaleString('zh-CN') : '-' }}
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>

    <!-- 逐题判分明细 -->
    <el-card class="detail-card">
      <template #header><strong>逐题判分明细</strong></template>
      <!-- 桌面端: 表格 -->
      <el-table :data="results" stripe v-show="!isMobile">
        <el-table-column prop="question_no" label="题号" width="70" />
        <el-table-column label="学生答案" width="110">
          <template #default="{ row }">
            <strong>{{ row.detected_answer || '∅(未涂)' }}</strong>
          </template>
        </el-table-column>
        <el-table-column prop="correct_answer" label="标准答案" width="100" />
        <el-table-column label="结果" width="80">
          <template #default="{ row }">
            <el-tag :type="row.final_score >= row.max_score ? 'success' : 'danger'" size="small">
              {{ row.final_score >= row.max_score ? '✓ 对' : '✗ 错' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="得分" width="100">
          <template #default="{ row }">
            {{ row.final_score }} / {{ row.max_score }}
          </template>
        </el-table-column>
        <el-table-column label="置信度" width="160">
          <template #default="{ row }">
            <el-progress
              :percentage="Math.round(row.confidence * 100)"
              :status="row.confidence > 0.8 ? 'success' : 'warning'"
            />
          </template>
        </el-table-column>
        <el-table-column label="各选项涂卡比例" min-width="280">
          <template #default="{ row }">
            <div v-for="opt in row.detail?.options || []" :key="opt.option" class="opt-row">
              <span class="opt-letter">{{ opt.option }}</span>
              <el-progress
                :percentage="Math.round(opt.fill_ratio * 100)"
                :stroke-width="10"
                class="opt-bar"
                :show-text="false"
                :color="opt.marked ? '#67c23a' : '#dcdfe6'"
              />
              <span class="opt-pct">
                {{ Math.round(opt.fill_ratio * 100) }}%
              </span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="复核" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.needs_review" type="warning" size="small">待复核</el-tag>
            <span v-else style="color:#67c23a;">自动通过</span>
          </template>
        </el-table-column>
      </el-table>

      <!-- 移动端: 卡片列表 -->
      <div v-show="isMobile" class="result-cards">
        <div v-for="row in results" :key="row.question_no" class="result-card-item">
          <div class="rc-head">
            <span class="rc-q">第{{ row.question_no }}题</span>
            <el-tag :type="row.final_score >= row.max_score ? 'success' : 'danger'" size="small">
              {{ row.final_score >= row.max_score ? '✓ 对' : '✗ 错' }}
            </el-tag>
            <span class="rc-score">{{ row.final_score }}/{{ row.max_score }}</span>
          </div>
          <div class="rc-answers">
            <span>作答 <b>{{ row.detected_answer || '∅' }}</b></span>
            <span>答案 <b>{{ row.correct_answer }}</b></span>
          </div>
          <div class="rc-conf">
            <span class="rc-conf-label">置信度 {{ Math.round(row.confidence * 100) }}%</span>
            <el-progress
              :percentage="Math.round(row.confidence * 100)"
              :show-text="false"
              :stroke-width="8"
              :status="row.confidence > 0.8 ? 'success' : 'warning'"
              class="rc-conf-bar"
            />
          </div>
          <div v-if="row.detail?.options?.length" class="rc-opts">
            <div v-for="opt in row.detail.options" :key="opt.option" class="opt-row">
              <span class="opt-letter">{{ opt.option }}</span>
              <el-progress
                :percentage="Math.round(opt.fill_ratio * 100)"
                :stroke-width="8"
                class="opt-bar"
                :show-text="false"
                :color="opt.marked ? '#67c23a' : '#dcdfe6'"
              />
              <span class="opt-pct">{{ Math.round(opt.fill_ratio * 100) }}%</span>
            </div>
          </div>
          <div v-if="row.needs_review" class="rc-review">
            <el-tag type="warning" size="small">待复核</el-tag>
          </div>
        </div>
        <el-empty v-if="!results.length" description="暂无判分明细" :image-size="80" />
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.page-header { margin-bottom: 20px; }
.result-card { margin-bottom: 0; }
.summary-card-desktop { margin-bottom: 0; }
.detail-card { margin-top: 20px; }
.sheet-img { width: 100%; border: 1px solid #eee; }
.total-score { font-size: 24px; color: #409eff; font-weight: bold; }
.opt-row { display:flex; align-items:center; gap:8px; margin-bottom:2px; }
.opt-letter { width:16px; font-weight:bold; color:#606266; }
.opt-bar { flex: 1; }
.opt-pct { width:36px; font-size:12px; color:#909399; }

/* 移动端 */
@media (max-width: 768px) {
  .page-header { margin-bottom: 12px; }
  .mobile-score-card { margin-bottom: 12px; text-align: center; }
  .mobile-score-num { font-size: 40px; color: #409eff; font-weight: bold; line-height: 1.1; }
  .mobile-score-label { font-size: 13px; color: #909399; margin-top: 4px; }
  .mt-mobile { margin-top: 12px; }
  .detail-card { margin-top: 12px; }

  .result-cards { display: flex; flex-direction: column; gap: 10px; }
  .result-card-item {
    background: #fff;
    border: 1px solid #ebeef5;
    border-radius: 8px;
    padding: 12px;
  }
  .rc-head {
    display: flex; align-items: center; gap: 10px; margin-bottom: 8px;
  }
  .rc-q { font-size: 15px; font-weight: 600; color: #303133; flex: 1; }
  .rc-score { color: #409eff; font-weight: 600; font-size: 14px; }
  .rc-answers {
    display: flex; gap: 16px; font-size: 13px; color: #606266; margin-bottom: 8px;
  }
  .rc-answers b { color: #303133; }
  .rc-conf { margin-bottom: 8px; }
  .rc-conf-label { font-size: 12px; color: #909399; display: block; margin-bottom: 4px; }
  .rc-conf-bar { width: 100%; }
  .rc-opts { padding-top: 8px; border-top: 1px dashed #ebeef5; }
  .rc-review { margin-top: 8px; }
}
</style>
