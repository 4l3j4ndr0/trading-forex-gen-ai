/* eslint-disable prettier/prettier */
import type { AdonisEndpoint } from '@tuyau/core/types'
import type { Registry } from './schema.d.ts'
import type { ApiDefinition } from './tree.d.ts'

const placeholder: any = {}

const routes = {
  'me.show': {
    methods: ["GET","HEAD"],
    pattern: '/api/v1/me',
    tokens: [{"old":"/api/v1/me","type":0,"val":"api","end":""},{"old":"/api/v1/me","type":0,"val":"v1","end":""},{"old":"/api/v1/me","type":0,"val":"me","end":""}],
    types: placeholder as Registry['me.show']['types'],
  },
  'broker.show': {
    methods: ["GET","HEAD"],
    pattern: '/api/v1/broker',
    tokens: [{"old":"/api/v1/broker","type":0,"val":"api","end":""},{"old":"/api/v1/broker","type":0,"val":"v1","end":""},{"old":"/api/v1/broker","type":0,"val":"broker","end":""}],
    types: placeholder as Registry['broker.show']['types'],
  },
  'broker.upsert': {
    methods: ["POST"],
    pattern: '/api/v1/broker',
    tokens: [{"old":"/api/v1/broker","type":0,"val":"api","end":""},{"old":"/api/v1/broker","type":0,"val":"v1","end":""},{"old":"/api/v1/broker","type":0,"val":"broker","end":""}],
    types: placeholder as Registry['broker.upsert']['types'],
  },
  'broker.test_connection': {
    methods: ["POST"],
    pattern: '/api/v1/broker/test',
    tokens: [{"old":"/api/v1/broker/test","type":0,"val":"api","end":""},{"old":"/api/v1/broker/test","type":0,"val":"v1","end":""},{"old":"/api/v1/broker/test","type":0,"val":"broker","end":""},{"old":"/api/v1/broker/test","type":0,"val":"test","end":""}],
    types: placeholder as Registry['broker.test_connection']['types'],
  },
  'broker.destroy': {
    methods: ["DELETE"],
    pattern: '/api/v1/broker',
    tokens: [{"old":"/api/v1/broker","type":0,"val":"api","end":""},{"old":"/api/v1/broker","type":0,"val":"v1","end":""},{"old":"/api/v1/broker","type":0,"val":"broker","end":""}],
    types: placeholder as Registry['broker.destroy']['types'],
  },
  'trading_settings.show': {
    methods: ["GET","HEAD"],
    pattern: '/api/v1/settings/trading',
    tokens: [{"old":"/api/v1/settings/trading","type":0,"val":"api","end":""},{"old":"/api/v1/settings/trading","type":0,"val":"v1","end":""},{"old":"/api/v1/settings/trading","type":0,"val":"settings","end":""},{"old":"/api/v1/settings/trading","type":0,"val":"trading","end":""}],
    types: placeholder as Registry['trading_settings.show']['types'],
  },
  'trading_settings.update': {
    methods: ["PUT"],
    pattern: '/api/v1/settings/trading',
    tokens: [{"old":"/api/v1/settings/trading","type":0,"val":"api","end":""},{"old":"/api/v1/settings/trading","type":0,"val":"v1","end":""},{"old":"/api/v1/settings/trading","type":0,"val":"settings","end":""},{"old":"/api/v1/settings/trading","type":0,"val":"trading","end":""}],
    types: placeholder as Registry['trading_settings.update']['types'],
  },
  'trading_settings.reset': {
    methods: ["POST"],
    pattern: '/api/v1/settings/trading/reset',
    tokens: [{"old":"/api/v1/settings/trading/reset","type":0,"val":"api","end":""},{"old":"/api/v1/settings/trading/reset","type":0,"val":"v1","end":""},{"old":"/api/v1/settings/trading/reset","type":0,"val":"settings","end":""},{"old":"/api/v1/settings/trading/reset","type":0,"val":"trading","end":""},{"old":"/api/v1/settings/trading/reset","type":0,"val":"reset","end":""}],
    types: placeholder as Registry['trading_settings.reset']['types'],
  },
  'trades.index': {
    methods: ["GET","HEAD"],
    pattern: '/api/v1/trades',
    tokens: [{"old":"/api/v1/trades","type":0,"val":"api","end":""},{"old":"/api/v1/trades","type":0,"val":"v1","end":""},{"old":"/api/v1/trades","type":0,"val":"trades","end":""}],
    types: placeholder as Registry['trades.index']['types'],
  },
  'trades.open': {
    methods: ["GET","HEAD"],
    pattern: '/api/v1/trades/open',
    tokens: [{"old":"/api/v1/trades/open","type":0,"val":"api","end":""},{"old":"/api/v1/trades/open","type":0,"val":"v1","end":""},{"old":"/api/v1/trades/open","type":0,"val":"trades","end":""},{"old":"/api/v1/trades/open","type":0,"val":"open","end":""}],
    types: placeholder as Registry['trades.open']['types'],
  },
  'trades.stats': {
    methods: ["GET","HEAD"],
    pattern: '/api/v1/trades/stats',
    tokens: [{"old":"/api/v1/trades/stats","type":0,"val":"api","end":""},{"old":"/api/v1/trades/stats","type":0,"val":"v1","end":""},{"old":"/api/v1/trades/stats","type":0,"val":"trades","end":""},{"old":"/api/v1/trades/stats","type":0,"val":"stats","end":""}],
    types: placeholder as Registry['trades.stats']['types'],
  },
  'trades.show': {
    methods: ["GET","HEAD"],
    pattern: '/api/v1/trades/:id',
    tokens: [{"old":"/api/v1/trades/:id","type":0,"val":"api","end":""},{"old":"/api/v1/trades/:id","type":0,"val":"v1","end":""},{"old":"/api/v1/trades/:id","type":0,"val":"trades","end":""},{"old":"/api/v1/trades/:id","type":1,"val":"id","end":""}],
    types: placeholder as Registry['trades.show']['types'],
  },
  'daily.index': {
    methods: ["GET","HEAD"],
    pattern: '/api/v1/daily',
    tokens: [{"old":"/api/v1/daily","type":0,"val":"api","end":""},{"old":"/api/v1/daily","type":0,"val":"v1","end":""},{"old":"/api/v1/daily","type":0,"val":"daily","end":""}],
    types: placeholder as Registry['daily.index']['types'],
  },
  'daily.today': {
    methods: ["GET","HEAD"],
    pattern: '/api/v1/daily/today',
    tokens: [{"old":"/api/v1/daily/today","type":0,"val":"api","end":""},{"old":"/api/v1/daily/today","type":0,"val":"v1","end":""},{"old":"/api/v1/daily/today","type":0,"val":"daily","end":""},{"old":"/api/v1/daily/today","type":0,"val":"today","end":""}],
    types: placeholder as Registry['daily.today']['types'],
  },
  'daily.show': {
    methods: ["GET","HEAD"],
    pattern: '/api/v1/daily/:date',
    tokens: [{"old":"/api/v1/daily/:date","type":0,"val":"api","end":""},{"old":"/api/v1/daily/:date","type":0,"val":"v1","end":""},{"old":"/api/v1/daily/:date","type":0,"val":"daily","end":""},{"old":"/api/v1/daily/:date","type":1,"val":"date","end":""}],
    types: placeholder as Registry['daily.show']['types'],
  },
  'logs.index': {
    methods: ["GET","HEAD"],
    pattern: '/api/v1/logs/hourly',
    tokens: [{"old":"/api/v1/logs/hourly","type":0,"val":"api","end":""},{"old":"/api/v1/logs/hourly","type":0,"val":"v1","end":""},{"old":"/api/v1/logs/hourly","type":0,"val":"logs","end":""},{"old":"/api/v1/logs/hourly","type":0,"val":"hourly","end":""}],
    types: placeholder as Registry['logs.index']['types'],
  },
  'logs.show': {
    methods: ["GET","HEAD"],
    pattern: '/api/v1/logs/hourly/:id',
    tokens: [{"old":"/api/v1/logs/hourly/:id","type":0,"val":"api","end":""},{"old":"/api/v1/logs/hourly/:id","type":0,"val":"v1","end":""},{"old":"/api/v1/logs/hourly/:id","type":0,"val":"logs","end":""},{"old":"/api/v1/logs/hourly/:id","type":0,"val":"hourly","end":""},{"old":"/api/v1/logs/hourly/:id","type":1,"val":"id","end":""}],
    types: placeholder as Registry['logs.show']['types'],
  },
  'system.health': {
    methods: ["GET","HEAD"],
    pattern: '/api/v1/system/health',
    tokens: [{"old":"/api/v1/system/health","type":0,"val":"api","end":""},{"old":"/api/v1/system/health","type":0,"val":"v1","end":""},{"old":"/api/v1/system/health","type":0,"val":"system","end":""},{"old":"/api/v1/system/health","type":0,"val":"health","end":""}],
    types: placeholder as Registry['system.health']['types'],
  },
  'system.status': {
    methods: ["GET","HEAD"],
    pattern: '/api/v1/system/status',
    tokens: [{"old":"/api/v1/system/status","type":0,"val":"api","end":""},{"old":"/api/v1/system/status","type":0,"val":"v1","end":""},{"old":"/api/v1/system/status","type":0,"val":"system","end":""},{"old":"/api/v1/system/status","type":0,"val":"status","end":""}],
    types: placeholder as Registry['system.status']['types'],
  },
  'system.kill_switch': {
    methods: ["POST"],
    pattern: '/api/v1/system/kill-switch',
    tokens: [{"old":"/api/v1/system/kill-switch","type":0,"val":"api","end":""},{"old":"/api/v1/system/kill-switch","type":0,"val":"v1","end":""},{"old":"/api/v1/system/kill-switch","type":0,"val":"system","end":""},{"old":"/api/v1/system/kill-switch","type":0,"val":"kill-switch","end":""}],
    types: placeholder as Registry['system.kill_switch']['types'],
  },
} as const satisfies Record<string, AdonisEndpoint>

export { routes }

export const registry = {
  routes,
  $tree: {} as ApiDefinition,
}

declare module '@tuyau/core/types' {
  export interface UserRegistry {
    routes: typeof routes
    $tree: ApiDefinition
  }
}
