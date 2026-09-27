<template>
  <section class="page" data-module="pipe_section-detail">
    <header class="page-head">
      <div>
        <h2>管段详情</h2>
        <p class="page-desc">
          <RouterLink class="link" to="/pipe_section">返回管段档案</RouterLink>
          · 详情与工作台、列表共用同一份档案数据，任何修正或状态流转后三处同时更新。
        </p>
      </div>
    </header>

    <div v-if="loading" class="empty-state">管段明细加载中…</div>
    <template v-else-if="entry">
      <div v-if="entry.issues.length" class="issue-banner">
        <strong>该管段有待补项：</strong>
        <span v-for="issue in entry.issues" :key="issue" class="tag tag-warn">{{ issue }}</span>
        <button class="btn" type="button" @click="correcting = true">立即修正</button>
      </div>

      <div class="stat-row">
        <article class="stat-card">
          <span class="stat-label">当前状态</span>
          <strong class="stat-value">
            <span class="status-badge" :class="`status-${entry.status}`">{{ entry.status }}</span>
          </strong>
        </article>
        <article class="stat-card" :class="{ 'stat-active': entry.status === '在役' }">
          <span class="stat-label">在役分组</span>
          <strong class="stat-value">{{ entry.status === '在役' ? '是' : '否' }}</strong>
        </article>
        <article class="stat-card" :class="{ 'stat-discard': entry.status === '废弃' }">
          <span class="stat-label">废弃分组</span>
          <strong class="stat-value">{{ entry.status === '废弃' ? '是' : '否' }}</strong>
        </article>
        <article class="stat-card" :class="{ 'stat-warn': !entry.hasCoordinate }">
          <span class="stat-label">坐标</span>
          <strong class="stat-value">{{ entry.hasCoordinate ? '已定位' : '待补' }}</strong>
        </article>
      </div>

      <table class="data-table detail-table">
        <tbody>
          <tr v-for="field in detailFields" :key="field.name">
            <th>{{ field.label }}</th>
            <td>{{ displayValue(field.name) }}</td>
          </tr>
          <tr>
            <th>定位坐标</th>
            <td>
              <template v-if="entry.hasCoordinate">{{ entry.经度 }}, {{ entry.纬度 }}</template>
              <span v-else class="tag tag-warn">坐标待补 / 待修正</span>
            </td>
          </tr>
        </tbody>
      </table>

      <div class="detail-actions">
        <button class="btn" type="button" @click="correcting = true">修正档案</button>
        <button
          v-for="action in availableActions"
          :key="action"
          class="btn"
          :class="{ primary: action === '恢复在役' }"
          type="button"
          :disabled="acting"
          @click="runAction(action)"
        >
          {{ action }}
        </button>
      </div>
      <p v-if="actionError" class="error-text">{{ actionError }}</p>
    </template>
    <div v-else class="empty-state">{{ loadError || '管段不存在或已归档' }}</div>

    <CorrectDialog
      v-if="correcting && entry"
      :entry="entry"
      @close="correcting = false"
      @saved="onSaved"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import { STATUS_ORDER, usePipeSectionStore, type PipeSection, type PipeStatus } from '@/stores/pipeSection'
import CorrectDialog from './CorrectDialog.vue'

const route = useRoute()
const store = usePipeSectionStore()

const entry = ref<PipeSection | null>(null)
const loading = ref(true)
const loadError = ref('')
const correcting = ref(false)
const acting = ref(false)
const actionError = ref('')

const detailFields = [
  { name: '管段编号', label: '管段编号' },
  { name: '管线类型', label: '管线类型' },
  { name: '材质规格', label: '材质规格' },
  { name: '埋设深度', label: '埋设深度' },
  { name: '所属管线', label: '所属管线（按管线分组依据）' },
  { name: '空间位置', label: '空间位置' },
  { name: '所在道路', label: '所在道路' },
  { name: '建设年代', label: '建设年代' },
  { name: '产权单位', label: '产权单位' },
] as const

const ACTIONS: Record<PipeStatus, string[]> = {
  在役: ['封存管段', '登记迁改', '标记废弃'],
  废弃: ['恢复在役'],
  封存: ['恢复在役', '登记迁改', '标记废弃'],
  迁改中: ['恢复在役', '封存管段', '标记废弃'],
}

const availableActions = computed(() => (entry.value ? ACTIONS[entry.value.status] : []))

function displayValue(name: (typeof detailFields)[number]['name']): string {
  if (!entry.value) return '—'
  const value = entry.value[name]
  return value === null || value === undefined || value === '' ? '—' : String(value)
}

async function loadEntry() {
  loading.value = true
  loadError.value = ''
  const id = Number(route.params.id)
  try {
    entry.value = await store.fetchEntry(id)
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : '管段读取失败'
  } finally {
    loading.value = false
  }
}

async function runAction(action: string) {
  if (!entry.value) return
  acting.value = true
  actionError.value = ''
  try {
    await store.runAction(entry.value, action)
    await loadEntry()
  } catch (error) {
    actionError.value = error instanceof Error ? error.message : '管段档案操作失败'
  } finally {
    acting.value = false
  }
}

async function onSaved(saved: PipeSection) {
  correcting.value = false
  entry.value = saved
  // store.correctEntry 已刷新工作台与列表；saved 是最新详情，三处现在同源
}

onMounted(loadEntry)
</script>
