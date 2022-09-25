import sqlalchemy

metadata = sqlalchemy.MetaData()

USER_TABLE = "users"
USERNAME = "usp_hex"
PASSWORD = "password_file"
SCOPES = "scope"
users = sqlalchemy.Table(
    USER_TABLE,
    metadata,
    # binary int of usp_hex
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column(USERNAME, sqlalchemy.String(length=255), unique=True, nullable=False),
    sqlalchemy.Column(PASSWORD, sqlalchemy.String(length=500)),
    sqlalchemy.Column(SCOPES, sqlalchemy.String(length=200), nullable=False)
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
    sqlalchemy.Column(ALGORITHM_COLUMN, sqlalchemy.String(length=100), nullable=False),
    sqlalchemy.Column(PUBLIC_KEY_COLUMN, sqlalchemy.String(length=200), nullable=False),
    sqlalchemy.Column(PRIVATE_KEY_COLUMN, sqlalchemy.String(length=200), nullable=False),
    sqlalchemy.Column(PUBLIC_FMT_COLUMN, sqlalchemy.String(length=100), nullable=False),
    sqlalchemy.Column(PRIVATE_FMT_COLUMN, sqlalchemy.String(length=100), nullable=False),
    sqlalchemy.Column(PUBLIC_ENCODING, sqlalchemy.String(length=100), nullable=False),
    sqlalchemy.Column(PRIVATE_ENCODING, sqlalchemy.String(length=100), nullable=False)
)

OPAQUE_SETUP_TABLE = "opaque"
OPAQUE_VALUE = "value"

opaque_setup = sqlalchemy.Table(
    OPAQUE_SETUP_TABLE,
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column(OPAQUE_VALUE, sqlalchemy.String(length=300), nullable=False)
)

REFRESH_TOKEN_TABLE = "refreshtokens"
REFR_USER_ID = "user_id"
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
    sqlalchemy.Column(REFR_USER_ID, sqlalchemy.Integer, sqlalchemy.ForeignKey("users.id", ondelete="CASCADE"),
                      nullable=False),
    sqlalchemy.Column(FAMILY_ID, sqlalchemy.String(length=200), nullable=False),
    sqlalchemy.Column(ACCESS_VALUE, sqlalchemy.String(length=1000), nullable=False),
    sqlalchemy.Column(ID_TOKEN_VALUE, sqlalchemy.String(length=1000), nullable=False),
    sqlalchemy.Column(EXPIRATION, sqlalchemy.Integer, nullable=False),
    sqlalchemy.Column(ISSUED_AT, sqlalchemy.Integer, nullable=False),
    sqlalchemy.Column(NONCE, sqlalchemy.String(length=200))
)

SIGNEDUP_TABLE = "signedup"
SU_FIRSTNAME = "firstname"
SU_LASTNAME = "lastname"
SU_PHONE = "phone"
SU_EMAIL = "email"
SU_CONFIRMED = "confirmed"
signedup = sqlalchemy.Table(
    SIGNEDUP_TABLE,
    metadata,
    sqlalchemy.Column(SU_FIRSTNAME, sqlalchemy.String(length=100), nullable=False),
    sqlalchemy.Column(SU_LASTNAME, sqlalchemy.String(length=100), nullable=False),
    sqlalchemy.Column(SU_PHONE, sqlalchemy.String(length=15), nullable=False),
    sqlalchemy.Column(SU_EMAIL, sqlalchemy.String(length=100), primary_key=True),
    sqlalchemy.Column(SU_CONFIRMED, sqlalchemy.Boolean, nullable=False),
)

USERDATA_TABLE = "userdata"
UD_ACTIVE = "active"
UD_FIRSTNAME = "firstname"
UD_LASTNAME = "lastname"
UD_CALLNAME = "callname"
UD_PHONE = "phone"
UD_EMAIL = "email"
AV40_ID = "av40id"
JOINED = "joined"
BIRTHDATE = "birthdate"
REGISTER_ID = "registerid"
EDUCATION_INSTITUTION = "eduinstitution"
USER_REGISTERED = "registered"
userdata = sqlalchemy.Table(
    USERDATA_TABLE,
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, sqlalchemy.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    sqlalchemy.Column(UD_ACTIVE, sqlalchemy.Boolean, nullable=False),
    sqlalchemy.Column(UD_FIRSTNAME, sqlalchemy.String(length=100), nullable=False),
    sqlalchemy.Column(UD_LASTNAME, sqlalchemy.String(length=100), nullable=False),
    sqlalchemy.Column(UD_CALLNAME, sqlalchemy.String(length=100)),
    sqlalchemy.Column(UD_PHONE, sqlalchemy.String(length=15)),
    sqlalchemy.Column(UD_EMAIL, sqlalchemy.String(length=100), unique=True),
    sqlalchemy.Column(AV40_ID, sqlalchemy.Integer),
    sqlalchemy.Column(JOINED, sqlalchemy.Date),
    sqlalchemy.Column(BIRTHDATE, sqlalchemy.Date, nullable=False),
    sqlalchemy.Column(REGISTER_ID, sqlalchemy.String(length=100), unique=True),
    sqlalchemy.Column(EDUCATION_INSTITUTION, sqlalchemy.String(length=100)),
    sqlalchemy.Column(USER_REGISTERED, sqlalchemy.Boolean, nullable=False)
)
