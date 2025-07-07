from fastapi import APIRouter

from routers.auth import callback, google, refresh, token

router = APIRouter(prefix="/auth")
router.include_router(callback.router, tags=["Auth Callback"])
router.include_router(google.router, tags=["Authorization"])
router.include_router(token.router, tags=["Token Management"])
router.include_router(refresh.router, tags=["Token Refresh"])
