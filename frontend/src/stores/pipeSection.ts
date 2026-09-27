/**
 * 管段档案共享状态：总览工作台、列表、详情三处共用同一份数据，
 * 任何状态流转、字段修正、登记都走这里的动作并统一刷新，保证三处数量与状态同时更新。
 */
import { defineStore } from 'pinia'

import { request } from '@/api/client'

const ENDPOINT = '/api/pipe_section'
export const PIPE_STATUSES = ['在役', '废弃', '封存', '迁改中'] as const
export const PIPE_ACTIONS = ['恢复在役', '标记废弃', '封存管段', '登记迁改'] as const
export const PIPE_ISSUE_LABELS = ['坐标缺失', '坐标格式有误', '空间位置缺失', '管段编号重复'] as const

export type PipeEntry = {
  id: number
  status: string
  pending?: boolean
  abnormal?: boolean
  issues: string[]
  has_issue: boolean
  管段编号: string
  管线类型: string
  材质规格: string
  埋设深度: string
  空间位置?: string
  坐标?: string
  建设年代?: string
  产权单位?: string
  所在道路?: string
  管段状态?: string
  [key: string]: string | number | boolean | null | string[] | undefined
}

export type WorkbenchGroup = {
  key: string
  label: string
  missing_location: boolean
  buckets: Record<string, PipeEntry[]>
  unknown: PipeEntry[]
  counts: Record<string, number>
}

export type Workbench = {
  view: 'line' | 'location'
  groups: WorkbenchGroup[]
  counts: Record<string, number>
  issues: PipeEntry[]
  issue_count: number
}

export type ListFilters = {
  keyword?: string
  status?: string
  issue?: string
  page?: number
  size?: number
}

type State = {
  workbench: Workbench | null
  view: 'line' | 'location'
  entries: PipeEntry[]
  total: number
  filters: ListFilters
  detail: PipeEntry | null
  loading: boolean
  error: string
  lastMessage: string
}

async function unwrap(response: Response, fallback: string) {
  const payload = await response.json().catch(() => null)
  if (!response.ok || !payload) {
    throw new Error(payload?.detail ?? payload?.message ?? fallback)
  }
  return payload
}

export const usePipeSectionStore = defineStore('pipeSection', {
  state: (): State => ({
    workbench: null,
    view: 'line',
    entries: [],
    total: 0,
    filters: { page: 1, size: 200 },
    detail: null,
    loading: false,
    error: '',
    lastMessage: '',
  }),

  actions: {
    async fetchWorkbench(view?: 'line' | 'location') {
      const nextView = view ?? this.view
      this.view = nextView
      this.loading = true
      this.error = ''
      try {
        const response = await request(`${ENDPOINT}/workbench?view=${nextView}`)
        this.workbench = await unwrap(response, '管段总览工作台读取失败')
      } catch (error) {
        this.error = error instanceof Error ? error.message : '管段总览工作台读取失败'
      } finally {
        this.loading = false
      }
    },

    async fetchList(nextFilters?: Partial<ListFilters>) {
      if (nextFilters) {
        this.filters = { ...this.filters, ...nextFilters }
      }
      this.loading = true
      this.error = ''
      try {
        const params = new URLSearchParams()
        for (const [key, value] of Object.entries(this.filters)) {
          if (value !== undefined && value !== null && value !== '') {
            params.set(key, String(value))
          }
        }
        const response = await request(`${ENDPOINT}?${params.toString()}`)
        const payload = await unwrap(response, '管段列表读取失败')
        this.entries = payload.items ?? []
        this.total = payload.total ?? this.entries.length
      } catch (error) {
        this.error = error instanceof Error ? error.message : '管段列表读取失败'
      } finally {
        this.loading = false
      }
    },

    async fetchDetail(id: number) {
      this.loading = true
      this.error = ''
      try {
        const response = await request(`${ENDPOINT}/${id}`)
        this.detail = await unwrap(response, '管段详情读取失败')
      } catch (error) {
        this.detail = null
        this.error = error instanceof Error ? error.message : '管段详情读取失败'
      } finally {
        this.loading = false
      }
    },

    clearDetail() {
      this.detail = null
      this.error = ''
    },

    /** 写操作之后统一刷新工作台与列表；详情页打开时也同步刷新当前明细。 */
    async refreshAfterMutation() {
      await Promise.all([this.fetchWorkbench(), this.fetchList()])
      if (this.detail) {
        await this.fetchDetail(this.detail.id)
      }
    },

    async runAction(entry: PipeEntry, action: string) {
      this.error = ''
      const response = await request(`${ENDPOINT}/${entry.id}/actions`, {
        method: 'POST',
        body: JSON.stringify({ values: { action } }),
      })
      const payload = await unwrap(response, '管段状态未更新，请稍后重试')
      if (!payload.ok) {
        throw new Error(payload.message)
      }
      this.lastMessage = payload.message
      await this.refreshAfterMutation()
    },

    async correctEntry(id: number, values: Record<string, string>) {
      this.error = ''
      const response = await request(`${ENDPOINT}/${id}`, {
        method: 'PUT',
        body: JSON.stringify({ values }),
      })
      const payload = await unwrap(response, '管段信息未保存')
      if (!payload.ok) {
        throw new Error(payload.message)
      }
      this.lastMessage = payload.message
      await this.refreshAfterMutation()
      return payload.entry as PipeEntry
    },

    async createEntry(values: Record<string, string>) {
      this.error = ''
      const response = await request(ENDPOINT, {
        method: 'POST',
        body: JSON.stringify({ values }),
      })
      const payload = await unwrap(response, '管段登记失败')
      if (!payload.ok) {
        throw new Error(payload.message)
      }
      this.lastMessage = payload.message
      await this.refreshAfterMutation()
      return payload.entry as PipeEntry
    },
  },
})
