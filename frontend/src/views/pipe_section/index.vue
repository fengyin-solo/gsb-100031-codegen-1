<template>
  <section class="page" data-module="pipe_section">
    <header class="page-head">
      <div>
        <h2>管段档案管理</h2>
        <p class="page-desc">
          保留管段编号、管线类型、材质规格、埋设深度；总览工作台可在"按管线"与"按空间位置"间切换，
          在役、废弃分别成组；坐标缺失或编号重复只标记待补、不静默丢弃，可直接修正。
        </p>
      </div>
      <div class="page-actions">
        <button class="btn" type="button" @click="exportRows">导出管段档案清单</button>
      </div>
    </header>

    <nav class="tab-bar">
      <button
        type="button"
        class="tab-item"
        :class="{ active: activeTab === 'workbench' }"
        @click="activeTab = 'workbench'"
      >
        总览工作台
      </button>
      <button
        type="button"
        class="tab-item"
        :class="{ active: activeTab === 'list' }"
        @click="switchToList"
      >
        档案列表
      </button>
    </nav>

    <Workbench v-show="activeTab === 'workbench'" @correct="openCorrect" />
    <ArchiveList v-if="activeTab === 'list'" @correct="openCorrect" />

    <CorrectDialog
      v-if="correctTarget"
      :entry="correctTarget"
      @close="closeCorrect"
      @saved="onSaved"
    />

    <footer v-if="store.errorMessage" class="page-foot">
      <span class="error-text">{{ store.errorMessage }}</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { usePipeSectionStore, type PipeSection } from '@/stores/pipeSection'
import Workbench from './Workbench.vue'
import ArchiveList from './ArchiveList.vue'
import CorrectDialog from './CorrectDialog.vue'

const store = usePipeSectionStore()

const activeTab = ref<'workbench' | 'list'>('workbench')
const correctTarget = ref<PipeSection | null>(null)

function switchToList() {
  activeTab.value = 'list'
}

function openCorrect(entry: PipeSection) {
  // 以当前最新档案为底，避免弹窗里带着陈旧的待补标记
  const latest = store.items.find((item) => item.id === entry.id)
  correctTarget.value = latest ?? entry
}

function closeCorrect() {
  correctTarget.value = null
}

async function onSaved() {
  // correctEntry 已触发 refreshAll，工作台与列表的状态、数量同步更新
  correctTarget.value = null
}

function exportRows() {
  window.open('/api/pipe_section/export', '_blank')
}

onMounted(() => {
  // 列表数据在挂载时也拉一份：待补面板依赖 items，且切到列表页时即时可见
  void store.fetchList()
  void store.fetchOverview()
})
</script>
