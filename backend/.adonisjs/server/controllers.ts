export const controllers = {
  Me: () => import('#controllers/me_controller'),
  Broker: () => import('#controllers/broker_controller'),
  TradingSettings: () => import('#controllers/trading_settings_controller'),
  Trades: () => import('#controllers/trades_controller'),
  Daily: () => import('#controllers/daily_controller'),
  Logs: () => import('#controllers/logs_controller'),
  System: () => import('#controllers/system_controller'),
}
