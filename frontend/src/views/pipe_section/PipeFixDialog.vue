<template>
  <div v-if="entry" class="modal-mask" @click.self="emit('close')">
    <div class="modal" role="dialog" aria-modal="true">
      <header class="modal-head">
        <h3>修正管段信息</h3>
        <span class="modal-sub">{{ entry.管段编号 }} · 待补项：{{ entry.issues.join('、') || '无' }}</span>
      </header>

      <div v-if="entry.issues.length" class="issue-banner">
        该管段存在 {{ entry.issues.length }} 项待补：<strong>{{ entry.issues.join('、') }}</strong>，补齐保存后自动重新核验。
      </div>

      <form class="modal-form" @submit.prevent="submit">
        <label v-for="field in editableFields" :key="field" class="modal-field">
          <span>
            {{ field }}
            <em v-if="requiredFields.includes(field)" class="required">必填</em>
          </span>
          <input v-model="form[field]" :placeholder="placeholderFor(field)" />
        </label>

        <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>
        <p v-else-if="hint" class="modal-hint">{{ hint }}</p>

        <footer class="modal-foot">
          <button class="btn ghost" type="button" @click="emit('close')">取消</button>
          <button class="btn primary" type="submit" :disabled="saving">
            {{ saving ? '保存中…' : '保存并重新核验' }}
          </button>
        </footer>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'

import { usePipeSectionStore, type PipeEntry } from '@/stores/pipeSection'

const props = defineProps<{ entry: PipeEntry | null }>()
const emit = defineEmits<{ (e: 'close'): void; (e: 'saved', message: string): void }>()

const store = usePipeSectionStore()

const editableFields = ['管段编号', '管线类型', '材质规格', '埋设深度', '空间位置', '坐标', '所在道路', '产权单位', '建设年代']
const requiredFields = ['管段编号', '管线类型', '材质规格', '埋设深度']

const form = reactive<Record<string, string>>({})
const saving = ref(false)
const errorMessage = ref('')

const hint = '坐标按「经度,纬度」填写，例如 120.102,30.286；重复编号请改成正确的唯一编号。'

function placeholderFor(field: string) {
  if (field === '坐标') return '经度,纬度，如 120.102,30.286'
  return `请输入${field}`
}

watch(
  () => props.entry,
  (entry) => {
    errorMessage.value = ''
    for (const field of editableFields) {
      const value = entry?.[field]
      form[field] = typeof value === 'string' ? value : ''
    }
  },
  { immediate: true },
)

async function submit() {
  if (!props.entry) return
  saving.value = true
  errorMessage.value = ''
  try {
    const values: Record<string, string> = {}
    for (const field of editableFields) {
      values[field] = form[field].trim()
    }
    await store.correctEntry(props.entry.id, values)
    emit('saved', store.lastMessage)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '保存失败'
  } finally {
    saving.value = false
  }
}
</script>
