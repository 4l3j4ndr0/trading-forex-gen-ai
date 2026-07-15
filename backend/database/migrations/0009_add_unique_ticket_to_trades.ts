import { BaseSchema } from '@adonisjs/lucid/schema'

export default class extends BaseSchema {
  protected tableName = 'trades'

  async up() {
    this.schema.alterTable(this.tableName, (table) => {
      table.unique(['ticket'], 'trades_ticket_unique')
    })
  }

  async down() {
    this.schema.alterTable(this.tableName, (table) => {
      table.dropUnique(['ticket'], 'trades_ticket_unique')
    })
  }
}
