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
