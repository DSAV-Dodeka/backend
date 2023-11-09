from datetime import date
from typing import Optional, Literal, List

from pydantic import field_validator, BaseModel, TypeAdapter, Field, AliasChoices

from auth.core.model import AccessTokenBase as AuthAccessToken
from auth.data.relational.entities import User as AuthUser


class User(AuthUser):
    # Set by the database
    id: int = -1
    id_name: str
    # Computed in the database
    user_id: str = ""
    scope: str = "member"


class Key(BaseModel):
    id: int
    algorithm: str
    public: str
    private: str
    public_format: str
    public_encoding: str
    private_format: str
    private_encoding: str


class AccessToken(AuthAccessToken):
    iat: int
    exp: int


class IdInfo(BaseModel):
    email: str
    name: str
    given_name: str
    family_name: str
    nickname: str
    preferred_username: str
    birthdate: str


class SignedUp(BaseModel):
    firstname: str
    lastname: str
    email: str
    phone: str
    confirmed: bool = False


class UserData(BaseModel):
    user_id: str
    active: bool
    firstname: str
    lastname: str
    callname: str = ""
    email: str
    phone: str
    av40id: int
    joined: date
    eduinstitution: str = ""
    birthdate: date = date.min
    registerid: str = ""
    registered: bool
    showage: bool

    # Coerces null in database to false
    @field_validator("showage")
    def coerce_showage(cls, value: Optional[bool]) -> bool:
        if value is None:
            return False
        else:
            return value


class ScopeData(BaseModel):
    scope: str


class BirthdayData(BaseModel):
    firstname: str
    lastname: str
    birthdate: date = date.min


class RawUserScopeData(BaseModel):
    firstname: str
    lastname: str
    user_id: str
    scope: str


class UserScopeData(BaseModel):
    name: str
    user_id: str
    scope: list[str]


class JWKSRow(BaseModel):
    id: int
    encrypted_value: str


class JWK(BaseModel):
    """Parameters are as standardized in the IANA JOSE registry (https://www.iana.org/assignments/jose/jose.xhtml)"""

    kty: Literal["OKP", "oct"]
    use: Literal["sig", "enc"]
    alg: Literal["EdDSA", "A256GCM"]
    kid: str
    crv: Optional[Literal["Ed448"]] = None
    k: Optional[str] = None  # symmetric key base64url bytes
    x: Optional[str] = None  # public asymmetric key base64url bytes
    d: Optional[str] = None  # private asymmetric key base64url bytes


class JWKPublicEdDSA(JWK):
    kty: Literal["OKP"]
    use: Literal["sig"]
    alg: Literal["EdDSA"]
    kid: str
    crv: Literal["Ed448"]
    x: str  # public asymmetric key base64url bytes


class JWKPairEdDSA(JWKPublicEdDSA):
    d: str  # private asymmetric key base64url bytes


class JWKSymmetricA256GCM(JWK):
    kty: Literal["oct"]
    use: Literal["enc"]
    alg: Literal["A256GCM"]
    kid: str
    k: str  # symmetric key base64url bytes


class JWKSet(BaseModel):
    keys: list[JWK]


class PEMKey(BaseModel):
    kid: str
    public: str  # PEM encoded X509PKCS#1 as unicode


class AuthRequest(BaseModel):
    response_type: str
    client_id: str
    redirect_uri: str
    state: str
    code_challenge: str
    code_challenge_method: str
    nonce: str


class SavedState(BaseModel):
    user_id: str
    user_email: str
    scope: str
    state: str


class UpdateEmailState(BaseModel):
    user_id: str
    old_email: str
    flow_id: str
    new_email: str


class Signup(BaseModel):
    firstname: str
    lastname: str
    email: str
    phone: str


class Classification(BaseModel):
    type: str
    start_date: date
    end_date: date
    hidden_date: date
    last_updated: date


class ClassPoints(BaseModel):
    user_id: str
    classification_id: str
    true_points: str
    display_points: str


class UserID(BaseModel):
    user_id: str


class UserNames(BaseModel):
    user_id: str
    firstname: str
    lastname: str


class ClassView(BaseModel):
    classification_id: int
    last_updated: date
    start_date: date
    hidden_date: date


class UserPointsNames(BaseModel):
    user_id: str
    firstname: str
    lastname: str
    # In the database it is 'display_points'/'true_points', but we want to export as points
    # It might also just be points in the event_points table
    points: int = Field(
        validation_alias=AliasChoices("display_points", "true_points", "points")
    )


UserPointsNamesList = TypeAdapter(List[UserPointsNames])


# class PointsData(BaseModel):
#     points: int


class StoredKeyKID(BaseModel):
    kid: str


class ClassEvent(BaseModel):
    event_id: str
    category: str
    description: str
    date: date


EventsList = TypeAdapter(List[ClassEvent])


class UserEvent(BaseModel):
    event_id: str
    category: str
    description: str
    date: date
    points: int


UserEventsList = TypeAdapter(List[UserEvent])


class UserPoints(BaseModel):
    user_id: str
    points: int


class NewEvent(BaseModel):
    users: list[UserPoints]
    class_type: Literal["points", "training"]
    date: date
    event_id: str
    category: str
    description: str = ""
