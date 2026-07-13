import { BaseSchema } from '@adonisjs/lucid/schema'

export default class extends BaseSchema {
  protected tableName = 'trade_partials'

  async up() {
    this.schema.createTable(this.tableName, (table) => {
      table.increments('id').primary()
      table.uuid('trade_id').notNullable().references('id').inTable('trades').onDelete('CASCADE')
      table.string('level', 5).notNullable()
      table.decimal('percentage', 5, 2).notNullable()
      table.decimal('close_price', 15, 6).notNullable()
      table.decimal('pnl_pips', 8, 2).notNullable()
      table.decimal('pnl_money', 12, 2).notNullable()
      table.timestamp('closed_at').notNullable()

      table.index(['trade_id'], 'idx_partials_trade')
    })
  }

  async down() {
    this.schema.dropTable(this.tableName)
  }
}
