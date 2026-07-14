import { BaseSchema } from '@adonisjs/lucid/schema'

export default class extends BaseSchema {
  protected tableName = 'trades'

  async up() {
    this.schema.createTable(this.tableName, (table) => {
      table.uuid('id').primary().defaultTo(this.raw('uuid_generate_v4()'))
      table.uuid('user_id').notNullable().references('id').inTable('users').onDelete('CASCADE')
      table.integer('pair_id').notNullable().references('id').inTable('pairs').onDelete('CASCADE')
      table.bigInteger('ticket').nullable()
      table.string('side', 4).notNullable()
      table.decimal('lot_size', 8, 2).notNullable()
      table.decimal('entry_price', 12, 6).notNullable()
      table.decimal('exit_price', 12, 6).nullable()
      table.decimal('sl_price', 12, 6).notNullable()
      table.decimal('tp_price', 12, 6).notNullable()
      table.decimal('sl_pips', 8, 2).notNullable()
      table.decimal('tp_pips', 8, 2).notNullable()
      table.decimal('pnl_pips', 8, 2).nullable()
      table.decimal('pnl_usd', 12, 4).nullable()
      table.decimal('risk_usd', 12, 4).notNullable()
      table.decimal('rr_ratio', 6, 2).notNullable()
      table.decimal('rr_achieved', 6, 2).nullable()
      table.string('status', 15).notNullable().defaultTo('open')
      table.string('close_reason', 30).nullable()
      table.text('comment').nullable()
      table.decimal('swap', 8, 2).nullable().defaultTo(0)
      table.decimal('commission', 8, 2).nullable().defaultTo(0)
      table.timestamp('opened_at').notNullable()
      table.timestamp('closed_at').nullable()
      table.decimal('holding_minutes', 8, 1).nullable()
      table.uuid('hourly_log_id').nullable()
      table.timestamp('created_at').notNullable()
      table.timestamp('updated_at').nullable()

      table.index(['user_id', 'status'], 'idx_trades_user_status')
      table.index(['user_id', 'closed_at'], 'idx_trades_user_closed')
      table.index(['pair_id', 'status'], 'idx_trades_pair_status')
    })
  }

  async down() {
    this.schema.dropTable(this.tableName)
  }
}
