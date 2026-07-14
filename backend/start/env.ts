/*
|--------------------------------------------------------------------------
| Environment variables service
|--------------------------------------------------------------------------
*/

import { Env } from '@adonisjs/core/env'

export default await Env.create(new URL('../', import.meta.url), {
  // Node
  NODE_ENV: Env.schema.enum(['development', 'production', 'test'] as const),
  PORT: Env.schema.number(),
  HOST: Env.schema.string({ format: 'host' }),
  LOG_LEVEL: Env.schema.string(),
  TZ: Env.schema.string.optional(),

  // App
  APP_KEY: Env.schema.secret(),

  // Session
  SESSION_DRIVER: Env.schema.enum(['cookie', 'memory'] as const),

  // Database (PostgreSQL)
  DB_HOST: Env.schema.string({ format: 'host' }),
  DB_PORT: Env.schema.number(),
  DB_USER: Env.schema.string(),
  DB_PASSWORD: Env.schema.string.optional(),
  DB_DATABASE: Env.schema.string(),

  // AWS Cognito
  COGNITO_USER_POOL_ID: Env.schema.string(),
  COGNITO_CLIENT_ID: Env.schema.string(),

  // AWS
  AWS_REGION: Env.schema.string.optional(),

  // MT5 Bridge
  MT5_BRIDGE_URL: Env.schema.string(),
  MT5_BRIDGE_API_KEY: Env.schema.string(),

  // Frontend URL (CORS)
  FRONTEND_URL: Env.schema.string({ format: 'url', tld: false }),
})
