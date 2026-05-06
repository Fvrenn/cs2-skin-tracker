"""init

Revision ID: 540c2b5ba3ab
Revises:
Create Date: 2026-05-06 20:45:03.535996

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '540c2b5ba3ab'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('price_history',
    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
    sa.Column('market_hash_name', sa.String(length=255), nullable=False),
    sa.Column('source', sa.Enum('csfloat', 'skinport', 'steam', name='price_source'), nullable=False),
    sa.Column('price_median', sa.Integer(), nullable=True),
    sa.Column('price_min', sa.Integer(), nullable=True),
    sa.Column('price_max', sa.Integer(), nullable=True),
    sa.Column('price_mean', sa.Integer(), nullable=True),
    sa.Column('volume', sa.Integer(), nullable=True),
    sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('market_hash_name', 'source', 'recorded_at', name='idx_price_history_unique')
    )
    op.create_index('idx_price_history_lookup', 'price_history', ['market_hash_name', 'source', 'recorded_at'], unique=False)
    op.create_table('users',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('steam_id', sa.String(length=50), nullable=True),
    sa.Column('discord_id', sa.String(length=50), nullable=True),
    sa.Column('threshold_up', sa.Numeric(precision=5, scale=4), server_default='0.2500', nullable=False),
    sa.Column('threshold_down', sa.Numeric(precision=5, scale=4), server_default='0.1000', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email')
    )
    op.create_table('skins',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('market_hash_name', sa.String(length=255), nullable=False),
    sa.Column('asset_id', sa.String(length=50), nullable=True),
    sa.Column('purchase_price', sa.Integer(), nullable=True),
    sa.Column('peak_price', sa.Integer(), nullable=True),
    sa.Column('peak_price_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('status', sa.Enum('passive', 'active', 'alert', 'reminder', 'sold', name='skin_status'), server_default='passive', nullable=False),
    sa.Column('sold_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('sold_price', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'asset_id', name='uq_skins_user_asset')
    )
    op.create_index('idx_skins_market_hash_name', 'skins', ['market_hash_name'], unique=False)
    op.create_index('idx_skins_status', 'skins', ['status'], unique=False)
    op.create_index('idx_skins_user_id', 'skins', ['user_id'], unique=False)
    op.create_table('watchlist',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('market_hash_name', sa.String(length=255), nullable=False),
    sa.Column('alert_on_drop', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('drop_threshold', sa.Numeric(precision=5, scale=4), nullable=True),
    sa.Column('alert_on_rise', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('rise_threshold', sa.Numeric(precision=5, scale=4), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'market_hash_name', name='uq_watchlist_user_skin')
    )
    op.create_index('idx_watchlist_user_id', 'watchlist', ['user_id'], unique=False)
    op.create_table('alert_logs',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('skin_id', sa.UUID(), nullable=True),
    sa.Column('watchlist_id', sa.UUID(), nullable=True),
    sa.Column('alert_type', sa.Enum('rise', 'peak_drop', 'reminder', 'watchlist_drop', 'watchlist_rise', name='alert_type'), nullable=False),
    sa.Column('price_at_alert', sa.Integer(), nullable=False),
    sa.Column('peak_price_ref', sa.Integer(), nullable=True),
    sa.Column('purchase_price_ref', sa.Integer(), nullable=True),
    sa.Column('discord_message', sa.Text(), nullable=True),
    sa.Column('discord_sent', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['skin_id'], ['skins.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['watchlist_id'], ['watchlist.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_alert_logs_created_at', 'alert_logs', ['created_at'], unique=False)
    op.create_index('idx_alert_logs_skin_id', 'alert_logs', ['skin_id'], unique=False)
    op.create_index('idx_alert_logs_user_id', 'alert_logs', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_alert_logs_user_id', table_name='alert_logs')
    op.drop_index('idx_alert_logs_skin_id', table_name='alert_logs')
    op.drop_index('idx_alert_logs_created_at', table_name='alert_logs')
    op.drop_table('alert_logs')
    op.drop_index('idx_watchlist_user_id', table_name='watchlist')
    op.drop_table('watchlist')
    op.drop_index('idx_skins_user_id', table_name='skins')
    op.drop_index('idx_skins_status', table_name='skins')
    op.drop_index('idx_skins_market_hash_name', table_name='skins')
    op.drop_table('skins')
    op.drop_table('users')
    op.drop_index('idx_price_history_lookup', table_name='price_history')
    op.drop_table('price_history')
    sa.Enum(name='alert_type').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='skin_status').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='price_source').drop(op.get_bind(), checkfirst=True)
