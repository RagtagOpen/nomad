"""add canceled column to carpools

Revision ID: 1c16c79d5f85
Revises: 0dad6c8372e4
Create Date: 2018-09-04 23:19:02.950009

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1c16c79d5f85'
down_revision = '0dad6c8372e4'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('carpools', sa.Column('canceled', sa.Boolean(), nullable=True, server_default=sa.schema.DefaultClause("0")))
    op.add_column('carpools', sa.Column('cancel_reason', sa.String(), nullable=True))
    op.create_index(op.f('ix_carpools_canceled'), 'carpools', ['canceled'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_carpools_canceled'), table_name='carpools')
    op.drop_column('carpools', 'canceled')
    op.drop_column('carpools', 'cancel_reason')
