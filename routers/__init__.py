from fastapi import APIRouter

from routers import protected
from routers.auth import router as auth_router
from routers.plaid import routes as plaid_router
from routers import plaid_sync as plaid_sync_router
from routers.users import router as users_router
from routers.transactions import router as transactions_router
from routers.accounts import router as accounts_router
from routers.friends import router as friends_router
from routers.splits import router as splits_router
from routers.ai import router as ai_router
from routers.budget_run import router as budget_run_router

router = APIRouter()
router.include_router(auth_router, tags=["Auth"])
router.include_router(protected.router, tags=["Protected Routes"])
router.include_router(plaid_router.router, tags=["Plaid Integration"])
router.include_router(users_router, tags=["Users"])
router.include_router(plaid_sync_router.router, tags=["Plaid Sync"])
router.include_router(transactions_router, tags=["Transactions"])
router.include_router(accounts_router, tags=["Accounts"])
router.include_router(friends_router, tags=["Friends"])
router.include_router(splits_router, tags=["Splits"])
router.include_router(ai_router, tags=["AI"])
router.include_router(budget_run_router, tags=["Budget Run"])
