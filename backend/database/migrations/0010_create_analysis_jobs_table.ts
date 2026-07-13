import { BaseSchema } from '@adonisjs/lucid/schema'

export default class extends BaseSchema {
  protected tableName = 'analysis_jobs'

  async up() {
    this.schema.createTable(this.tableName, (table) => {
      table.increments('id').primary()
      table.string('session', 20).notNullable()
      table.jsonb('pairs_analyzed').notNullable().defaultTo('[]')
      table.integer('signals_generated').notNullable().defaultTo(0)
      table.string('status', 15).notNullable().defaultTo('running')
      table.text('error_message').nullable()
      table.timestamp('started_at').notNullable()
      table.timestamp('finished_at').nullable()
      table.timestamp('created_at').notNullable()

      table.index(['session', 'created_at'], 'idx_jobs_session_created')
    })
  }

  async down() {
    this.schema.dropTable(this.tableName)
  }
}
