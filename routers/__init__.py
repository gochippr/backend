from fastapi import APIRouter

from routers.auth import router as auth_router

router = APIRouter()
router.include_router(auth_router, tags=["Auth"])
