from apiserver.app.routers.auth import auth_router
from apiserver.app.routers.onboard import onboard_router
from apiserver.app.routers.update import update_router

__all__ = ["auth_router", "onboard_router", "update_router"]
