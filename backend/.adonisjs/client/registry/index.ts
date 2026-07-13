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
  'me.update_settings': {
    methods: ["PUT"],
    pattern: '/api/v1/me/settings',
    tokens: [{"old":"/api/v1/me/settings","type":0,"val":"api","end":""},{"old":"/api/v1/me/settings","type":0,"val":"v1","end":""},{"old":"/api/v1/me/settings","type":0,"val":"me","end":""},{"old":"/api/v1/me/settings","type":0,"val":"settings","end":""}],
    types: placeholder as Registry['me.update_settings']['types'],
  },
  'analysis.run': {
    methods: ["POST"],
    pattern: '/api/v1/analysis/run',
    tokens: [{"old":"/api/v1/analysis/run","type":0,"val":"api","end":""},{"old":"/api/v1/analysis/run","type":0,"val":"v1","end":""},{"old":"/api/v1/analysis/run","type":0,"val":"analysis","end":""},{"old":"/api/v1/analysis/run","type":0,"val":"run","end":""}],
    types: placeholder as Registry['analysis.run']['types'],
  },
  'analysis.analyses': {
    methods: ["GET","HEAD"],
    pattern: '/api/v1/analyses',
    tokens: [{"old":"/api/v1/analyses","type":0,"val":"api","end":""},{"old":"/api/v1/analyses","type":0,"val":"v1","end":""},{"old":"/api/v1/analyses","type":0,"val":"analyses","end":""}],
    types: placeholder as Registry['analysis.analyses']['types'],
  },
  'analysis.signals': {
    methods: ["GET","HEAD"],
    pattern: '/api/v1/signals',
    tokens: [{"old":"/api/v1/signals","type":0,"val":"api","end":""},{"old":"/api/v1/signals","type":0,"val":"v1","end":""},{"old":"/api/v1/signals","type":0,"val":"signals","end":""}],
    types: placeholder as Registry['analysis.signals']['types'],
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
