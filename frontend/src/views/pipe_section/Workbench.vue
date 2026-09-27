<template>
  <div class="workbench">
    <div class="switch-bar">
      <div class="seg-control" role="tablist">
        <button
          type="button"
          class="seg-item"
          :class="{ active: store.groupBy === 'pipeline' }"
          @click="switchMode('pipeline')"
        >
          按管线
        </button>
        <button
          type="button"
          class="seg-item"
          :class="{ active: store.groupBy === 'location' }"
          @click="switchMode('location')"
        >
          按空间位置
        </button>
      </div>
      <button class="btn ghost" type="button" @click="store.fetchOverview()">刷新分组</button>
    </div>

    <div class="stat-row">
      <article class="stat-card">
        <span class="stat-label">管段总数</span>
        <strong class="stat-value">{{ store.overview?.total ?? 0 }}</strong>
      </article>
      <article v-for="status in STATUS_ORDER" :key="status" class="stat-card" :class="statusCardClass(status)">
        <span class="stat-label">{{ status }}管段</span>
        <strong class="stat-value">{{ store.overview?.counts[status] ?? 0 }}</strong>
      </article>
      <article class="stat-card stat-warn">
        <span class="stat-label">坐标待补 / 有误</span>
        <strong class="stat-value">{{ store.overview?.pendingCoord ?? 0 }}</strong>
      </article>
      <article class="stat-card stat-warn">
        <span class="stat-label">编号重复（涉及管段）</span>
        <strong class="stat-value">{{ store.overview?.duplicate ?? 0 }}</strong>
      </article>
    </div>

    <section v-if="store.pendingItems.length" class="pending-panel">
      <header class="panel-head">
        <h3>待补项（{{ store.pendingItems.length }} 段，不会被静默丢弃）</h3>
        <span class="page-desc">坐标缺失/格式错误或编号重复的管段集中在此，修正后自动回到正常分组。</span>
      </header>
      <table class="data-table">
        <thead>
          <tr>
            <th>管段编号</th>
            <th>管线类型</th>
            <th>材质规格</th>
            <th>埋设深度</th>
            <th>状态</th>
            <th>待补原因</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in store.pendingItems" :key="`pending-${item.id}`">
            <td>
              {{ item.管段编号 ?? '—' }}
              <span class="tag tag-warn" v-if="item.duplicate">重复</span>
            </td>
            <td>{{ item.管线类型 ?? '—' }}</td>
            <td>{{ item.材质规格 ?? '—' }}</td>
            <td>{{ item.埋设深度 ?? '—' }}</td>
            <td><span class="status-badge" :class="`status-${item.status}`">{{ item.status }}</span></td>
            <td>
              <span v-for="issue in item.issues" :key="issue" class="tag tag-warn">{{ issue }}</span>
            </td>
            <td class="row-actions">
              <button class="link" type="button" @click="emit('correct', item)">修正</button>
              <RouterLink class="link" :to="`/pipe_section/${item.id}`">详情</RouterLink>
            </td>
          </tr>
        </tbody>
      </table>
    </section>

    <section class="group-board">
      <header class="panel-head">
        <h3>{{ store.groupBy === 'pipeline' ? '按管线分组' : '按空间位置分组' }}</h3>
        <span class="page-desc">
          {{ store.groupBy === 'pipeline' ? '每条管线下列出全部管段，并按在役/废弃分别统计。' : '按 0.01° 网格归集；坐标不全的管段统一进入"坐标待补"组。' }}
        </span>
      </header>
      <div v-if="store.overview && store.overview.groups.length" class="group-grid">
        <article
          v-for="group in store.overview.groups"
          :key="group.key"
          class="group-card"
          :class="{ 'group-missing': group.key === 'coord-missing' }"
        >
          <header class="group-head">
            <h4 :title="group.label">{{ group.label }}</h4>
            <span class="group-total">共 {{ group.total }} 段</span>
          </header>
          <div class="group-counts">
            <span
              v-for="status in STATUS_ORDER"
              :key="status"
              class="count-chip"
              :class="[{ active: status === '在役' || status === '废弃' }, `chip-${status}`]"
              :title="`${status}管段`"
            >
              {{ status }} {{ group.counts[status] ?? 0 }}
            </span>
          </div>
          <ul class="group-items">
            <li v-for="item in group.items" :key="`${group.key}-${item.id}`">
              <RouterLink class="link group-link" :to="`/pipe_section/${item.id}`">
                {{ item.管段编号 ?? '未编号' }}
              </RouterLink>
              <span class="group-item-meta">{{ item.管线类型 }} · {{ item.材质规格 }} · 埋深 {{ item.埋设深度 ?? '—' }}</span>
              <span class="status-badge" :class="`status-${item.status}`">{{ item.status }}</span>
              <span v-if="item.issues.length" class="tag tag-warn">待补</span>
            </li>
          </ul>
        </article>
      </div>
      <p v-else class="empty-state">暂无分组数据</p>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'

import { STATUS_ORDER, usePipeSectionStore, type PipeStatus, type PipeSection } from '@/stores/pipeSection'

const emit = defineEmits<{ (e: 'correct', entry: PipeSection): void }>()

const store = usePipeSectionStore()

onMounted(() => {
  if (!store.overview) void store.fetchOverview()
})

function switchMode(mode: 'pipeline' | 'location') {
  if (store.groupBy !== mode) void store.fetchOverview(mode)
}

function statusCardClass(status: PipeStatus) {
  return {
    'stat-active': status === '在役',
    'stat-discard': status === '废弃',
  }
}
</script>
