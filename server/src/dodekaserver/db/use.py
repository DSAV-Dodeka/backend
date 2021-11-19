from databases import Database


async def retrieve_by_id(db: Database, table: str, id_int: int):
    query = f"SELECT * FROM {table} where id = :id"
    record = await db.fetch_one(query, values={"id": id_int})
    return dict(record)
