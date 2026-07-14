import { BaseSchema } from '@adonisjs/lucid/schema'

export default class extends BaseSchema {
  protected tableName = 'hourly_logs'

  async up() {
    this.schema.createTable(this.tableName, (table) => {
      table.uuid('id').primary().defaultTo(this.raw('uuid_generate_v4()'))
      table.uuid('user_id').notNullable().references('id').inTable('users').onDelete('CASCADE')
      table.timestamp('timestamp').notNullable()
      table.smallint('utc_hour').notNullable()
      table.string('session', 20).nullable()
      table.decimal('balance_usd', 12, 2).nullable()
      table.decimal('equity_usd', 12, 2).nullable()
      table.smallint('open_positions').notNullable().defaultTo(0)
      table.smallint('trades_opened').notNullable().defaultTo(0)
      table.smallint('trades_closed').notNullable().defaultTo(0)
      table.smallint('trades_skipped').notNullable().defaultTo(0)
      table.decimal('pnl_this_hour', 12, 4).nullable()
      table.decimal('cumulative_pnl_today', 12, 4).nullable()
      table.jsonb('symbols_analyzed').nullable()
      table.text('market_context').nullable()
      table.text('decision_summary').nullable()
      table.decimal('target_progress_pct', 6, 2).nullable()
      table.timestamp('created_at').notNullable()

      table.index(['user_id', 'timestamp'], 'idx_hourly_logs_user_timestamp')
    })

    // Add FK from trades to hourly_logs
    this.schema.alterTable('trades', (table) => {
      table.foreign('hourly_log_id').references('id').inTable('hourly_logs').onDelete('SET NULL')
    })
  }

  async down() {
    this.schema.alterTable('trades', (table) => {
      table.dropForeign('hourly_log_id')
    })
    this.schema.dropTable(this.tableName)
  }
}
