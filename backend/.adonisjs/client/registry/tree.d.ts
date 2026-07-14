/* eslint-disable prettier/prettier */
import type { routes } from './index.ts'

export interface ApiDefinition {
  me: {
    show: typeof routes['me.show']
  }
  broker: {
    show: typeof routes['broker.show']
    upsert: typeof routes['broker.upsert']
    testConnection: typeof routes['broker.test_connection']
    destroy: typeof routes['broker.destroy']
  }
  tradingSettings: {
    show: typeof routes['trading_settings.show']
    update: typeof routes['trading_settings.update']
    reset: typeof routes['trading_settings.reset']
  }
  trades: {
    index: typeof routes['trades.index']
    open: typeof routes['trades.open']
    stats: typeof routes['trades.stats']
    show: typeof routes['trades.show']
  }
  daily: {
    index: typeof routes['daily.index']
    today: typeof routes['daily.today']
    show: typeof routes['daily.show']
  }
  logs: {
    index: typeof routes['logs.index']
    show: typeof routes['logs.show']
  }
  system: {
    health: typeof routes['system.health']
    status: typeof routes['system.status']
    killSwitch: typeof routes['system.kill_switch']
  }
}
