import { defineStore } from 'pinia'
import { api } from '@/services/api'

interface Trade {
  id: string
  ticket: number
  side: string
  lot_size: number
  entry_price: number
  exit_price: number | null
  sl_pips: number
  tp_pips: number
  pnl_pips: number | null
  pnl_usd: number | null
  status: string
  close_reason: string | null
  comment: string | null
  opened_at: string
  closed_at: string | null
  holding_minutes: number | null
}

interface DailySummary {
  date: string
  realizedPnl: number
  tradesTotal: number
  tradesWon: number
  tradesLost: number
  winRate: number
  targetReached: boolean
}

interface HourlyLog {
  id: string
  timestamp: string
  utc_hour: number
  session: string
  trades_opened: number
  trades_closed: number
  trades_skipped: number
  pnl_this_hour: number
  decision_summary: string
  market_context: string | null
}

export const useTradingStore = defineStore('trading', {
  state: () => ({
    balance: 0,
    equity: 0,
    dailyPnl: 0,
    openPositions: 0,
    killSwitch: false,
    autoTrading: true,
    accountType: 'unknown',
    openTrades: [] as Trade[],
    tradeHistory: [] as Trade[],
    dailySummary: null as DailySummary | null,
    hourlyLogs: [] as HourlyLog[],
    stats: null as Record<string, number> | null,
    loading: false,
  }),

  actions: {
    async loadDashboard() {
      this.loading = true
      try {
        const [status, today, open] = await Promise.allSettled([
          api.get<{ data: { killSwitch: boolean; autoTradingEnabled: boolean; openPositions: number; dailyPnl: number; balance: number; equity: number; accountType: string } }>('/system/status'),
          api.get<{ data: DailySummary }>('/daily/today'),
          api.get<{ data: Trade[] }>('/trades/open'),
        ])

        if (status.status === 'fulfilled') {
          this.killSwitch = status.value.data.killSwitch
          this.autoTrading = status.value.data.autoTradingEnabled
          this.openPositions = status.value.data.openPositions
          this.dailyPnl = status.value.data.dailyPnl
          this.balance = status.value.data.balance
          this.equity = status.value.data.equity
          this.accountType = status.value.data.accountType
        }
        if (today.status === 'fulfilled') {
          this.dailySummary = today.value.data
        }
        if (open.status === 'fulfilled') {
          this.openTrades = open.value.data
        }
      } catch (e) {
        console.error('Failed to load dashboard', e)
      } finally {
        this.loading = false
      }
    },

    async loadTrades(params?: Record<string, unknown>) {
      const res = await api.get<{ data: Trade[]; meta: { total: number } }>('/trades', params)
      this.tradeHistory = res.data
      return res
    },

    async loadStats(period = '30d') {
      const res = await api.get<{ data: Record<string, number> }>('/trades/stats', { period })
      this.stats = res.data
    },

    async loadLogs(date?: string, page = 1, limit = 25) {
      const params: Record<string, unknown> = { page, limit }
      if (date) params.date = date
      const res = await api.get<{ data: HourlyLog[]; meta: { total: number; page: number; totalPages: number } }>('/logs/hourly', params)
      this.hourlyLogs = res.data
      return res.meta
    },

    async toggleKillSwitch(enabled: boolean) {
      await api.post('/system/kill-switch', { enabled })
      this.killSwitch = enabled
    },
  },
})
