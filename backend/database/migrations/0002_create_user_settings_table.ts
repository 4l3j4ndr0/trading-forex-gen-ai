import { BaseSchema } from '@adonisjs/lucid/schema'

export default class extends BaseSchema {
  protected tableName = 'user_settings'

  async up() {
    this.schema.createTable(this.tableName, (table) => {
      table.increments('id').primary()
      table.uuid('user_id').notNullable().references('id').inTable('users').onDelete('CASCADE')
      table.decimal('max_risk_per_trade', 4, 2).notNullable().defaultTo(1.0)
      table.decimal('max_daily_drawdown', 4, 2).notNullable().defaultTo(6.0)
      table.decimal('max_weekly_drawdown', 4, 2).notNullable().defaultTo(15.0)
      table.integer('max_open_positions').notNullable().defaultTo(3)
      table.jsonb('preferred_pairs').notNullable().defaultTo('[]')
      table.jsonb('preferred_sessions').notNullable().defaultTo('["london","new_york"]')
      table.integer('min_signal_score').notNullable().defaultTo(6)
      table.string('min_signal_class', 1).notNullable().defaultTo('B')
      table.jsonb('alert_channels').notNullable().defaultTo('{"websocket":true,"email":false}')
      table.jsonb('broker_config').nullable()
      table.string('timezone', 50).notNullable().defaultTo('America/Bogota')
      table.timestamp('created_at').notNullable()
      table.timestamp('updated_at').nullable()

      table.unique(['user_id'])
    })
  }

  async down() {
    this.schema.dropTable(this.tableName)
  }
}
