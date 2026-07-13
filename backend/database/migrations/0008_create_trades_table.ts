import { BaseSchema } from '@adonisjs/lucid/schema'

export default class extends BaseSchema {
  protected tableName = 'trades'

  async up() {
    this.schema.createTable(this.tableName, (table) => {
      table.uuid('id').primary().defaultTo(this.raw('uuid_generate_v4()'))
      table.uuid('signal_id').nullable().references('id').inTable('signals').onDelete('SET NULL')
      table.uuid('user_id').notNullable().references('id').inTable('users').onDelete('CASCADE')
      table.integer('pair_id').notNullable().references('id').inTable('pairs').onDelete('CASCADE')
      table.string('direction', 4).notNullable()
      table.decimal('entry_price', 15, 6).notNullable()
      table.decimal('stop_loss', 15, 6).notNullable()
      table.decimal('current_sl', 15, 6).notNullable()
      table.decimal('take_profit_1', 15, 6).notNullable()
      table.decimal('take_profit_2', 15, 6).nullable()
      table.decimal('take_profit_3', 15, 6).nullable()
      table.decimal('lot_size', 8, 2).notNullable()
      table.decimal('risk_percent', 4, 2).notNullable()
      table.string('status', 15).notNullable().defaultTo('open')
      table.string('close_reason', 20).nullable()
      table.decimal('close_price', 15, 6).nullable()
      table.decimal('pnl_pips', 8, 2).nullable()
      table.decimal('pnl_money', 12, 2).nullable()
      table.decimal('commission', 8, 2).nullable().defaultTo(0)
      table.decimal('swap', 8, 2).nullable().defaultTo(0)
      table.string('broker_order_id', 100).nullable()
      table.string('execution_type', 10).notNullable().defaultTo('manual')
      table.timestamp('opened_at').notNullable()
      table.timestamp('closed_at').nullable()
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
