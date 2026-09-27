<template>
  <section class="page" data-module="pipe_section_workbench">
    <header class="page-head">
      <div>
        <h2>管段总览工作台</h2>
        <p class="page-desc">在「按管线」与「按空间位置」之间自由切换；组内在役、废弃、封存、迁改中分别计数，坐标缺失、编号重复等待补项单独标明并可就地修正。</p>
      </div>
      <div class="page-actions">
        <RouterLink class="btn" to="/pipe_section">查看档案列表</RouterLink>
        <button class="btn primary" type="button" @click="showCreate = true">登记管段</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in statCards" :key="item.label" class="stat-card" :class="item.cls">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <div class="switch-bar">
      <div class="segmented" role="tablist">
        <button
          v-for="option in viewOptions"
          :key="option.value"
          type="button"
          role="tab"
          :class="{ active: view === option.value }"
          @click="switchView(option.value)"
        >
          {{ option.label }}
        </button>
      </div>
      <span v-if="store.error" class="error-text">{{ store.error }}</span>
      <span v-else-if="store.lastMessage" class="ok-text">{{ store.lastMessage }}</span>
      <button class="btn ghost" type="button" @click="store.fetchWorkbench()">刷新</button>
    </div>

    <div v-if="store.loading && !workbench" class="panel-empty">工作台加载中…</div>

    <template v-else-if="workbench">
      <div class="group-grid">
        <article v-for="group in workbench.groups" :key="group.key" class="group-card" :class="{ warning: group.missing_location }">
          <header class="group-head">
            <h3>{{ group.label }}</h3>
            <span class="group-total">共 {{ group.counts.total }} 段</span>
          </header>
          <div class="bucket-row">
            <button
              v-for="status in statuses"
              :key="status"
              type="button"
              class="bucket"
              :class="bucketClass(status)"
              @click="filterByStatus(status)"
              :title="`在列表中只看「${group.label}」${status}管段`"
            >
              <span>{{ status }}</span>
              <strong>{{ group.counts[status] ?? 0 }}</strong>
            </button>
          </div>
          <p v-if="group.counts.pending" class="group-pending">含 {{ group.counts.pending }} 段待补</p>

          <div class="member-list">
            <div
              v-for="entry in membersOf(group)"
              :key="String(entry.id)"
              class="member-row"
              :class="{ 'is-abandoned': entry.status === '废弃' }"
            >
              <div class="member-main">
                <RouterLink class="member-code" :to="`/pipe_section/detail/${entry.id}`">{{ entry.管段编号 }}</RouterLink>
                <span class="member-spec">{{ entry.材质规格 }} · 埋深 {{ entry.埋设深度 }}</span>
              </div>
              <div class="member-meta">
                <span class="status-tag" :class="`tag-${statusKey(entry.status)}`">{{ entry.status }}</span>
                <span v-for="issue in entry.issues" :key="issue" class="issue-tag">{{ issue }}</span>
                <button class="link" type="button" @click="openFix(entry)">修正</button>
                <button class="link" type="button" @click="toggleStatus(entry)">
                  {{ entry.status === '废弃' ? '恢复在役' : '标记废弃' }}
                </button>
              </div>
            </div>
          </div>
        </article>
      </div>

      <section class="issue-panel">
        <header class="issue-panel-head">
          <h3>待补项（{{ workbench.issue_count }}）</h3>
          <p>坐标缺失、坐标格式有误、空间位置缺失与重复编号都在此标明，不会静默丢弃；修正后自动从清单移除。</p>
        </header>
        <table v-if="workbench.issues.length" class="data-table">
          <thead>
            <tr>
              <th>管段编号</th>
              <th>管线类型</th>
              <th>材质规格</th>
              <th>埋设深度</th>
              <th>当前状态</th>
              <th>待补项</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="entry in workbench.issues" :key="String(entry.id)">
              <td><RouterLink class="link" :to="`/pipe_section/detail/${entry.id}`">{{ entry.管段编号 }}</RouterLink></td>
              <td>{{ entry.管线类型 || '—' }}</td>
              <td>{{ entry.材质规格 }}</td>
              <td>{{ entry.埋设深度 }}</td>
              <td><span class="status-tag" :class="`tag-${statusKey(entry.status)}`">{{ entry.status }}</span></td>
              <td>
                <span v-for="issue in entry.issues" :key="issue" class="issue-tag">{{ issue }}</span>
              </td>
              <td class="row-actions">
                <button class="link" type="button" @click="openFix(entry)">修正</button>
                <button class="link" type="button" @click="toggleStatus(entry)">
                  {{ entry.status === '废弃' ? '恢复在役' : '标记废弃' }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
        <p v-else class="panel-empty ok-text">所有管段坐标、空间位置与编号均已核验通过。</p>
      </section>
    </template>

    <PipeFixDialog :entry="fixEntry" @close="fixEntry = null" @saved="onSaved" />
    <PipeCreateDialog v-if="showCreate" @close="showCreate = false" @saved="onSaved" />
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import PipeCreateDialog from './PipeCreateDialog.vue'
import PipeFixDialog from './PipeFixDialog.vue'
import { PIPE_STATUSES, usePipeSectionStore, type PipeEntry, type WorkbenchGroup } from '@/stores/pipeSection'

const router = useRouter()
const store = usePipeSectionStore()

type ViewMode = 'line' | 'location'
const view = ref<ViewMode>('line')
const viewOptions = [
  { value: 'line' as ViewMode, label: '按管线' },
  { value: 'location' as ViewMode, label: '按空间位置' },
]
const statuses = PIPE_STATUSES

const workbench = computed(() => store.workbench)

const statCards = computed(() => {
  const counts = workbench.value?.counts ?? {}
  return [
    { label: '在役管段', value: counts['在役'] ?? 0, cls: '' },
    { label: '废弃管段', value: counts['废弃'] ?? 0, cls: 'card-danger' },
    { label: '封存/迁改中', value: (counts['封存'] ?? 0) + (counts['迁改中'] ?? 0), cls: '' },
    { label: '待补项', value: workbench.value?.issue_count ?? 0, cls: 'card-warn' },
  ]
})

async function switchView(next: ViewMode) {
  view.value = next
  await store.fetchWorkbench(next)
}

function membersOf(group: WorkbenchGroup): PipeEntry[] {
  const members: PipeEntry[] = []
  for (const status of statuses) {
    members.push(...group.buckets[status])
  }
  members.push(...group.unknown)
  return members
}

function bucketClass(status: string) {
  if (status === '废弃') return 'bucket-danger'
  if (status === '封存' || status === '迁改中') return 'bucket-muted'
  return ''
}

function statusKey(status: string) {
  if (status === '废弃') return 'danger'
  if (status === '封存' || status === '迁改中') return 'muted'
  return 'ok'
}

const fixEntry = ref<PipeEntry | null>(null)
const showCreate = ref(false)

function openFix(entry: PipeEntry) {
  fixEntry.value = entry
}

function onSaved() {
  fixEntry.value = null
  showCreate.value = false
}

async function toggleStatus(entry: PipeEntry) {
  const action = entry.status === '废弃' ? '恢复在役' : '标记废弃'
  try {
    await store.runAction(entry, action)
  } catch (error) {
    store.error = error instanceof Error ? error.message : '操作失败'
  }
}

function filterByStatus(status: string) {
  void router.push({ path: '/pipe_section', query: { status } })
}

onMounted(() => {
  void store.fetchWorkbench(view.value)
})
</script>
