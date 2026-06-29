import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/scan' },
  {
    path: '/scan',
    name: 'scan',
    component: () => import('../views/ScanUpload.vue'),
    meta: { title: '扫描判分' },
  },
  {
    path: '/results/:id',
    name: 'results',
    component: () => import('../views/SheetResults.vue'),
    meta: { title: '判分结果' },
  },
  {
    path: '/papers',
    name: 'papers',
    component: () => import('../views/PaperList.vue'),
    meta: { title: '试卷管理' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
