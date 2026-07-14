import { defineStore } from 'pinia'
import { signOut, fetchAuthSession, getCurrentUser } from 'aws-amplify/auth'
import { api } from '@/services/api'

interface MeResponse {
  data: {
    id: string
    email: string
    fullName: string | null
    accountCurrency: string
    isActive: boolean
    hasBroker: boolean
    hasSettings: boolean
    brokerName: string | null
    accountType: string | null
  }
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    email: '',
    userId: '',
    fullName: '',
    hasBroker: false,
    hasSettings: false,
    brokerName: null as string | null,
    accountType: null as string | null,
    profileLoaded: false,
  }),

  getters: {
    isAuthenticated: (state) => !!state.userId,
    initials: (state) => {
      if (state.fullName) {
        const parts = state.fullName.split(' ')
        return parts.length > 1
          ? `${parts[0]?.[0] ?? ''}${parts[1]?.[0] ?? ''}`.toUpperCase()
          : state.fullName.slice(0, 2).toUpperCase()
      }
      return state.email ? state.email.slice(0, 2).toUpperCase() : '??'
    },
  },

  actions: {
    async currentSession() {
      try {
        const session = await fetchAuthSession()
        const tokens = session.tokens

        if (tokens?.idToken) {
          const { userId, signInDetails } = await getCurrentUser()
          const payload = tokens.idToken.payload

          this.userId = userId
          this.email = signInDetails?.loginId || (typeof payload['email'] === 'string' ? payload['email'] : '')
          this.fullName = typeof payload['name'] === 'string' ? payload['name'] : ''

          await this.loadProfile()
        }
      } catch {
        this.reset()
      }
    },

    async loadProfile() {
      try {
        const res = await api.get<MeResponse>('/me')
        if (res.data) {
          this.fullName = res.data.fullName || this.fullName
          this.hasBroker = res.data.hasBroker
          this.hasSettings = res.data.hasSettings
          this.brokerName = res.data.brokerName
          this.accountType = res.data.accountType
          this.profileLoaded = true
        }
      } catch {
        // Backend not available
      }
    },

    async logOut() {
      await signOut({ global: true })
      this.reset()
    },

    reset() {
      this.email = ''
      this.userId = ''
      this.fullName = ''
      this.hasBroker = false
      this.hasSettings = false
      this.brokerName = null
      this.accountType = null
      this.profileLoaded = false
    },
  },
})
