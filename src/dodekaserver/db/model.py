import sqlalchemy

metadata = sqlalchemy.MetaData()

# users = sqlalchemy.Table(
#     "users",
#     metadata,
#     sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
#     sqlalchemy.Column("name", sqlalchemy.String(length=100)),
# )

USER_TABLE = "users"
USERNAME = "usp_hex"
NAME = "name"
LAST_NAME = "last_name"
PASSWORD = "password_file"
users = sqlalchemy.Table(
    USER_TABLE,
    metadata,
    # binary int of usp_hex
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column(USERNAME, sqlalchemy.String, unique=True),
    sqlalchemy.Column(NAME, sqlalchemy.String(length=100)),
    sqlalchemy.Column(LAST_NAME, sqlalchemy.String(length=100)),
    sqlalchemy.Column(PASSWORD, sqlalchemy.String(length=500)),
)

KEY_TABLE = "keys"
PUBLIC_KEY_COLUMN = "public"
PRIVATE_KEY_COLUMN = "private"
keys = sqlalchemy.Table(
    KEY_TABLE,
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column(PUBLIC_KEY_COLUMN, sqlalchemy.String(length=200)),
    sqlalchemy.Column(PRIVATE_KEY_COLUMN, sqlalchemy.String(length=200)),
)
