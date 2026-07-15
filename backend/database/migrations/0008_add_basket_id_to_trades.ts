import { BaseSchema } from '@adonisjs/lucid/schema'

export default class extends BaseSchema {
  protected tableName = 'trades'

  async up() {
    this.schema.alterTable(this.tableName, (table) => {
      table.string('basket_id', 50).nullable().index()
    })
  }

  async down() {
    this.schema.alterTable(this.tableName, (table) => {
      table.dropColumn('basket_id')
    })
  }
}
