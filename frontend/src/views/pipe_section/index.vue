<template>
  <section class="page" data-module="pipe_section">
    <header class="page-head">
      <div>
        <h2>管段档案管理</h2>
        <p class="page-desc">维护管段，围绕管段编号、管线类型、材质规格、埋设深度做登记、筛选与状态流转；待补项与总览工作台、详情实时同步。</p>
      </div>
      <div class="page-actions">
        <RouterLink class="btn" to="/pipe_section/workbench">打开总览工作台</RouterLink>
        <button class="btn primary" type="button" @click="showCreate = true">登记管段</button>
        <button class="btn" type="button" @click="exportRows">导出管段档案清单</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in statCards" :key="item.label" class="stat-card" :class="item.cls">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <form class="filter-bar" @submit.prevent="applyFilters">
      <label class="filter-item">
        <span>管段编号</span>
        <input v-model="filterForm.keyword" placeholder="按管段编号检索" />
      </label>
      <label class="filter-item">
        <span>管段状态</span>
        <select v-model="filterForm.status">
          <option value="">全部状态</option>
          <option v-for="status in statuses" :key="status" :value="status">{{ status }}</option>
        </select>
      </label>
      <label class="filter-item">
        <span>待补项</span>
        <select v-model="filterForm.issue">
          <option value="">不限待补项</option>
          <option v-for="issue in issueLabels" :key="issue" :value="issue">{{ issue }}</option>
        </select>
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column">{{ column }}</th>
          <th>待补项</th>
          <th>可执行动作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in store.entries" :key="String(row.id)">
          <td>
            <RouterLink class="link" :to="`/pipe_section/detail/${row.id}`">{{ row.管段编号 }}</RouterLink>
          </td>
          <td>{{ row.管线类型 || '—' }}</td>
          <td>{{ row.材质规格 || '—' }}</td>
          <td>{{ row.埋设深度 || '—' }}</td>
          <td>{{ row.空间位置 || '—' }}</td>
          <td>{{ row.坐标 || '—' }}</td>
          <td><span class="status-tag" :class="`tag-${statusKey(row.status)}`">{{ row.管段状态 ?? row.status }}</span></td>
          <td>
            <span v-if="row.issues.length">
              <span v-for="issue in row.issues" :key="issue" class="issue-tag">{{ issue }}</span>
            </span>
            <span v-else class="ok-text">完整</span>
          </td>
          <td class="row-actions">
            <button class="link" type="button" @click="openFix(row)">修正</button>
            <button
              v-for="action in availableActions(row.status)"
              :key="action"
              class="link"
              type="button"
              @click="runAction(action, row)"
            >
              {{ action }}
            </button>
          </td>
        </tr>
        <tr v-if="!store.entries.length">
          <td :colspan="columns.length + 2" class="empty-state">暂无符合条件的管段档案数据</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ store.total }} 条管段档案记录（与总览工作台、详情同源同步）</span>
      <span v-if="store.error" class="error-text">{{ store.error }}</span>
      <span v-else-if="store.lastMessage" class="ok-text">{{ store.lastMessage }}</span>
    </footer>

    <PipeFixDialog :entry="fixEntry" @close="fixEntry = null" @saved="onSaved" />
    <PipeCreateDialog v-if="showCreate" @close="showCreate = false" @saved="onSaved" />
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'

import PipeCreateDialog from './PipeCreateDialog.vue'
import PipeFixDialog from './PipeFixDialog.vue'
import {
  PIPE_ISSUE_LABELS,
  PIPE_STATUSES,
  usePipeSectionStore,
  type PipeEntry,
} from '@/stores/pipeSection'

const ENDPOINT = '/api/pipe_section'
const columns = ['管段编号', '管线类型', '材质规格', '埋设深度', '空间位置', '坐标', '管段状态']
const statuses = PIPE_STATUSES
const issueLabels = PIPE_ISSUE_LABELS

const store = usePipeSectionStore()
const route = useRoute()

const filterForm = reactive({
  keyword: '',
  status: typeof route.query.status === 'string' ? route.query.status : '',
  issue: '',
})

const statCards = computed(() => {
  const counts = store.workbench?.counts ?? {}
  return [
    { label: '在役管段', value: counts['在役'] ?? 0, cls: '' },
    { label: '废弃管段', value: counts['废弃'] ?? 0, cls: 'card-danger' },
    { label: '封存/迁改中', value: (counts['封存'] ?? 0) + (counts['迁改中'] ?? 0), cls: '' },
    { label: '待补项', value: store.workbench?.issue_count ?? 0, cls: 'card-warn' },
  ]
})

const fixEntry = ref<PipeEntry | null>(null)
const showCreate = ref(false)

function availableActions(status: string) {
  // 当前是什么状态，就把它切换到另外几个状态的动作给出；自身状态对应的动作不再重复列出
  return ['恢复在役', '标记废弃', '封存管段', '登记迁改'].filter((action) => {
    const target = { 恢复在役: '在役', 标记废弃: '废弃', 封存管段: '封存', 登记迁改: '迁改中' }
    return target[action as keyof typeof target] !== status
  })
}

function statusKey(status: string) {
  if (status === '废弃') return 'danger'
  if (status === '封存' || status === '迁改中') return 'muted'
  return 'ok'
}

function openFix(row: PipeEntry) {
  fixEntry.value = row
}

function onSaved() {
  fixEntry.value = null
  showCreate.value = false
}

function applyFilters() {
  void store.fetchList({
    keyword: filterForm.keyword || undefined,
    status: filterForm.status || undefined,
    issue: filterForm.issue || undefined,
    page: 1,
  })
}

function resetFilters() {
  filterForm.keyword = ''
  filterForm.status = ''
  filterForm.issue = ''
  void store.fetchList({ keyword: undefined, status: undefined, issue: undefined, page: 1 })
}

function exportRows() {
  window.open(`${ENDPOINT}/export`, '_blank')
}

async function runAction(action: string, row: PipeEntry) {
  try {
    await store.runAction(row, action)
  } catch (error) {
    store.error = error instanceof Error ? error.message : '管段档案操作失败'
  }
}

onMounted(async () => {
  await Promise.all([
    store.fetchWorkbench(),
    store.fetchList({
      keyword: undefined,
      status: filterForm.status || undefined,
      issue: undefined,
      page: 1,
      size: 200,
    }),
  ])
})
</script>
