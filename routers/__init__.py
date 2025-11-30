from fastapi import APIRouter

from routers import protected
from routers.auth import router as auth_router
from routers.plaid import routes as plaid_router
from routers.users import router as users_router

router = APIRouter()
router.include_router(auth_router, tags=["Auth"])
router.include_router(protected.router, tags=["Protected Routes"])
router.include_router(plaid_router.router, tags=["Plaid Integration"])
router.include_router(users_router, tags=["Users"])
