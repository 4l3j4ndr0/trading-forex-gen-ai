import { BaseSchema } from '@adonisjs/lucid/schema'

export default class extends BaseSchema {
  protected tableName = 'pairs'

  async up() {
    this.schema.createTable(this.tableName, (table) => {
      table.increments('id').primary()
      table.string('symbol', 10).notNullable().unique()
      table.string('massive_ticker', 15).notNullable().unique()
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
  }

  async down() {
    this.schema.dropTable(this.tableName)
  }
}
