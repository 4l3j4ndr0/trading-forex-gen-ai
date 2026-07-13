/* eslint-disable prettier/prettier */
import type { routes } from './index.ts'

export interface ApiDefinition {
  me: {
    show: typeof routes['me.show']
    updateSettings: typeof routes['me.update_settings']
  }
  analysis: {
    run: typeof routes['analysis.run']
    analyses: typeof routes['analysis.analyses']
    signals: typeof routes['analysis.signals']
  }
}
