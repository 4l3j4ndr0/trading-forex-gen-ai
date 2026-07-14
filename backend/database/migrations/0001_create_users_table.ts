import { BaseSchema } from '@adonisjs/lucid/schema'

export default class extends BaseSchema {
  protected tableName = 'users'

  async up() {
    this.schema.raw('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    this.schema.createTable(this.tableName, (table) => {
      table.uuid('id').primary().defaultTo(this.raw('uuid_generate_v4()'))
      table.string('cognito_sub', 255).notNullable().unique()
      table.string('email', 254).notNullable().unique()
      table.string('full_name', 255).nullable()
      table.string('account_currency', 3).notNullable().defaultTo('USD')
      table.boolean('is_active').notNullable().defaultTo(true)
      table.timestamp('last_login_at').nullable()
      table.timestamp('created_at').notNullable()
      table.timestamp('updated_at').nullable()
    })
  }

  async down() {
    this.schema.dropTable(this.tableName)
    this.schema.raw('DROP EXTENSION IF EXISTS "uuid-ossp"')
  }
}
