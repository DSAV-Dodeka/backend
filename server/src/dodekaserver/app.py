from typing import Optional

from fastapi import FastAPI

from databases import Database

from dodekaserver.db.settings import DB_URL
import dodekaserver.data as data

app = FastAPI()

database = Database(DB_URL)


@app.on_event("startup")
async def startup():
    await database.connect()


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


@app.get("/users/{user_id}")
async def get_user(user_id: int):
    user = await data.get_user_row(database, user_id)

    return {"Hello": str(user)}


@app.get("/")
async def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
async def read_item(item_id: int, q: Optional[str] = None):
    return {"item_id": item_id, "q": q}
