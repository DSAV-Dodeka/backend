from pydantic import BaseModel
import datetime
from datetime import timezone

x = datetime.datetime.now(timezone.utc).timestamp()
print(x)