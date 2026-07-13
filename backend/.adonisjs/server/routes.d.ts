import '@adonisjs/core/types/http'

type ParamValue = string | number | bigint | boolean

export type ScannedRoutes = {
  ALL: {
    'me.show': { paramsTuple?: []; params?: {} }
    'me.update_settings': { paramsTuple?: []; params?: {} }
    'analysis.run': { paramsTuple?: []; params?: {} }
    'analysis.analyses': { paramsTuple?: []; params?: {} }
    'analysis.signals': { paramsTuple?: []; params?: {} }
  }
  GET: {
    'me.show': { paramsTuple?: []; params?: {} }
    'analysis.analyses': { paramsTuple?: []; params?: {} }
    'analysis.signals': { paramsTuple?: []; params?: {} }
  }
  HEAD: {
    'me.show': { paramsTuple?: []; params?: {} }
    'analysis.analyses': { paramsTuple?: []; params?: {} }
    'analysis.signals': { paramsTuple?: []; params?: {} }
  }
  PUT: {
    'me.update_settings': { paramsTuple?: []; params?: {} }
  }
  POST: {
    'analysis.run': { paramsTuple?: []; params?: {} }
  }
}
declare module '@adonisjs/core/types/http' {
  export interface RoutesList extends ScannedRoutes {}
}