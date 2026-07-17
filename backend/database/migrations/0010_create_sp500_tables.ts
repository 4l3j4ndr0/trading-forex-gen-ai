import { BaseSchema } from '@adonisjs/lucid/schema'

export default class extends BaseSchema {
  async up() {
    // SP500 Settings (config from frontend, not .env)
    this.schema.createTable('sp500_settings', (table) => {
      table.uuid('id').primary().defaultTo(this.raw('gen_random_uuid()'))
      table.uuid('user_id').notNullable().references('id').inTable('users').onDelete('CASCADE')

      // Symbol config
      table.string('symbol', 20).notNullable().defaultTo('US500Cash')
      table.decimal('point_value', 6, 2).notNullable().defaultTo(1.0) // $1 per point per lot
      table.decimal('min_lot', 6, 2).notNullable().defaultTo(0.01)
      table.decimal('max_lot', 6, 2).notNullable().defaultTo(5.0)

      // Risk Management
      table.decimal('max_risk_per_trade_pct', 4, 2).notNullable().defaultTo(1.0)
      table.decimal('max_daily_loss_pct', 4, 2).notNullable().defaultTo(5.0)
      table.integer('max_consecutive_losses').notNullable().defaultTo(5)
      table.decimal('min_rr_ratio', 4, 2).notNullable().defaultTo(1.5)
      table.integer('max_open_positions').notNullable().defaultTo(5)

      // Killzones (UTC times)
      table.string('am_killzone_start', 5).notNullable().defaultTo('13:30')
      table.string('am_killzone_end', 5).notNullable().defaultTo('15:30')
      table.string('pm_killzone_start', 5).notNullable().defaultTo('18:00')
      table.string('pm_killzone_end', 5).notNullable().defaultTo('20:00')
      table.string('premarket_start', 5).notNullable().defaultTo('12:00')
      table.string('regular_session_start', 5).notNullable().defaultTo('13:30')
      table.string('regular_session_end', 5).notNullable().defaultTo('20:00')

      // News filter
      table.integer('news_buffer_minutes').notNullable().defaultTo(15)

      // Target
      table.decimal('daily_target_pct', 4, 2).notNullable().defaultTo(1.0)
      table.decimal('daily_target_points', 8, 2).notNullable().defaultTo(30.0)

      // Analysis filters
      table.integer('min_structure_score').notNullable().defaultTo(2) // MTF alignment
      table.decimal('min_sweep_distance_points', 6, 2).notNullable().defaultTo(5.0)

      // System
      table.boolean('kill_switch').notNullable().defaultTo(false)
      table.boolean('auto_trading_enabled').notNullable().defaultTo(true)

      table.timestamp('created_at').notNullable()
      table.timestamp('updated_at').nullable()

      table.unique(['user_id'])
    })

    // SP500 Trades
    this.schema.createTable('sp500_trades', (table) => {
      table.uuid('id').primary().defaultTo(this.raw('gen_random_uuid()'))
      table.uuid('user_id').notNullable().references('id').inTable('users').onDelete('CASCADE')
      table.bigInteger('ticket').notNullable().unique()
      table.string('side', 4).notNullable() // BUY or SELL
      table.decimal('lot_size', 10, 2).notNullable()
      table.decimal('entry_price', 12, 2).notNullable()
      table.decimal('exit_price', 12, 2).nullable()
      table.decimal('sl_price', 12, 2).nullable()
      table.decimal('tp_price', 12, 2).nullable()
      table.decimal('sl_points', 8, 2).nullable()
      table.decimal('tp_points', 8, 2).nullable()
      table.decimal('pnl_points', 10, 2).nullable()
      table.decimal('pnl_usd', 10, 2).nullable()
      table.decimal('risk_usd', 10, 2).nullable()
      table.text('comment').nullable()
      table.string('basket_id', 50).nullable()
      table.string('close_reason', 50).nullable()
      table.string('status', 10).notNullable().defaultTo('open')
      table.timestamp('opened_at').notNullable()
      table.timestamp('closed_at').nullable()
      table.integer('holding_minutes').nullable()
      table.timestamp('created_at').notNullable()

      table.index(['user_id', 'status'])
      table.index(['basket_id'])
      table.index(['opened_at'])
    })

    // SP500 Agent Logs
    this.schema.createTable('sp500_logs', (table) => {
      table.uuid('id').primary().defaultTo(this.raw('gen_random_uuid()'))
      table.uuid('user_id').notNullable().references('id').inTable('users').onDelete('CASCADE')
      table.text('decision').notNullable()
      table.integer('trades_opened').defaultTo(0)
      table.integer('trades_closed').defaultTo(0)
      table.decimal('floating_pnl', 10, 2).defaultTo(0)
      table.timestamp('created_at').notNullable()

      table.index(['user_id', 'created_at'])
    })
  }

  async down() {
    this.schema.dropTable('sp500_logs')
    this.schema.dropTable('sp500_trades')
    this.schema.dropTable('sp500_settings')
  }
}
