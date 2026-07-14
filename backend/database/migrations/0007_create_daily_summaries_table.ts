import { BaseSchema } from '@adonisjs/lucid/schema'

export default class extends BaseSchema {
  protected tableName = 'daily_summaries'

  async up() {
    this.schema.createTable(this.tableName, (table) => {
      table.uuid('id').primary().defaultTo(this.raw('uuid_generate_v4()'))
      table.uuid('user_id').notNullable().references('id').inTable('users').onDelete('CASCADE')
      table.date('date').notNullable()
      table.decimal('balance_start', 12, 2).nullable()
      table.decimal('balance_end', 12, 2).nullable()
      table.decimal('target_usd', 12, 2).nullable()
      table.decimal('realized_pnl', 12, 4).nullable()
      table.smallint('trades_total').notNullable().defaultTo(0)
      table.smallint('trades_won').notNullable().defaultTo(0)
      table.smallint('trades_lost').notNullable().defaultTo(0)
      table.decimal('win_rate', 5, 2).nullable()
      table.decimal('best_trade_usd', 12, 4).nullable()
      table.decimal('worst_trade_usd', 12, 4).nullable()
      table.decimal('max_drawdown_usd', 12, 4).nullable()
      table.boolean('target_reached').notNullable().defaultTo(false)
      table.timestamp('created_at').notNullable()

      table.unique(['user_id', 'date'], 'idx_daily_summaries_user_date')
    })
  }

  async down() {
    this.schema.dropTable(this.tableName)
  }
}
