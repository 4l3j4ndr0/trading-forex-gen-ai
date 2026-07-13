import type { HttpContext } from '@adonisjs/core/http'
import type { NextFn } from '@adonisjs/core/types/http'
import { CognitoJwtVerifier } from 'aws-jwt-verify'
import env from '#start/env'
import User from '#models/user'
import db from '@adonisjs/lucid/services/db'

const verifier = CognitoJwtVerifier.create({
  userPoolId: env.get('COGNITO_USER_POOL_ID'),
  tokenUse: 'id',
  clientId: env.get('COGNITO_CLIENT_ID'),
})

export interface CognitoUser {
  sub: string
  email: string
  user: User
}

declare module '@adonisjs/core/http' {
  interface HttpContext {
    cognito: CognitoUser
  }
}

export default class CognitoMiddleware {
  async handle(ctx: HttpContext, next: NextFn) {
    const authHeader = ctx.request.header('authorization')
    if (!authHeader?.startsWith('Bearer ')) {
      return ctx.response.unauthorized({ message: 'Token no proporcionado' })
    }

    const token = authHeader.slice(7)

    let payload: Awaited<ReturnType<typeof verifier.verify>>
    try {
      payload = await verifier.verify(token)
    } catch {
      return ctx.response.unauthorized({ message: 'Token inválido o expirado' })
    }

    const sub = payload.sub
    const email = typeof payload.email === 'string' ? payload.email : ''

    // Buscar o crear usuario (Opción A: lazy creation)
    let user = await User.findBy('cognito_sub', sub)

    if (!user) {
      user = await db.transaction(async (trx) => {
        const newUser = new User()
        newUser.cognitoSub = sub
        newUser.email = email
        newUser.fullName = typeof payload.name === 'string' ? payload.name : null
        newUser.accountCurrency = 'USD'
        newUser.accountBalance = 0
        newUser.isActive = true
        newUser.useTransaction(trx)
        await newUser.save()

        // Crear settings con valores por defecto
        await trx.insertQuery().table('user_settings').insert({
          user_id: newUser.id,
          max_risk_per_trade: 1.0,
          max_daily_drawdown: 6.0,
          max_weekly_drawdown: 15.0,
          max_open_positions: 3,
          preferred_pairs: JSON.stringify(['EUR/USD', 'GBP/USD', 'USD/JPY']),
          preferred_sessions: JSON.stringify(['london', 'new_york']),
          min_signal_score: 6,
          min_signal_class: 'B',
          alert_channels: JSON.stringify({ websocket: true, email: false }),
          timezone: 'America/Bogota',
          created_at: new Date(),
          updated_at: new Date(),
        })

        return newUser
      })
    } else {
      // Actualizar last_login_at
      user.lastLoginAt = (await import('luxon')).DateTime.now()
      await user.save()
    }

    ctx.cognito = { sub, email, user }

    return next()
  }
}
