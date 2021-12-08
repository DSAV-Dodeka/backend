import asyncio

from databases import Database
from dodekaserver.db.settings import DB_URL


# async def upsert_by_id(db: Database, table: str, row: dict):
#     r_id = row.pop('id')
#     row_keys = ', '.join(row.keys())
#     row_values = ', '.join([f"'{val}'" for val in row.values()])
#     set_rows = []
#     for key, value in row.items():
#         set_rows.append(f"{key} = '{value}'")
#     set_rows = ', '.join(set_rows)
#     query = f"INSERT INTO {table}(id, {row_keys}) VALUES ({r_id}, {row_values})" \
#             f"ON CONFLICT (id) DO UPDATE SET" \
#             f"  {set_rows};"
#     return await db.execute(query=query)


async def insert(db: Database):
    row = {"id": 22, "last_name": "aas"}
    row_keys = []
    row_keys_vars = []
    row_keys_set = []
    for key in row.keys():
        row_keys.append(key)
        row_keys_vars.append(f':{key}')
        row_keys_set.append(f'{key} = :{key}')
    row_keys = ', '.join(row_keys)
    row_keys_vars = ', '.join(row_keys_vars)
    row_keys_set = ', '.join(row_keys_set)
    query = f"INSERT INTO users ({row_keys}) VALUES ({row_keys_vars}) ON CONFLICT (id) DO UPDATE SET {row_keys_set};"
    await db.execute(query=query, values=row)

async def main():
    db = Database(DB_URL)
    await db.connect()

    # await upsert_by_id(db, "users", {})
    await insert(db)


if __name__ == '__main__':
    asyncio.run(main())
