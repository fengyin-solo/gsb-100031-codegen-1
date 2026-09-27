<template>
  <div class="modal-mask" @click.self="emit('close')">
    <div class="modal-card">
      <header class="modal-head">
        <h3>修正管段档案 · {{ entry.管段编号 }}</h3>
        <button class="link" type="button" @click="emit('close')">关闭</button>
      </header>

      <div v-if="entry.issues.length" class="issue-banner">
        <strong>待补项：</strong>
        <span v-for="issue in entry.issues" :key="issue" class="tag tag-warn">{{ issue }}</span>
      </div>

      <form class="correct-form" @submit.prevent="submit">
        <label v-for="field in textFields" :key="field.name" class="form-item">
          <span>{{ field.label }}<em v-if="field.required">*</em></span>
          <input v-model="form[field.name]" :placeholder="field.placeholder" />
        </label>
        <label v-for="field in coordFields" :key="field.name" class="form-item">
          <span>{{ field.label }}</span>
          <input v-model="form[field.name]" inputmode="decimal" :placeholder="field.placeholder" />
        </label>
        <p class="form-hint">经度与纬度需同时填写，任留一项会被拦截；坐标缺失时此管段归入"坐标待补"组。</p>
        <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>
        <footer class="modal-foot">
          <button class="btn ghost" type="button" @click="emit('close')">取消</button>
          <button class="btn primary" type="submit" :disabled="saving">
            {{ saving ? '提交中…' : '保存修正' }}
          </button>
        </footer>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'

import { usePipeSectionStore, type PipeSection } from '@/stores/pipeSection'

const props = defineProps<{ entry: PipeSection }>()
const emit = defineEmits<{ (e: 'close'): void; (e: 'saved', entry: PipeSection): void }>()

const store = usePipeSectionStore()

const textFields = [
  { name: '管段编号', label: '管段编号', required: true, placeholder: '如 PIPE-0008' },
  { name: '所属管线', label: '所属管线', required: false, placeholder: '按管线分组的依据，如 滨河路供水干管' },
  { name: '空间位置', label: '空间位置', required: false, placeholder: '如 滨河路（东环至建设路段）' },
  { name: '管线类型', label: '管线类型', required: true, placeholder: '给水 / 排水 / 燃气 / 供热 / 电力' },
  { name: '材质规格', label: '材质规格', required: true, placeholder: '如 DN300 球墨铸铁管' },
  { name: '埋设深度', label: '埋设深度', required: false, placeholder: '如 1.8m' },
  { name: '所在道路', label: '所在道路', required: false, placeholder: '如 滨河路' },
] as const

const coordFields = [
  { name: '经度', label: '经度', placeholder: '如 116.40' },
  { name: '纬度', label: '纬度', placeholder: '如 39.91' },
] as const

type FormKey = (typeof textFields)[number]['name'] | (typeof coordFields)[number]['name']

function initialValue(value: string | number | null): string {
  return value === null || value === undefined ? '' : String(value)
}

const form = reactive<Record<FormKey, string>>({
  管段编号: initialValue(props.entry.管段编号),
  所属管线: initialValue(props.entry.所属管线),
  空间位置: initialValue(props.entry.空间位置),
  管线类型: initialValue(props.entry.管线类型),
  材质规格: initialValue(props.entry.材质规格),
  埋设深度: initialValue(props.entry.埋设深度),
  所在道路: initialValue(props.entry.所在道路),
  经度: initialValue(props.entry.经度),
  纬度: initialValue(props.entry.纬度),
})

const saving = ref(false)
const errorMessage = ref('')

async function submit() {
  saving.value = true
  errorMessage.value = ''
  try {
    // 经纬度留空时显式传空字符串，服务端据此识别为"坐标待补"而不是解析错误
    const values: Record<string, string> = {}
    for (const key of Object.keys(form) as FormKey[]) {
      values[key] = form[key].trim()
    }
    const saved = await store.correctEntry(props.entry.id, values)
    emit('saved', saved)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '档案修正失败'
  } finally {
    saving.value = false
  }
}
</script>
