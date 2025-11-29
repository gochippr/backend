from fastapi import APIRouter

from routers.auth.authorize import google

router = APIRouter(prefix="/authorize")
router.include_router(google.router, tags=["Google Authorization"])
