<template>
  <div class="modal-mask" @click.self="emit('close')">
    <div class="modal" role="dialog" aria-modal="true">
      <header class="modal-head">
        <h3>登记管段</h3>
        <span class="modal-sub">必填项缺失或坐标非法会被拦下；编号重复也会登记并标记待核，不做静默丢弃。</span>
      </header>

      <form class="modal-form" @submit.prevent="submit">
        <label v-for="field in fields" :key="field.name" class="modal-field">
          <span>
            {{ field.name }}
            <em v-if="field.required" class="required">必填</em>
          </span>
          <input v-model="form[field.name]" :placeholder="placeholderFor(field.name)" />
        </label>

        <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>
        <p v-else class="modal-hint">坐标按「经度,纬度」填写，例如 120.102,30.286；暂无坐标可留空，留空会标记为坐标待补。</p>

        <footer class="modal-foot">
          <button class="btn ghost" type="button" @click="emit('close')">取消</button>
          <button class="btn primary" type="submit" :disabled="saving">{{ saving ? '提交中…' : '登记管段' }}</button>
        </footer>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'

import { usePipeSectionStore } from '@/stores/pipeSection'

const emit = defineEmits<{ (e: 'close'): void; (e: 'saved', message: string): void }>()

const store = usePipeSectionStore()

const fields = [
  { name: '管段编号', required: true },
  { name: '管线类型', required: true },
  { name: '材质规格', required: true },
  { name: '埋设深度', required: true },
  { name: '空间位置', required: false },
  { name: '坐标', required: false },
  { name: '所在道路', required: false },
  { name: '产权单位', required: false },
  { name: '建设年代', required: false },
] as const

const form = reactive<Record<string, string>>(Object.fromEntries(fields.map((field) => [field.name, ''])))
const saving = ref(false)
const errorMessage = ref('')

function placeholderFor(field: string) {
  if (field === '坐标') return '经度,纬度，如 120.102,30.286'
  return `请输入${field}`
}

async function submit() {
  saving.value = true
  errorMessage.value = ''
  try {
    const values: Record<string, string> = {}
    for (const field of fields) {
      values[field.name] = form[field.name].trim()
    }
    await store.createEntry(values)
    emit('saved', store.lastMessage)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '管段登记失败'
  } finally {
    saving.value = false
  }
}
</script>
