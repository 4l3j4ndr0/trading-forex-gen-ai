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

    // Buscar o crear usuario (lazy creation)
    let user = await User.findBy('cognito_sub', sub)

    if (!user) {
      user = await db.transaction(async (trx) => {
        const newUser = new User()
        newUser.cognitoSub = sub
        newUser.email = email
        newUser.fullName = typeof payload.name === 'string' ? payload.name : null
        newUser.accountCurrency = 'USD'
        newUser.isActive = true
        newUser.useTransaction(trx)
        await newUser.save()

        // Crear trading_settings con defaults
        await trx.insertQuery().table('trading_settings').insert({
          user_id: newUser.id,
          max_risk_per_trade_pct: 1.0,
          max_daily_loss_pct: 1.0,
          max_drawdown_pct: 5.0,
          max_consecutive_losses: 5,
          min_rr_ratio: 1.5,
          default_lot_size: 0.05,
          max_lot_size: 0.50,
          max_open_positions: 3,
          trading_start_utc: '07:00',
          trading_end_utc: '21:00',
          news_buffer_minutes: 30,
          max_trade_duration_minutes: 240,
          daily_target_pct: 1.0,
          reduce_lot_at_pct: 80,
          min_adx_entry: 25,
          min_alignment_score: 2,
          max_spread_pips: 3.0,
          allowed_pairs: JSON.stringify(['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'EURGBP']),
          kill_switch: false,
          auto_trading_enabled: true,
          created_at: new Date(),
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
