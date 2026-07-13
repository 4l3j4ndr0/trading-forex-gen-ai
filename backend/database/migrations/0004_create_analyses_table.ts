import { BaseSchema } from '@adonisjs/lucid/schema'

export default class extends BaseSchema {
  protected tableName = 'analyses'

  async up() {
    this.schema.createTable(this.tableName, (table) => {
      table.uuid('id').primary().defaultTo(this.raw('uuid_generate_v4()'))
      table.integer('pair_id').notNullable().references('id').inTable('pairs').onDelete('CASCADE')
      table.uuid('user_id').nullable().references('id').inTable('users').onDelete('SET NULL')
      table.string('trigger_type', 20).notNullable().defaultTo('scheduled')
      table.string('timeframe_primary', 5).notNullable()
      table.jsonb('timeframes_analyzed').notNullable().defaultTo('["D1","H4","H1","M15"]')
      table.string('market_bias', 10).nullable()
      table.integer('trend_strength').nullable()
      table.integer('score').nullable()
      table.text('summary').nullable()
      table.text('ai_reasoning').nullable()
      table.string('news_sentiment', 10).nullable()
      table.text('news_summary').nullable()
      table.string('status', 15).notNullable().defaultTo('completed')
      table.timestamp('executed_at').notNullable()
      table.integer('duration_ms').nullable()
      table.timestamp('created_at').notNullable()

      table.index(['pair_id', 'created_at'], 'idx_analyses_pair_created')
      table.index(['status', 'created_at'], 'idx_analyses_status_created')
    })
  }

  async down() {
    this.schema.dropTable(this.tableName)
  }
}
