from pydantic import BaseModel


class KvAddress(BaseModel):
    host: str
    port: int
    db_n: int


KV_ADDRESS = KvAddress(host='localhost', port='6379', db_n=0)
