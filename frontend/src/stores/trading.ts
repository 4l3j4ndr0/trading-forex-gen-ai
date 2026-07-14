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
        const [status, today, open] = await Promise.all([
          api.get<{ data: { killSwitch: boolean; autoTradingEnabled: boolean; openPositions: number; dailyPnl: number } }>('/system/status'),
          api.get<{ data: DailySummary }>('/daily/today'),
          api.get<{ data: Trade[] }>('/trades/open'),
        ])

        this.killSwitch = status.data.killSwitch
        this.autoTrading = status.data.autoTradingEnabled
        this.openPositions = status.data.openPositions
        this.dailyPnl = status.data.dailyPnl
        this.dailySummary = today.data
        this.openTrades = open.data
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

    async loadLogs(date?: string) {
      const res = await api.get<{ data: HourlyLog[] }>('/logs/hourly', date ? { date } : {})
      this.hourlyLogs = res.data
    },

    async toggleKillSwitch(enabled: boolean) {
      await api.post('/system/kill-switch', { enabled })
      this.killSwitch = enabled
    },
  },
})
