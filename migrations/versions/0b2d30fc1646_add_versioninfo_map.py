"""add versioninfo map

Revision ID: 0b2d30fc1646
Revises: 8e55e1df7106
Create Date: 2023-09-03 14:35:04.421781

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import MetaData

from sner.server.materialized_views import CreateView, DropView


# revision identifiers, used by Alembic.
revision = '0b2d30fc1646'
down_revision = '8e55e1df7106'
branch_labels = None
depends_on = None


def upgrade():
    version_info_temp_table = op.create_table('version_info_temp',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('host_id', sa.Integer(), nullable=False),
    sa.Column('host_address', postgresql.INET(), nullable=False),
    sa.Column('host_hostname', sa.String(length=256), nullable=True),
    sa.Column('service_proto', sa.String(length=250), nullable=False),
    sa.Column('service_port', sa.Integer(), nullable=False),
    sa.Column('via_target', sa.String(length=250), nullable=True),
    sa.Column('product', sa.String(length=250), nullable=True),
    sa.Column('version', sa.String(length=250), nullable=True),
    sa.Column('extra', sa.JSON(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )

    op.execute(CreateView('version_info', sa.select(version_info_temp_table), materialized=True))


def downgrade():
    op.execute(DropView('version_info', materialized=True))
    op.drop_table('version_info_temp')
