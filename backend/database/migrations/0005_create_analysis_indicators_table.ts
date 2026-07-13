import { BaseSchema } from '@adonisjs/lucid/schema'

export default class extends BaseSchema {
  protected tableName = 'analysis_indicators'

  async up() {
    this.schema.createTable(this.tableName, (table) => {
      table.increments('id').primary()
      table.uuid('analysis_id').notNullable().references('id').inTable('analyses').onDelete('CASCADE')
      table.string('timeframe', 5).notNullable()
      table.string('indicator_name', 30).notNullable()
      table.decimal('value', 15, 6).nullable()
      table.jsonb('extra_values').nullable()
      table.string('interpretation', 20).nullable()
      table.timestamp('created_at').notNullable()

      table.index(['analysis_id', 'timeframe'], 'idx_indicators_analysis_tf')
    })
  }

  async down() {
    this.schema.dropTable(this.tableName)
  }
}
