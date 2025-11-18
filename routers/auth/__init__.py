from fastapi import APIRouter

from routers.auth import callback, google, logout, refresh, session, token

router = APIRouter(prefix="/auth")
router.include_router(callback.router, tags=["Auth Callback"])
router.include_router(google.router, tags=["Authorization"])
router.include_router(token.router, tags=["Token Management"])
router.include_router(refresh.router, tags=["Token Refresh"])
router.include_router(session.router, tags=["Session Management"])
router.include_router(logout.router, tags=["Logout"])
