<template>
  <section class="page" data-module="pipe_section_detail">
    <header class="page-head">
      <div>
        <h2>管段详情</h2>
        <p class="page-desc">单条管段的档案字段、待补项与状态流转；此处执行的操作会同时更新总览工作台与列表。</p>
      </div>
      <div class="page-actions">
        <RouterLink class="btn" to="/pipe_section/workbench">返回总览工作台</RouterLink>
        <RouterLink class="btn" to="/pipe_section">返回档案列表</RouterLink>
      </div>
    </header>

    <div v-if="store.loading && !entry" class="panel-empty">详情加载中…</div>
    <div v-else-if="!entry" class="panel-empty">
      <p class="error-text">{{ store.error || '管段不存在或已归档' }}</p>
    </div>

    <template v-else>
      <div class="detail-head">
        <div>
          <h3>{{ entry.管段编号 }}</h3>
          <span class="status-tag" :class="`tag-${statusKey(entry.status)}`">{{ entry.status }}</span>
          <span v-for="issue in entry.issues" :key="issue" class="issue-tag">{{ issue }}</span>
        </div>
        <div class="row-actions">
          <button class="btn" type="button" @click="showFix = true">修正档案信息</button>
          <button
            v-for="action in availableActions"
            :key="action"
            class="btn"
            :class="{ primary: action === '恢复在役', danger: action === '标记废弃' }"
            type="button"
            @click="runAction(action)"
          >
            {{ action }}
          </button>
        </div>
      </div>

      <table class="data-table detail-table">
        <tbody>
          <tr v-for="field in displayFields" :key="field.name">
            <th>{{ field.name }}</th>
            <td>
              <template v-if="entry[field.name]">{{ entry[field.name] }}</template>
              <template v-else><span class="muted-text">未登记</span></template>
            </td>
          </tr>
        </tbody>
      </table>

      <section class="issue-panel" v-if="entry.issues.length">
        <header class="issue-panel-head">
          <h3>待补项（{{ entry.issues.length }}）</h3>
          <p>以下问题不会被静默丢弃，补齐信息保存后会自动重新核验。</p>
        </header>
        <ul class="issue-list">
          <li v-for="issue in entry.issues" :key="issue">
            <span class="issue-tag">{{ issue }}</span>
            <span class="issue-tip">{{ issueHint(issue) }}</span>
          </li>
        </ul>
      </section>

      <footer class="page-foot">
        <span v-if="store.error" class="error-text">{{ store.error }}</span>
        <span v-else-if="store.lastMessage" class="ok-text">{{ store.lastMessage }}</span>
      </footer>
    </template>

    <PipeFixDialog :entry="entry" v-if="showFix" @close="showFix = false" @saved="showFix = false" />
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import PipeFixDialog from './PipeFixDialog.vue'
import { usePipeSectionStore } from '@/stores/pipeSection'

const route = useRoute()
const store = usePipeSectionStore()
const showFix = ref(false)

const displayFields = [
  { name: '管线类型' },
  { name: '材质规格' },
  { name: '埋设深度' },
  { name: '空间位置' },
  { name: '坐标' },
  { name: '所在道路' },
  { name: '产权单位' },
  { name: '建设年代' },
]

const entry = computed(() => store.detail)

const availableActions = computed(() => {
  if (!entry.value) return []
  const targets: Record<string, string> = {
    恢复在役: '在役',
    标记废弃: '废弃',
    封存管段: '封存',
    登记迁改: '迁改中',
  }
  return Object.keys(targets).filter((action) => targets[action] !== entry.value!.status)
})

function statusKey(status: string) {
  if (status === '废弃') return 'danger'
  if (status === '封存' || status === '迁改中') return 'muted'
  return 'ok'
}

function issueHint(issue: string) {
  if (issue === '坐标缺失' || issue === '坐标格式有误') {
    return '请按「经度,纬度」补录或更正坐标，例如 120.102,30.286'
  }
  if (issue === '空间位置缺失') {
    return '请补录所属片区或道路，便于按空间位置归组'
  }
  if (issue === '管段编号重复') {
    return '档案中存在相同管段编号，请核对后改成正确的唯一编号'
  }
  return ''
}

async function runAction(action: string) {
  if (!entry.value) return
  try {
    await store.runAction(entry.value, action)
  } catch (error) {
    store.error = error instanceof Error ? error.message : '管段状态更新失败'
  }
}

async function load() {
  const id = Number(route.params.id)
  if (Number.isFinite(id)) {
    await store.fetchDetail(id)
  }
}

watch(() => route.params.id, () => void load())
onMounted(load)
</script>
