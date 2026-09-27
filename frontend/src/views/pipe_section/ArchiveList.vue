<template>
  <div class="archive-list">
    <form class="filter-bar" @submit.prevent="reload">
      <label class="filter-item">
        <span>管段编号</span>
        <input v-model="keyword" placeholder="按管段编号检索" />
      </label>
      <label class="filter-item">
        <span>管段状态</span>
        <select v-model="status">
          <option value="">全部状态</option>
          <option v-for="item in STATUS_ORDER" :key="item" :value="item">{{ item }}</option>
        </select>
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
      <button class="btn ghost" type="button" @click="exportRows">导出清单</button>
    </form>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column">{{ column }}</th>
          <th>数据质量</th>
          <th>可执行动作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in store.items" :key="String(row.id)">
          <td>{{ row.管段编号 ?? '—' }}</td>
          <td>{{ row.管线类型 ?? '—' }}</td>
          <td>{{ row.材质规格 ?? '—' }}</td>
          <td>{{ row.埋设深度 ?? '—' }}</td>
          <td>{{ row.所属管线 ?? '—' }}</td>
          <td>
            <span class="status-badge" :class="`status-${row.status}`">{{ row.status }}</span>
          </td>
          <td>
            <template v-if="row.issues.length">
              <span v-for="issue in row.issues" :key="issue" class="tag tag-warn">{{ issue }}</span>
            </template>
            <span v-else class="tag tag-ok">完整</span>
          </td>
          <td class="row-actions">
            <RouterLink class="link" :to="`/pipe_section/${row.id}`">详情</RouterLink>
            <button class="link" type="button" @click="emit('correct', row)">修正</button>
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
        <tr v-if="!store.items.length">
          <td :colspan="columns.length + 2" class="empty-state">暂无管段档案数据</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ store.total }} 条管段档案记录（与工作台、详情同源更新）</span>
      <span v-if="store.errorMessage" class="error-text">{{ store.errorMessage }}</span>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { STATUS_ORDER, usePipeSectionStore, type PipeSection, type PipeStatus } from '@/stores/pipeSection'

const emit = defineEmits<{ (e: 'correct', entry: PipeSection): void }>()

const store = usePipeSectionStore()

const columns = ['管段编号', '管线类型', '材质规格', '埋设深度', '所属管线', '管段状态']
const keyword = ref('')
const status = ref('')

const ACTIONS: Record<PipeStatus, string[]> = {
  在役: ['封存管段', '登记迁改', '标记废弃'],
  废弃: ['恢复在役'],
  封存: ['恢复在役', '登记迁改', '标记废弃'],
  迁改中: ['恢复在役', '封存管段', '标记废弃'],
}

function availableActions(current: PipeStatus): string[] {
  return ACTIONS[current] ?? ['恢复在役']
}

async function reload() {
  await store.fetchList(keyword.value.trim(), status.value)
}

function resetFilters() {
  keyword.value = ''
  status.value = ''
  void reload()
}

function exportRows() {
  window.open('/api/pipe_section/export', '_blank')
}

async function runAction(action: string, row: PipeSection) {
  try {
    await store.runAction(row, action)
  } catch (error) {
    // 错误已落在 store.errorMessage 的场景之外，这里兜底提示
    window.alert(error instanceof Error ? error.message : '管段档案操作失败')
  }
}

onMounted(reload)
</script>
