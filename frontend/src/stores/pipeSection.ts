import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { request } from '@/api/client'

const ENDPOINT = '/api/pipe_section'

/** 管段状态；在役、废弃是工作台的主要分组口径，封存、迁改中同样保留计数 */
export const STATUS_ORDER = ['在役', '废弃', '封存', '迁改中'] as const
export type PipeStatus = (typeof STATUS_ORDER)[number]

export type PipeSection = {
  id: number
  status: PipeStatus
  管段编号: string | null
  管线类型: string | null
  材质规格: string | null
  埋设深度: string | null
  建设年代: string | null
  产权单位: string | null
  所在道路: string | null
  所属管线: string | null
  空间位置: string | null
  经度: number | null
  纬度: number | null
  hasCoordinate: boolean
  duplicate: boolean
  issues: string[]
}

export type OverviewGroup = {
  key: string
  label: string
  total: number
  counts: Partial<Record<PipeStatus, number>>
  items: PipeSection[]
}

export type Overview = {
  groupBy: 'pipeline' | 'location'
  total: number
  counts: Record<PipeStatus, number>
  pendingCoord: number
  duplicate: number
  groups: OverviewGroup[]
}

export const usePipeSectionStore = defineStore('pipeSection', () => {
  const items = ref<PipeSection[]>([])
  const total = ref(0)
  const overview = ref<Overview | null>(null)
  const groupBy = ref<'pipeline' | 'location'>('pipeline')
  const loading = ref(false)
  const errorMessage = ref('')

  const pendingItems = computed(() => items.value.filter((item) => item.issues.length > 0))

  function applyItems(next: PipeSection[]) {
    items.value = next
    total.value = next.length
  }

  async function fetchList(keyword = '', status = '') {
    loading.value = true
    errorMessage.value = ''
    const params = new URLSearchParams()
    if (keyword) params.set('keyword', keyword)
    if (status) params.set('status', status)
    params.set('size', '200')
    try {
      const response = await request(`${ENDPOINT}?${params.toString()}`)
      if (!response.ok) throw new Error('管段列表读取失败')
      const payload = await response.json()
      applyItems((payload.items ?? []) as PipeSection[])
    } catch (error) {
      errorMessage.value = error instanceof Error ? error.message : '管段档案列表读取失败'
    } finally {
      loading.value = false
    }
  }

  async function fetchOverview(mode?: 'pipeline' | 'location') {
    if (mode) groupBy.value = mode
    loading.value = true
    errorMessage.value = ''
    try {
      const response = await request(`${ENDPOINT}/overview?group_by=${groupBy.value}`)
      if (!response.ok) throw new Error('总览工作台读取失败')
      overview.value = (await response.json()) as Overview
    } catch (error) {
      errorMessage.value = error instanceof Error ? error.message : '总览工作台读取失败'
    } finally {
      loading.value = false
    }
  }

  /** 任何写入后统一刷新工作台与列表；详情页在保存后会顺带刷新自己，三处口径同源。 */
  async function refreshAll() {
    await Promise.all([fetchList(), fetchOverview()])
  }

  async function runAction(entry: PipeSection, action: string) {
    errorMessage.value = ''
    const response = await request(`${ENDPOINT}/${entry.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ values: { action } }),
    })
    const payload = await response.json().catch(() => null)
    if (!response.ok || !payload?.ok) {
      throw new Error(payload?.message || '管段档案动作未生效，请稍后重试')
    }
    await refreshAll()
  }

  async function correctEntry(id: number, values: Record<string, string>) {
    errorMessage.value = ''
    const response = await request(`${ENDPOINT}/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ values }),
    })
    const payload = await response.json().catch(() => null)
    if (!response.ok || !payload?.ok) {
      throw new Error(payload?.message || '档案修正未生效，请稍后重试')
    }
    await refreshAll()
    return payload.entry as PipeSection
  }

  async function fetchEntry(id: number): Promise<PipeSection> {
    const response = await request(`${ENDPOINT}/${id}`)
    if (!response.ok) {
      const payload = await response.json().catch(() => null)
      throw new Error(payload?.detail || `管段 ${id} 读取失败`)
    }
    return (await response.json()) as PipeSection
  }

  return {
    items,
    total,
    overview,
    groupBy,
    loading,
    errorMessage,
    pendingItems,
    fetchList,
    fetchOverview,
    refreshAll,
    runAction,
    correctEntry,
    fetchEntry,
  }
})
