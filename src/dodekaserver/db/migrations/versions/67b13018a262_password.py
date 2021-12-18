"""Password

Revision ID: 67b13018a262
Revises: 0170a07aac96
Create Date: 2021-11-21 23:45:37.537419

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '67b13018a262'
down_revision = '0170a07aac96'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('password_hash_hex', sa.String(length=100), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'password_hash_hex')
    # ### end Alembic commands ###
