import { defineBoot } from '#q-app'
import { Amplify } from 'aws-amplify'
import outputs from '../../amplify_outputs.json'

window.global = window.global || window
window.process = window.process || ({ env: {} } as unknown as NodeJS.Process)

export default defineBoot(() => {
  Amplify.configure(outputs as Parameters<typeof Amplify.configure>[0])
})
