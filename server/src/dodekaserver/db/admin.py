from databases import Database

from dodekaserver.db.use import execute_queries_unsafe


async def remove_test_dbs(admin_db: Database):
    query_databases = "SELECT datname FROM pg_database"
    fetch_res = await admin_db.fetch_all(query_databases)
    test_dbs = [dict(res)['datname'] for res in fetch_res if 'test' in dict(res)['datname']]
    queries = [f"DROP DATABASE IF EXISTS {test_db}" for test_db in test_dbs]
    await execute_queries_unsafe(admin_db, queries)
