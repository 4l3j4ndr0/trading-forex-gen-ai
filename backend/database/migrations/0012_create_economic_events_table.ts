import { BaseSchema } from '@adonisjs/lucid/schema'

export default class extends BaseSchema {
  protected tableName = 'economic_events'

  async up() {
    this.schema.createTable(this.tableName, (table) => {
      table.increments('id').primary()
      table.string('title', 255).notNullable()
      table.string('currency', 3).notNullable()
      table.string('impact', 10).notNullable()
      table.string('forecast', 50).nullable()
      table.string('previous', 50).nullable()
      table.string('actual', 50).nullable()
      table.timestamp('event_at').notNullable()
      table.timestamp('created_at').notNullable()

      table.index(['event_at', 'impact'], 'idx_events_at_impact')
      table.index(['currency'], 'idx_events_currency')
    })
  }

  async down() {
    this.schema.dropTable(this.tableName)
  }
}
