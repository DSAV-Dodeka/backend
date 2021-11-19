import sqlalchemy

metadata = sqlalchemy.MetaData()

# users = sqlalchemy.Table(
#     "users",
#     metadata,
#     sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
#     sqlalchemy.Column("name", sqlalchemy.String(length=100)),
# )

USER_TABLE = "users"
users = sqlalchemy.Table(
    USER_TABLE,
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("name", sqlalchemy.String(length=100)),
    sqlalchemy.Column("last_name", sqlalchemy.String(length=100)),
)
