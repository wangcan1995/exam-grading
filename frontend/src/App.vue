<script setup>
import { ref, onMounted, onUnmounted } from "vue";
import { RouterLink, RouterView } from "vue-router";

const isMobile = ref(false);
const drawerVisible = ref(false);

function checkMobile() {
  isMobile.value = window.innerWidth < 768;
}

onMounted(() => {
  checkMobile();
  window.addEventListener("resize", checkMobile);
});

onUnmounted(() => {
  window.removeEventListener("resize", checkMobile);
});

function goRoute(path) {
  drawerVisible.value = false;
  // vue-router handles navigation via <router-link>, but for drawer items we use programmatic navigation
  window.history.pushState({}, "", path);
  window.dispatchEvent(new PopStateEvent("popstate"));
}
</script>

<template>
  <el-container style="min-height: 100vh">
    <!-- 桌面端头部 -->
    <el-header v-if="!isMobile" class="app-header">
      <h2 class="app-title">📝 试卷阅卷打分系统</h2>
      <el-menu
        :default-active="$route.path"
        mode="horizontal"
        background-color="#409eff"
        text-color="#fff"
        active-text-color="#fff"
        router
        style="margin-left: 40px; border: none; flex: 1"
      >
        <el-menu-item index="/scan">扫描判分</el-menu-item>
        <el-menu-item index="/papers">试卷管理</el-menu-item>
      </el-menu>
      <el-tag type="warning" size="small" effect="dark">第1期 MVP</el-tag>
    </el-header>

    <!-- 移动端头部 -->
    <el-header v-else class="app-header app-header-mobile">
      <h2 class="app-title app-title-mobile">📝 阅卷系统</h2>
      <div style="flex: 1"></div>
      <el-button
        text
        @click="drawerVisible = true"
        style="color: #fff; font-size: 22px; padding: 4px 8px"
      >
        ☰
      </el-button>
    </el-header>

    <!-- 移动端导航抽屉 -->
    <el-drawer
      v-model="drawerVisible"
      title="导航菜单"
      direction="ltr"
      size="260px"
      :show-close="false"
    >
      <el-menu
        :default-active="$route.path"
        router
        @select="drawerVisible = false"
      >
        <el-menu-item index="/scan">
          <span>📤 扫描判分</span>
        </el-menu-item>
        <el-menu-item index="/papers">
          <span>📋 试卷管理</span>
        </el-menu-item>
      </el-menu>
      <el-tag type="warning" size="small" effect="dark" style="margin-top: 20px"
        >第1期 MVP</el-tag
      >
    </el-drawer>

    <el-main :class="{ 'app-main-mobile': isMobile }">
      <RouterView />
    </el-main>
  </el-container>
</template>

<style>
body {
  margin: 0;
  font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
  background: #f5f7fa;
}

.app-header {
  background: #409eff;
  color: #fff;
  display: flex;
  align-items: center;
}

.app-header-mobile {
  padding: 0 12px;
  height: 50px !important;
}

.app-title {
  margin: 0;
  font-size: 18px;
  white-space: nowrap;
}

.app-title-mobile {
  font-size: 16px;
}

.app-main-mobile {
  padding: 12px;
}

/* ===== 全局移动端适配 ===== */
@media (max-width: 768px) {
  /* 表格在小屏幕上横向滚动 */
  .el-table {
    overflow-x: auto;
  }

  /* 对话框全屏 */
  .el-dialog {
    width: 95% !important;
    margin-top: 5vh !important;
  }

  /* 卡片间距缩小 */
  .el-card {
    margin-bottom: 12px;
  }

  /* 表单全宽 */
  .el-form-item .el-select,
  .el-form-item .el-input {
    width: 100% !important;
  }

  .el-form-item {
    flex-direction: column;
    align-items: stretch;
  }

  .el-form-item__label {
    text-align: left;
    margin-bottom: 4px;
  }

  /* 上传区域自适应 */
  .el-upload-dragger {
    padding: 20px 12px;
    width: 100%;
  }

  /* 描述列表字体缩小 */
  .el-descriptions__label,
  .el-descriptions__content {
    font-size: 13px;
    padding: 8px 10px;
  }
}
</style>
