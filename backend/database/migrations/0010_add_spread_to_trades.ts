import { BaseSchema } from '@adonisjs/lucid/schema'

export default class extends BaseSchema {
  protected tableName = 'trades'

  async up() {
    this.schema.alterTable(this.tableName, (table) => {
      table.decimal('spread_pips', 6, 2).nullable()
      table.decimal('spread_cost_usd', 8, 4).nullable()
    })
  }

  async down() {
    this.schema.alterTable(this.tableName, (table) => {
      table.dropColumn('spread_pips')
      table.dropColumn('spread_cost_usd')
    })
  }
}
