"""refactor vulsnearch

Revision ID: 61cbea5d192f
Revises: a2ab383eef52
Create Date: 2023-11-06 19:46:03.438959

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from sner.server.materialized_views import CreateView, DropView


# revision identifiers, used by Alembic.
revision = '61cbea5d192f'
down_revision = 'a2ab383eef52'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(DropView('vulnsearch', materialized=True))
    op.drop_table('vulnsearch_temp')

    op.create_table('vulnsearch',
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
    sa.Column('tags', postgresql.ARRAY(sa.String(), dimensions=1), nullable=False),
    sa.Column('comment', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    vulnsearch_temp_table = op.create_table('vulnsearch_temp',
    sa.Column('id', sa.VARCHAR(length=32), autoincrement=False, nullable=False),
    sa.Column('host_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('service_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('host_address', postgresql.INET(), autoincrement=False, nullable=False),
    sa.Column('host_hostname', sa.VARCHAR(length=256), autoincrement=False, nullable=True),
    sa.Column('service_proto', sa.VARCHAR(length=250), autoincrement=False, nullable=True),
    sa.Column('service_port', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('via_target', sa.VARCHAR(length=250), autoincrement=False, nullable=True),
    sa.Column('cveid', sa.VARCHAR(length=250), autoincrement=False, nullable=True),
    sa.Column('name', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('description', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('cvss', postgresql.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
    sa.Column('cvss3', postgresql.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
    sa.Column('attack_vector', sa.VARCHAR(length=250), autoincrement=False, nullable=True),
    sa.Column('data', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
    sa.Column('cpe', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
    sa.Column('cpe_full', sa.VARCHAR(length=1000), autoincrement=False, nullable=True),
    sa.PrimaryKeyConstraint('id', name='vulnsearch_temp_pkey')
    )

    op.drop_table('vulnsearch')
    op.execute(CreateView('vulnsearch', sa.select(vulnsearch_temp_table), materialized=True))
