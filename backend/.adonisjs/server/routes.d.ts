import '@adonisjs/core/types/http'

type ParamValue = string | number | bigint | boolean

export type ScannedRoutes = {
  ALL: {
    'me.show': { paramsTuple?: []; params?: {} }
    'pairs.index': { paramsTuple?: []; params?: {} }
    'broker.show': { paramsTuple?: []; params?: {} }
    'broker.upsert': { paramsTuple?: []; params?: {} }
    'broker.test_connection': { paramsTuple?: []; params?: {} }
    'broker.destroy': { paramsTuple?: []; params?: {} }
    'trading_settings.show': { paramsTuple?: []; params?: {} }
    'trading_settings.update': { paramsTuple?: []; params?: {} }
    'trading_settings.reset': { paramsTuple?: []; params?: {} }
    'trades.index': { paramsTuple?: []; params?: {} }
    'trades.open': { paramsTuple?: []; params?: {} }
    'trades.stats': { paramsTuple?: []; params?: {} }
    'trades.show': { paramsTuple: [ParamValue]; params: {'id': ParamValue} }
    'daily.index': { paramsTuple?: []; params?: {} }
    'daily.today': { paramsTuple?: []; params?: {} }
    'daily.show': { paramsTuple: [ParamValue]; params: {'date': ParamValue} }
    'logs.index': { paramsTuple?: []; params?: {} }
    'logs.show': { paramsTuple: [ParamValue]; params: {'id': ParamValue} }
    'system.health': { paramsTuple?: []; params?: {} }
    'system.status': { paramsTuple?: []; params?: {} }
    'system.kill_switch': { paramsTuple?: []; params?: {} }
    'sp_500_settings.show': { paramsTuple?: []; params?: {} }
    'sp_500_settings.upsert': { paramsTuple?: []; params?: {} }
    'sp_500_trades.index': { paramsTuple?: []; params?: {} }
    'sp_500_trades.open': { paramsTuple?: []; params?: {} }
    'sp_500_trades.stats': { paramsTuple?: []; params?: {} }
    'sp_500_logs.index': { paramsTuple?: []; params?: {} }
  }
  GET: {
    'me.show': { paramsTuple?: []; params?: {} }
    'pairs.index': { paramsTuple?: []; params?: {} }
    'broker.show': { paramsTuple?: []; params?: {} }
    'trading_settings.show': { paramsTuple?: []; params?: {} }
    'trades.index': { paramsTuple?: []; params?: {} }
    'trades.open': { paramsTuple?: []; params?: {} }
    'trades.stats': { paramsTuple?: []; params?: {} }
    'trades.show': { paramsTuple: [ParamValue]; params: {'id': ParamValue} }
    'daily.index': { paramsTuple?: []; params?: {} }
    'daily.today': { paramsTuple?: []; params?: {} }
    'daily.show': { paramsTuple: [ParamValue]; params: {'date': ParamValue} }
    'logs.index': { paramsTuple?: []; params?: {} }
    'logs.show': { paramsTuple: [ParamValue]; params: {'id': ParamValue} }
    'system.health': { paramsTuple?: []; params?: {} }
    'system.status': { paramsTuple?: []; params?: {} }
    'sp_500_settings.show': { paramsTuple?: []; params?: {} }
    'sp_500_trades.index': { paramsTuple?: []; params?: {} }
    'sp_500_trades.open': { paramsTuple?: []; params?: {} }
    'sp_500_trades.stats': { paramsTuple?: []; params?: {} }
    'sp_500_logs.index': { paramsTuple?: []; params?: {} }
  }
  HEAD: {
    'me.show': { paramsTuple?: []; params?: {} }
    'pairs.index': { paramsTuple?: []; params?: {} }
    'broker.show': { paramsTuple?: []; params?: {} }
    'trading_settings.show': { paramsTuple?: []; params?: {} }
    'trades.index': { paramsTuple?: []; params?: {} }
    'trades.open': { paramsTuple?: []; params?: {} }
    'trades.stats': { paramsTuple?: []; params?: {} }
    'trades.show': { paramsTuple: [ParamValue]; params: {'id': ParamValue} }
    'daily.index': { paramsTuple?: []; params?: {} }
    'daily.today': { paramsTuple?: []; params?: {} }
    'daily.show': { paramsTuple: [ParamValue]; params: {'date': ParamValue} }
    'logs.index': { paramsTuple?: []; params?: {} }
    'logs.show': { paramsTuple: [ParamValue]; params: {'id': ParamValue} }
    'system.health': { paramsTuple?: []; params?: {} }
    'system.status': { paramsTuple?: []; params?: {} }
    'sp_500_settings.show': { paramsTuple?: []; params?: {} }
    'sp_500_trades.index': { paramsTuple?: []; params?: {} }
    'sp_500_trades.open': { paramsTuple?: []; params?: {} }
    'sp_500_trades.stats': { paramsTuple?: []; params?: {} }
    'sp_500_logs.index': { paramsTuple?: []; params?: {} }
  }
  POST: {
    'broker.upsert': { paramsTuple?: []; params?: {} }
    'broker.test_connection': { paramsTuple?: []; params?: {} }
    'trading_settings.reset': { paramsTuple?: []; params?: {} }
    'system.kill_switch': { paramsTuple?: []; params?: {} }
  }
  DELETE: {
    'broker.destroy': { paramsTuple?: []; params?: {} }
  }
  PUT: {
    'trading_settings.update': { paramsTuple?: []; params?: {} }
    'sp_500_settings.upsert': { paramsTuple?: []; params?: {} }
  }
}
declare module '@adonisjs/core/types/http' {
  export interface RoutesList extends ScannedRoutes {}
}