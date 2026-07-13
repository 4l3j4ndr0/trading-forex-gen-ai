import { BaseSchema } from '@adonisjs/lucid/schema'

export default class extends BaseSchema {
  protected tableName = 'signal_confluences'

  async up() {
    this.schema.createTable(this.tableName, (table) => {
      table.increments('id').primary()
      table.uuid('signal_id').notNullable().references('id').inTable('signals').onDelete('CASCADE')
      table.string('factor_type', 30).notNullable()
      table.string('timeframe', 5).notNullable()
      table.text('description').notNullable()
      table.decimal('weight', 3, 2).notNullable().defaultTo(1.0)
      table.timestamp('created_at').notNullable()

      table.index(['signal_id'], 'idx_confluences_signal')
    })
  }

  async down() {
    this.schema.dropTable(this.tableName)
  }
}
