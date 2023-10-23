"""localdb vulnsearch

Revision ID: a2ab383eef52
Revises: ab03e37b4677
Create Date: 2023-10-23 09:07:11.159482

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import MetaData

from sner.server.materialized_views import CreateView, DropView


# revision identifiers, used by Alembic.
revision = 'a2ab383eef52'
down_revision = 'ab03e37b4677'
branch_labels = None
depends_on = None


def upgrade():
    vulnsearch_temp_table = op.create_table('vulnsearch_temp',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('host_id', sa.Integer(), nullable=False),
    sa.Column('service_id', sa.Integer(), nullable=True),
    sa.Column('host_address', postgresql.INET(), nullable=False),
    sa.Column('host_hostname', sa.String(length=256), nullable=True),
    sa.Column('service_proto', sa.String(length=250), nullable=True),
    sa.Column('service_port', sa.Integer(), nullable=True),
    sa.Column('via_target', sa.String(length=250), nullable=True),
    sa.Column('cveid', sa.String(length=250), nullable=True),
    sa.Column('name', sa.Text(), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('cvss', sa.Float(), nullable=True),
    sa.Column('cvss3', sa.Float(), nullable=True),
    sa.Column('attack_vector', sa.String(length=250), nullable=True),
    sa.Column('data', sa.JSON(), nullable=True),
    sa.Column('cpe', sa.JSON(), nullable=True),
    sa.Column('cpe_full', sa.String(length=1000), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )

    op.execute(CreateView('vulnsearch', sa.select(vulnsearch_temp_table), materialized=True))

def downgrade():
    op.execute(DropView('vulnsearch', materialized=True))
    op.drop_table('vulnsearch_temp')
