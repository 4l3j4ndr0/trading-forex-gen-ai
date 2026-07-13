import { defineStore } from 'pinia'
import { signOut, fetchAuthSession, getCurrentUser } from 'aws-amplify/auth'
import { api } from '@/services/api'

interface UserSettings {
  maxRiskPerTrade: number
  maxDailyDrawdown: number
  maxWeeklyDrawdown: number
  maxOpenPositions: number
  preferredPairs: string[]
  preferredSessions: string[]
  minSignalScore: number
  minSignalClass: string
  alertChannels: Record<string, boolean>
  timezone: string
}

interface MeResponse {
  data: {
    id: string
    email: string
    fullName: string | null
    avatarUrl: string | null
    accountCurrency: string
    accountBalance: number
    isActive: boolean
    lastLoginAt: string | null
    createdAt: string
    settings: UserSettings | null
  }
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    email: '',
    userId: '',
    fullName: '',
    accountBalance: 0,
    accountCurrency: 'USD',
    settings: null as UserSettings | null,
    profileLoaded: false,
  }),

  getters: {
    isAuthenticated: (state) => !!state.userId,
    initials: (state) => {
      if (state.fullName) {
        const parts = state.fullName.split(' ')
        if (parts.length > 1) {
          return `${parts[0]?.[0] ?? ''}${parts[1]?.[0] ?? ''}`.toUpperCase()
        }
        return state.fullName.slice(0, 2).toUpperCase()
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
          const email = payload['email']
          const name = payload['name']
          this.email = signInDetails?.loginId || (typeof email === 'string' ? email : '')
          this.fullName = typeof name === 'string' ? name : ''

          // Cargar perfil del backend (lazy creation del usuario)
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
          this.accountBalance = res.data.accountBalance
          this.accountCurrency = res.data.accountCurrency
          this.settings = res.data.settings
          this.profileLoaded = true
        }
      } catch {
        // Backend no disponible — seguir con datos de Cognito
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
      this.accountBalance = 0
      this.accountCurrency = 'USD'
      this.settings = null
      this.profileLoaded = false
    },
  },
})
