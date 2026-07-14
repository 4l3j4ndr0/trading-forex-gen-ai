import { BaseSchema } from '@adonisjs/lucid/schema'

export default class extends BaseSchema {
  protected tableName = 'broker_configs'

  async up() {
    this.schema.createTable(this.tableName, (table) => {
      table.uuid('id').primary().defaultTo(this.raw('uuid_generate_v4()'))
      table.uuid('user_id').notNullable().references('id').inTable('users').onDelete('CASCADE')
      table.string('broker_name', 50).notNullable().defaultTo('XM')
      table.integer('mt5_login').notNullable()
      table.text('mt5_password_encrypted').notNullable()
      table.string('mt5_server', 100).notNullable()
      table.string('bridge_url', 255).notNullable()
      table.text('bridge_api_key_encrypted').notNullable()
      table.string('symbol_suffix', 10).notNullable().defaultTo('#')
      table.string('account_type', 10).notNullable().defaultTo('demo')
      table.boolean('is_active').notNullable().defaultTo(true)
      table.timestamp('last_connected_at').nullable()
      table.timestamp('created_at').notNullable()
      table.timestamp('updated_at').nullable()

      table.unique(['user_id'])
    })
  }

  async down() {
    this.schema.dropTable(this.tableName)
  }
}
