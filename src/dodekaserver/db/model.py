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
    sqlalchemy.Column(USERNAME, sqlalchemy.String(length=255), unique=True),
    sqlalchemy.Column(PASSWORD, sqlalchemy.String(length=500)),
)

KEY_TABLE = "keys"
PUBLIC_KEY_COLUMN = "public"
PRIVATE_KEY_COLUMN = "private"
PRIVATE_FMT_COLUMN = "private_format"
PUBLIC_FMT_COLUMN = "public_format"
PUBLIC_ENCODING = "public_encoding"
PRIVATE_ENCODING = "private_encoding"
ALGORITHM_COLUMN = "algorithm"
keys = sqlalchemy.Table(
    KEY_TABLE,
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column(ALGORITHM_COLUMN, sqlalchemy.String(length=100)),
    sqlalchemy.Column(PUBLIC_KEY_COLUMN, sqlalchemy.String(length=200)),
    sqlalchemy.Column(PRIVATE_KEY_COLUMN, sqlalchemy.String(length=200)),
    sqlalchemy.Column(PUBLIC_FMT_COLUMN, sqlalchemy.String(length=100)),
    sqlalchemy.Column(PRIVATE_FMT_COLUMN, sqlalchemy.String(length=100)),
    sqlalchemy.Column(PUBLIC_ENCODING, sqlalchemy.String(length=100)),
    sqlalchemy.Column(PRIVATE_ENCODING, sqlalchemy.String(length=100))
)
