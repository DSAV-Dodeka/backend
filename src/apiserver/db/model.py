import sqlalchemy as sqla

# Helps name constraints
convention = {
  "ix": 'ix_%(column_0_label)s',
  "uq": "uq_%(table_name)s_%(column_0_name)s",
  "ck": "ck_%(table_name)s_%(constraint_name)s",
  "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
  "pk": "pk_%(table_name)s"
}

metadata = sqla.MetaData(naming_convention=convention)

USER_TABLE = "users"
USER_INT_ID = "id"
USER_NAME_ID = "id_name"
USER_ID = "user_id"
USER_EMAIL = "email"
PASSWORD = "password_file"
SCOPES = "scope"
compute_text = sqla.text(f"{USER_INT_ID}::varchar(32) || '_' || {USER_NAME_ID}")
users = sqla.Table(
    USER_TABLE,
    metadata,
    # binary int of usp_hex
    sqla.Column("id", sqla.Integer, primary_key=True),
    sqla.Column("id_name", sqla.String, nullable=False),
    sqla.Column(USER_ID, sqla.String(length=150), sqla.Computed(compute_text), unique=True, nullable=False,
                index=True),
    sqla.Column(USER_EMAIL, sqla.String(length=255), unique=True, nullable=False, index=True),
    sqla.Column(PASSWORD, sqla.String(length=500)),
    sqla.Column(SCOPES, sqla.String(length=200), nullable=False)
)

KEY_TABLE = "keys"
KEY_ID = "kid"
KEY_ISSUED = "iat"
KEY_USE = "use"
keys = sqla.Table(
    KEY_TABLE,
    metadata,
    sqla.Column(KEY_ID, sqla.String(length=50), primary_key=True),
    sqla.Column(KEY_ISSUED, sqla.Integer, nullable=False),
    sqla.Column(KEY_USE, sqla.String(length=50), nullable=False),
)

JWK_TABLE = "jwk"
JWK_VALUE = "encrypted_value"
jwk_check_text = sqla.text(f"id = 1")

jwk = sqla.Table(
    JWK_TABLE,
    metadata,
    sqla.Column("id", sqla.Integer, sqla.CheckConstraint(jwk_check_text, name='check_single'), primary_key=True),
    sqla.Column(JWK_VALUE, sqla.String, nullable=False),
)

OPAQUE_SETUP_TABLE = "opaque"
OPAQUE_VALUE = "value"

opaque_setup = sqla.Table(
    OPAQUE_SETUP_TABLE,
    metadata,
    sqla.Column("id", sqla.Integer, primary_key=True),
    sqla.Column(OPAQUE_VALUE, sqla.String(length=300), nullable=False)
)

REFRESH_TOKEN_TABLE = "refreshtokens"
FAMILY_ID = "family_id"
ACCESS_VALUE = "access_value"
ID_TOKEN_VALUE = "id_token_value"
EXPIRATION = "exp"
NONCE = "nonce"
ISSUED_AT = "iat"
refreshtokens = sqla.Table(
    REFRESH_TOKEN_TABLE,
    metadata,
    sqla.Column("id", sqla.Integer, primary_key=True),
    sqla.Column(USER_ID, sqla.String(length=150), sqla.ForeignKey(f"{USER_TABLE}.{USER_ID}",
                                                                  ondelete="CASCADE"),
                nullable=False),
    sqla.Column(FAMILY_ID, sqla.String(length=200), nullable=False),
    sqla.Column(ACCESS_VALUE, sqla.String(length=1000), nullable=False),
    sqla.Column(ID_TOKEN_VALUE, sqla.String(length=1000), nullable=False),
    sqla.Column(EXPIRATION, sqla.Integer, nullable=False),
    sqla.Column(ISSUED_AT, sqla.Integer, nullable=False),
    sqla.Column(NONCE, sqla.String(length=200))
)

SIGNEDUP_TABLE = "signedup"
SU_FIRSTNAME = "firstname"
SU_LASTNAME = "lastname"
SU_PHONE = "phone"
SU_EMAIL = "email"
SU_CONFIRMED = "confirmed"
signedup = sqla.Table(
    SIGNEDUP_TABLE,
    metadata,
    sqla.Column(SU_FIRSTNAME, sqla.String(length=100), nullable=False),
    sqla.Column(SU_LASTNAME, sqla.String(length=100), nullable=False),
    sqla.Column(SU_PHONE, sqla.String(length=15), nullable=False),
    sqla.Column(SU_EMAIL, sqla.String(length=100), primary_key=True),
    sqla.Column(SU_CONFIRMED, sqla.Boolean, nullable=False),
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
userdata = sqla.Table(
    USERDATA_TABLE,
    metadata,
    sqla.Column(USER_ID, sqla.String(length=150),
                sqla.ForeignKey(f"{USER_TABLE}.{USER_ID}", ondelete="CASCADE"),
                primary_key=True),
    sqla.Column(UD_ACTIVE, sqla.Boolean, nullable=False),
    sqla.Column(UD_FIRSTNAME, sqla.String(length=100), nullable=False),
    sqla.Column(UD_LASTNAME, sqla.String(length=100), nullable=False),
    sqla.Column(UD_CALLNAME, sqla.String(length=100)),
    sqla.Column(UD_PHONE, sqla.String(length=15)),
    sqla.Column(UD_EMAIL, sqla.String(length=255), sqla.ForeignKey(f"{USER_TABLE}.{USER_EMAIL}",
                                                                   ondelete="CASCADE", onupdate="CASCADE"),
                unique=True, nullable=False),
    sqla.Column(AV40_ID, sqla.Integer),
    sqla.Column(JOINED, sqla.Date),
    sqla.Column(BIRTHDATE, sqla.Date, nullable=False),
    sqla.Column(REGISTER_ID, sqla.String(length=100), unique=True),
    sqla.Column(EDUCATION_INSTITUTION, sqla.String(length=100)),
    sqla.Column(USER_REGISTERED, sqla.Boolean, nullable=False)
)
