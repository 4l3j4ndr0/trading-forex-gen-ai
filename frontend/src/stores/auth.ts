import { defineStore } from 'pinia'
import { signOut, fetchAuthSession, getCurrentUser } from 'aws-amplify/auth'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    email: '' as string,
    userId: '' as string,
    fullName: '' as string,
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
          this.email = signInDetails?.loginId || String(payload.email ?? '')
          this.fullName = String(payload.name ?? '')
        }
      } catch {
        // No session active
        this.reset()
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
    },
  },
})
