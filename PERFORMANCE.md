What is fast:
- The actual HTTP server, which runs on uvloop. This won't ever be a likely bottleneck
- The direct interface with the database: asyncpg is one of the fastest PostgreSQL adapters around

What is slow:
- The parsing and loading of database data into Python (parsing into Pydantic models)
- Manipulation of database data in Python
- If we return a type directly, meaning FastAPI has to do additional conversion. Using JSONResponse directly is much faster

Most of the latter isn't a problem for simple responses that don't work on many rows. But if many rows are included, it might be worth it to write a parse function for a specific model and return a JSONResponse directly.
