import { BaseSchema } from '@adonisjs/lucid/schema'

export default class extends BaseSchema {
  protected tableName = 'trading_settings'

  async up() {
    this.schema.createTable(this.tableName, (table) => {
      table.uuid('id').primary().defaultTo(this.raw('uuid_generate_v4()'))
      table.uuid('user_id').notNullable().references('id').inTable('users').onDelete('CASCADE')

      // Risk Management
      table.decimal('max_risk_per_trade_pct', 4, 2).notNullable().defaultTo(1.0)
      table.decimal('max_daily_loss_pct', 4, 2).notNullable().defaultTo(1.0)
      table.decimal('max_drawdown_pct', 4, 2).notNullable().defaultTo(5.0)
      table.integer('max_consecutive_losses').notNullable().defaultTo(5)
      table.decimal('min_rr_ratio', 4, 2).notNullable().defaultTo(1.5)

      // Position Sizing
      table.decimal('default_lot_size', 6, 2).notNullable().defaultTo(0.05)
      table.decimal('max_lot_size', 6, 2).notNullable().defaultTo(0.50)
      table.integer('max_open_positions').notNullable().defaultTo(3)

      // Session & Timing
      table.string('trading_start_utc', 5).notNullable().defaultTo('07:00')
      table.string('trading_end_utc', 5).notNullable().defaultTo('21:00')
      table.integer('news_buffer_minutes').notNullable().defaultTo(30)
      table.integer('max_trade_duration_minutes').notNullable().defaultTo(240)

      // Target
      table.decimal('daily_target_pct', 4, 2).notNullable().defaultTo(1.0)
      table.integer('reduce_lot_at_pct').notNullable().defaultTo(80)

      // Analysis Filters
      table.integer('min_adx_entry').notNullable().defaultTo(25)
      table.integer('min_alignment_score').notNullable().defaultTo(2)
      table.decimal('max_spread_pips', 4, 1).notNullable().defaultTo(3.0)

      // Pairs
      table.jsonb('allowed_pairs').notNullable().defaultTo('["EURUSD","GBPUSD","USDJPY","AUDUSD","USDCAD","EURGBP"]')

      // System
      table.boolean('kill_switch').notNullable().defaultTo(false)
      table.boolean('auto_trading_enabled').notNullable().defaultTo(true)

      table.timestamp('created_at').notNullable()
      table.timestamp('updated_at').nullable()

      table.unique(['user_id'])
    })
  }

  async down() {
    this.schema.dropTable(this.tableName)
  }
}
