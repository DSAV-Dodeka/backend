from pydantic import BaseModel, field_validator
from pydantic_core.core_schema import FieldValidationInfo


class AuthRequest(BaseModel):
    response_type: str
    client_id: str
    redirect_uri: str
    state: str
    code_challenge: str
    code_challenge_method: str
    nonce: str
