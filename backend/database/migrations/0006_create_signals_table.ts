import { BaseSchema } from '@adonisjs/lucid/schema'

export default class extends BaseSchema {
  protected tableName = 'signals'

  async up() {
    this.schema.createTable(this.tableName, (table) => {
      table.uuid('id').primary().defaultTo(this.raw('uuid_generate_v4()'))
      table.uuid('analysis_id').nullable().references('id').inTable('analyses').onDelete('SET NULL')
      table.uuid('user_id').notNullable().references('id').inTable('users').onDelete('CASCADE')
      table.integer('pair_id').notNullable().references('id').inTable('pairs').onDelete('CASCADE')
      table.string('direction', 4).notNullable()
      table.string('signal_type', 15).notNullable()
      table.string('classification', 1).notNullable()
      table.integer('score').notNullable()
      table.decimal('entry_price', 15, 6).notNullable()
      table.decimal('stop_loss', 15, 6).notNullable()
      table.decimal('take_profit_1', 15, 6).notNullable()
      table.decimal('take_profit_2', 15, 6).nullable()
      table.decimal('take_profit_3', 15, 6).nullable()
      table.decimal('lot_size', 8, 2).notNullable()
      table.decimal('risk_percent', 4, 2).notNullable()
      table.decimal('risk_reward', 4, 2).notNullable()
      table.decimal('pips_at_risk', 8, 2).notNullable()
      table.decimal('pips_to_tp1', 8, 2).notNullable()
      table.decimal('pips_to_tp2', 8, 2).nullable()
      table.decimal('pips_to_tp3', 8, 2).nullable()
      table.decimal('invalidation_level', 15, 6).nullable()
      table.jsonb('timeframe_alignment').nullable()
      table.integer('confluence_count').notNullable().defaultTo(0)
      table.string('status', 15).notNullable().defaultTo('pending')
      table.text('notes').nullable()
      table.timestamp('expires_at').nullable()
      table.timestamp('activated_at').nullable()
      table.timestamp('closed_at').nullable()
      table.decimal('close_price', 15, 6).nullable()
      table.decimal('pnl_pips', 8, 2).nullable()
      table.decimal('pnl_money', 12, 2).nullable()
      table.timestamp('created_at').notNullable()
      table.timestamp('updated_at').nullable()

      table.index(['user_id', 'status'], 'idx_signals_user_status')
      table.index(['pair_id', 'created_at'], 'idx_signals_pair_created')
      table.index(['classification', 'status'], 'idx_signals_class_status')
    })
  }

  async down() {
    this.schema.dropTable(this.tableName)
  }
}
