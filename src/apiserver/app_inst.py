from apiserver.app_def import create_app
from apiserver.app_lifespan import lifespan


# Running FastAPI relies on the fact the app is created at module top-level
# Seperating the logic in a function also allows it to be called elsewhere, like tests
apiserver_app = create_app(lifespan)
