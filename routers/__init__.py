from fastapi import APIRouter

from routers.auth import router as auth_router
from routers import protected

router = APIRouter()
router.include_router(auth_router, tags=["Auth"])
router.include_router(protected.router, tags=["Protected Routes"])
