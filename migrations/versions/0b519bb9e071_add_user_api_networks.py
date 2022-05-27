"""add user.api_networks

Revision ID: 0b519bb9e071
Revises: bb0d676c28c7
Create Date: 2022-05-26 21:34:32.021058

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0b519bb9e071'
down_revision = 'bb0d676c28c7'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user', sa.Column('api_networks', postgresql.ARRAY(sa.String(), dimensions=1)))
    op.execute(sa.table('user', sa.column('api_networks')).update().values(api_networks=[]))
    op.alter_column('user', 'api_networks', nullable=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('user', 'api_networks')
    # ### end Alembic commands ###