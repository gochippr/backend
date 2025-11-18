from fastapi import APIRouter

from routers.auth import callback as auth_callback
from routers.auth.authorize import router as authorize_router

router = APIRouter(prefix="/auth")
router.include_router(auth_callback.router, tags=["Auth Callback"])
router.include_router(authorize_router, tags=["Authorization"])
