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


@app.get("/user_write/{user_id}")
async def write_user(user_id: int, name: Optional[str], last_name: Optional[str]):
    user_row = {"id": user_id, "name": name, "last_name": last_name}
    rc = await data.upsert_user_row(database, user_row)
    return {"Response": "Ok"}


@app.get("/")
async def read_root():
    return {"Hallo": "Atleten"}
