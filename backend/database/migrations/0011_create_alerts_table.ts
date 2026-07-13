import { BaseSchema } from '@adonisjs/lucid/schema'

export default class extends BaseSchema {
  protected tableName = 'alerts'

  async up() {
    this.schema.createTable(this.tableName, (table) => {
      table.increments('id').primary()
      table.uuid('user_id').notNullable().references('id').inTable('users').onDelete('CASCADE')
      table.uuid('signal_id').nullable().references('id').inTable('signals').onDelete('SET NULL')
      table.string('channel', 20).notNullable()
      table.string('title', 200).notNullable()
      table.text('body').nullable()
      table.boolean('is_read').notNullable().defaultTo(false)
      table.timestamp('sent_at').notNullable()
      table.timestamp('read_at').nullable()
      table.timestamp('created_at').notNullable()

      table.index(['user_id', 'is_read'], 'idx_alerts_user_read')
    })
  }

  async down() {
    this.schema.dropTable(this.tableName)
  }
}
