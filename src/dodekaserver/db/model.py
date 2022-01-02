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

REFRESH_TOKEN_TABLE = "refreshtokens"
FAMILY_ID = "family_id"
ACCESS_VALUE = "access_value"
ID_TOKEN_VALUE = "id_token_value"
EXPIRATION = "exp"
NONCE = "nonce"
ISSUED_AT = "iat"
refreshtokens = sqlalchemy.Table(
    REFRESH_TOKEN_TABLE,
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column(FAMILY_ID, sqlalchemy.String(length=200)),
    sqlalchemy.Column(ACCESS_VALUE, sqlalchemy.String(length=1000)),
    sqlalchemy.Column(ID_TOKEN_VALUE, sqlalchemy.String(length=1000)),
    sqlalchemy.Column(EXPIRATION, sqlalchemy.Integer),
    sqlalchemy.Column(ISSUED_AT, sqlalchemy.Integer),
    sqlalchemy.Column(NONCE, sqlalchemy.String(length=200))
)
