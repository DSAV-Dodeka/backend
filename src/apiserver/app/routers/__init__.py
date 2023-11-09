from apiserver.app.routers.auth import router as auth_router
from apiserver.app.routers.onboard import onboard_router
from apiserver.app.routers.update import update_router
from apiserver.app.routers.members import members_router
from apiserver.app.routers.admin import admin_router

__all__ = [
    "auth_router",
    "onboard_router",
    "update_router",
    "members_router",
    "admin_router",
]
