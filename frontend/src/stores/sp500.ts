import { defineStore } from 'pinia'
import { api } from '@/services/api'

interface SP500Trade {
  id: string
  ticket: number
  side: string
  lotSize: number
  entryPrice: number
  exitPrice: number | null
  slPrice: number | null
  tpPrice: number | null
  slPoints: number | null
  tpPoints: number | null
  pnlPoints: number | null
  pnlUsd: number | null
  riskUsd: number | null
  comment: string | null
  basketId: string | null
  closeReason: string | null
  status: string
  openedAt: string
  closedAt: string | null
  holdingMinutes: number | null
}

interface SP500Settings {
  symbol: string
  pointValue: number
  minLot: number
  maxLot: number
  maxRiskPerTradePct: number
  maxDailyLossPct: number
  maxConsecutiveLosses: number
  minRrRatio: number
  maxOpenPositions: number
  amKillzoneStart: string
  amKillzoneEnd: string
  pmKillzoneStart: string
  pmKillzoneEnd: string
  premarketStart: string
  regularSessionStart: string
  regularSessionEnd: string
  newsBufferMinutes: number
  dailyTargetPct: number
  dailyTargetPoints: number
  minStructureScore: number
  minSweepDistancePoints: number
  killSwitch: boolean
  autoTradingEnabled: boolean
}

interface SP500Log {
  id: string
  timestamp: string
  decision: string
  tradesOpened: number
  tradesClosed: number
  floatingPnl: number
}

interface SP500Stats {
  totalTrades: number
  wins?: number
  losses?: number
  winRate?: number
  totalPnl?: number
  avgPnl?: number
  bestTrade?: number
  worstTrade?: number
}

export const useSP500Store = defineStore('sp500', {
  state: () => ({
    settings: null as SP500Settings | null,
    openTrades: [] as SP500Trade[],
    tradeHistory: [] as SP500Trade[],
    logs: [] as SP500Log[],
    stats: null as SP500Stats | null,
    loading: false,
  }),

  getters: {
    openPositions: (state) => state.openTrades.length,
    hasSettings: (state) => state.settings !== null,
  },

  actions: {
    async loadSettings() {
      try {
        const res = await api.get<{ data: SP500Settings | null }>('/sp500/settings')
        this.settings = res.data
      } catch {
        this.settings = null
      }
    },

    async saveSettings(data: Partial<SP500Settings>) {
      await api.put('/sp500/settings', data)
      await this.loadSettings()
    },

    async loadOpenTrades() {
      try {
        const res = await api.get<{ data: SP500Trade[] }>('/sp500/trades/open')
        this.openTrades = res.data
      } catch {
        this.openTrades = []
      }
    },

    async loadTrades(params?: Record<string, unknown>) {
      const res = await api.get<{ data: SP500Trade[]; meta: { total: number; page: number; totalPages: number } }>('/sp500/trades', params)
      this.tradeHistory = res.data
      return res
    },

    async loadStats() {
      try {
        const res = await api.get<{ data: SP500Stats }>('/sp500/trades/stats')
        this.stats = res.data
      } catch {
        this.stats = null
      }
    },

    async loadLogs(date?: string, page = 1, limit = 25) {
      const params: Record<string, unknown> = { page, limit }
      if (date) params.date = date
      const res = await api.get<{ data: SP500Log[]; meta: { total: number; page: number; totalPages: number; totals: { wins: number; losses: number; realizedPnl: number } } }>('/sp500/logs', params)
      this.logs = res.data
      return res.meta
    },

    async loadDashboard() {
      this.loading = true
      try {
        await Promise.allSettled([
          this.loadSettings(),
          this.loadOpenTrades(),
          this.loadStats(),
        ])
      } finally {
        this.loading = false
      }
    },
  },
})
