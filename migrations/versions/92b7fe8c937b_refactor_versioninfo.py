"""refactor versioninfo

Revision ID: 92b7fe8c937b
Revises: 61cbea5d192f
Create Date: 2023-11-12 01:43:06.665300

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from sner.server.materialized_views import CreateView, DropView


# revision identifiers, used by Alembic.
revision = '92b7fe8c937b'
down_revision = '61cbea5d192f'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(DropView('version_info', materialized=True))
    op.drop_table('version_info_temp')

    op.create_table('versioninfo',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('host_id', sa.Integer(), nullable=False),
    sa.Column('host_address', postgresql.INET(), nullable=False),
    sa.Column('host_hostname', sa.String(length=256), nullable=True),
    sa.Column('service_proto', sa.String(length=250), nullable=True),
    sa.Column('service_port', sa.Integer(), nullable=True),
    sa.Column('via_target', sa.String(length=250), nullable=True),
    sa.Column('product', sa.String(length=250), nullable=True),
    sa.Column('version', sa.String(length=250), nullable=True),
    sa.Column('extra', sa.JSON(), nullable=True),
    sa.Column('tags', postgresql.ARRAY(sa.String(), dimensions=1), nullable=False),
    sa.Column('comment', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    version_info_temp_table = op.create_table('version_info_temp',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('host_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('host_address', postgresql.INET(), autoincrement=False, nullable=False),
    sa.Column('host_hostname', sa.VARCHAR(length=256), autoincrement=False, nullable=True),
    sa.Column('service_proto', sa.VARCHAR(length=250), autoincrement=False, nullable=True),
    sa.Column('service_port', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('via_target', sa.VARCHAR(length=250), autoincrement=False, nullable=True),
    sa.Column('product', sa.VARCHAR(length=250), autoincrement=False, nullable=True),
    sa.Column('version', sa.VARCHAR(length=250), autoincrement=False, nullable=True),
    sa.Column('extra', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
    sa.PrimaryKeyConstraint('id', name='version_info_temp_pkey')
    )

    op.drop_table('versioninfo')
    op.execute(CreateView('version_info', sa.select(version_info_temp_table), materialized=True))
