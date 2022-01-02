from pydantic import BaseModel
import datetime
from datetime import timezone

# x = datetime.datetime.now(timezone.utc).timestamp()
# print(x)
i = "d764baa92d6724624740b140a7b592668e011680cdb1d47f12befeb17183c53e2b6516cac766c2b82a504fda37751fd6c188d2ce646420d6bf196bcfbb9bb646"
z = bytes.fromhex(i)
print(z.decode("utf-8"))