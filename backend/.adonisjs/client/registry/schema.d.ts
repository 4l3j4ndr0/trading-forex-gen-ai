/* eslint-disable prettier/prettier */
/// <reference path="../manifest.d.ts" />

import type { ExtractBody, ExtractErrorResponse, ExtractQuery, ExtractQueryForGet, ExtractResponse } from '@tuyau/core/types'
import type { InferInput, SimpleError } from '@vinejs/vine/types'

export type ParamValue = string | number | bigint | boolean

export interface Registry {
  'me.show': {
    methods: ["GET","HEAD"]
    pattern: '/api/v1/me'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: ExtractResponse<Awaited<ReturnType<import('#controllers/me_controller').default['show']>>>
      errorResponse: ExtractErrorResponse<Awaited<ReturnType<import('#controllers/me_controller').default['show']>>>
    }
  }
  'broker.show': {
    methods: ["GET","HEAD"]
    pattern: '/api/v1/broker'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: ExtractResponse<Awaited<ReturnType<import('#controllers/broker_controller').default['show']>>>
      errorResponse: ExtractErrorResponse<Awaited<ReturnType<import('#controllers/broker_controller').default['show']>>>
    }
  }
  'broker.upsert': {
    methods: ["POST"]
    pattern: '/api/v1/broker'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: ExtractResponse<Awaited<ReturnType<import('#controllers/broker_controller').default['upsert']>>>
      errorResponse: ExtractErrorResponse<Awaited<ReturnType<import('#controllers/broker_controller').default['upsert']>>>
    }
  }
  'broker.test_connection': {
    methods: ["POST"]
    pattern: '/api/v1/broker/test'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: ExtractResponse<Awaited<ReturnType<import('#controllers/broker_controller').default['testConnection']>>>
      errorResponse: ExtractErrorResponse<Awaited<ReturnType<import('#controllers/broker_controller').default['testConnection']>>>
    }
  }
  'broker.destroy': {
    methods: ["DELETE"]
    pattern: '/api/v1/broker'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: ExtractResponse<Awaited<ReturnType<import('#controllers/broker_controller').default['destroy']>>>
      errorResponse: ExtractErrorResponse<Awaited<ReturnType<import('#controllers/broker_controller').default['destroy']>>>
    }
  }
  'trading_settings.show': {
    methods: ["GET","HEAD"]
    pattern: '/api/v1/settings/trading'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: ExtractResponse<Awaited<ReturnType<import('#controllers/trading_settings_controller').default['show']>>>
      errorResponse: ExtractErrorResponse<Awaited<ReturnType<import('#controllers/trading_settings_controller').default['show']>>>
    }
  }
  'trading_settings.update': {
    methods: ["PUT"]
    pattern: '/api/v1/settings/trading'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: ExtractResponse<Awaited<ReturnType<import('#controllers/trading_settings_controller').default['update']>>>
      errorResponse: ExtractErrorResponse<Awaited<ReturnType<import('#controllers/trading_settings_controller').default['update']>>>
    }
  }
  'trading_settings.reset': {
    methods: ["POST"]
    pattern: '/api/v1/settings/trading/reset'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: ExtractResponse<Awaited<ReturnType<import('#controllers/trading_settings_controller').default['reset']>>>
      errorResponse: ExtractErrorResponse<Awaited<ReturnType<import('#controllers/trading_settings_controller').default['reset']>>>
    }
  }
  'trades.index': {
    methods: ["GET","HEAD"]
    pattern: '/api/v1/trades'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: ExtractResponse<Awaited<ReturnType<import('#controllers/trades_controller').default['index']>>>
      errorResponse: ExtractErrorResponse<Awaited<ReturnType<import('#controllers/trades_controller').default['index']>>>
    }
  }
  'trades.open': {
    methods: ["GET","HEAD"]
    pattern: '/api/v1/trades/open'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: ExtractResponse<Awaited<ReturnType<import('#controllers/trades_controller').default['open']>>>
      errorResponse: ExtractErrorResponse<Awaited<ReturnType<import('#controllers/trades_controller').default['open']>>>
    }
  }
  'trades.stats': {
    methods: ["GET","HEAD"]
    pattern: '/api/v1/trades/stats'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: ExtractResponse<Awaited<ReturnType<import('#controllers/trades_controller').default['stats']>>>
      errorResponse: ExtractErrorResponse<Awaited<ReturnType<import('#controllers/trades_controller').default['stats']>>>
    }
  }
  'trades.show': {
    methods: ["GET","HEAD"]
    pattern: '/api/v1/trades/:id'
    types: {
      body: {}
      paramsTuple: [ParamValue]
      params: { id: ParamValue }
      query: {}
      response: ExtractResponse<Awaited<ReturnType<import('#controllers/trades_controller').default['show']>>>
      errorResponse: ExtractErrorResponse<Awaited<ReturnType<import('#controllers/trades_controller').default['show']>>>
    }
  }
  'daily.index': {
    methods: ["GET","HEAD"]
    pattern: '/api/v1/daily'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: ExtractResponse<Awaited<ReturnType<import('#controllers/daily_controller').default['index']>>>
      errorResponse: ExtractErrorResponse<Awaited<ReturnType<import('#controllers/daily_controller').default['index']>>>
    }
  }
  'daily.today': {
    methods: ["GET","HEAD"]
    pattern: '/api/v1/daily/today'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: ExtractResponse<Awaited<ReturnType<import('#controllers/daily_controller').default['today']>>>
      errorResponse: ExtractErrorResponse<Awaited<ReturnType<import('#controllers/daily_controller').default['today']>>>
    }
  }
  'daily.show': {
    methods: ["GET","HEAD"]
    pattern: '/api/v1/daily/:date'
    types: {
      body: {}
      paramsTuple: [ParamValue]
      params: { date: ParamValue }
      query: {}
      response: ExtractResponse<Awaited<ReturnType<import('#controllers/daily_controller').default['show']>>>
      errorResponse: ExtractErrorResponse<Awaited<ReturnType<import('#controllers/daily_controller').default['show']>>>
    }
  }
  'logs.index': {
    methods: ["GET","HEAD"]
    pattern: '/api/v1/logs/hourly'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: ExtractResponse<Awaited<ReturnType<import('#controllers/logs_controller').default['index']>>>
      errorResponse: ExtractErrorResponse<Awaited<ReturnType<import('#controllers/logs_controller').default['index']>>>
    }
  }
  'logs.show': {
    methods: ["GET","HEAD"]
    pattern: '/api/v1/logs/hourly/:id'
    types: {
      body: {}
      paramsTuple: [ParamValue]
      params: { id: ParamValue }
      query: {}
      response: ExtractResponse<Awaited<ReturnType<import('#controllers/logs_controller').default['show']>>>
      errorResponse: ExtractErrorResponse<Awaited<ReturnType<import('#controllers/logs_controller').default['show']>>>
    }
  }
  'system.health': {
    methods: ["GET","HEAD"]
    pattern: '/api/v1/system/health'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: ExtractResponse<Awaited<ReturnType<import('#controllers/system_controller').default['health']>>>
      errorResponse: ExtractErrorResponse<Awaited<ReturnType<import('#controllers/system_controller').default['health']>>>
    }
  }
  'system.status': {
    methods: ["GET","HEAD"]
    pattern: '/api/v1/system/status'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: ExtractResponse<Awaited<ReturnType<import('#controllers/system_controller').default['status']>>>
      errorResponse: ExtractErrorResponse<Awaited<ReturnType<import('#controllers/system_controller').default['status']>>>
    }
  }
  'system.kill_switch': {
    methods: ["POST"]
    pattern: '/api/v1/system/kill-switch'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: ExtractResponse<Awaited<ReturnType<import('#controllers/system_controller').default['killSwitch']>>>
      errorResponse: ExtractErrorResponse<Awaited<ReturnType<import('#controllers/system_controller').default['killSwitch']>>>
    }
  }
}
