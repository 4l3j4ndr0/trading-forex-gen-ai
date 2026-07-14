import { BaseSchema } from '@adonisjs/lucid/schema'

export default class extends BaseSchema {
  protected tableName = 'pairs'

  async up() {
    this.schema.createTable(this.tableName, (table) => {
      table.increments('id').primary()
      table.string('symbol', 10).notNullable().unique()
      table.string('base_currency', 3).notNullable()
      table.string('quote_currency', 3).notNullable()
      table.decimal('pip_size', 10, 6).notNullable()
      table.decimal('pip_value_usd', 10, 4).notNullable().defaultTo(10)
      table.decimal('spread_avg', 5, 2).notNullable().defaultTo(1.5)
      table.string('category', 10).notNullable().defaultTo('major')
      table.jsonb('sessions').notNullable().defaultTo('["london","new_york"]')
      table.boolean('is_active').notNullable().defaultTo(true)
      table.timestamp('created_at').notNullable()
    })

    // Seed initial pairs
    this.defer(async (db) => {
      await db.table('pairs').multiInsert([
        { symbol: 'EURUSD', base_currency: 'EUR', quote_currency: 'USD', pip_size: 0.0001, pip_value_usd: 10, spread_avg: 1.6, category: 'major', sessions: JSON.stringify(['london', 'new_york']), is_active: true, created_at: new Date() },
        { symbol: 'GBPUSD', base_currency: 'GBP', quote_currency: 'USD', pip_size: 0.0001, pip_value_usd: 10, spread_avg: 2.1, category: 'major', sessions: JSON.stringify(['london', 'new_york']), is_active: true, created_at: new Date() },
        { symbol: 'USDJPY', base_currency: 'USD', quote_currency: 'JPY', pip_size: 0.01, pip_value_usd: 6.7, spread_avg: 1.8, category: 'major', sessions: JSON.stringify(['tokyo', 'new_york']), is_active: true, created_at: new Date() },
        { symbol: 'AUDUSD', base_currency: 'AUD', quote_currency: 'USD', pip_size: 0.0001, pip_value_usd: 10, spread_avg: 1.8, category: 'major', sessions: JSON.stringify(['tokyo', 'london']), is_active: true, created_at: new Date() },
        { symbol: 'USDCAD', base_currency: 'USD', quote_currency: 'CAD', pip_size: 0.0001, pip_value_usd: 7.5, spread_avg: 2.2, category: 'major', sessions: JSON.stringify(['new_york']), is_active: true, created_at: new Date() },
        { symbol: 'EURGBP', base_currency: 'EUR', quote_currency: 'GBP', pip_size: 0.0001, pip_value_usd: 12.5, spread_avg: 2.0, category: 'cross', sessions: JSON.stringify(['london']), is_active: true, created_at: new Date() },
      ])
    })
  }

  async down() {
    this.schema.dropTable(this.tableName)
  }
}
