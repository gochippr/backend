import logging

from models.auth_user import AuthUser
from database.supabase.user import (
    get_user_by_idp_id_and_provider,
    get_user_by_email,
    create_user,
    update_user_info,
)

logger = logging.getLogger(__name__)


def get_or_create_user_from_auth(auth_user: AuthUser) -> str:
    """
    Business logic to get or create a user from an authenticated user.

    Args:
        auth_user: Authenticated user from JWT token

    Returns:
        ID (string) of the user in the database
    """
    provider = auth_user.provider or "google"

    existing_user = get_user_by_idp_id_and_provider(auth_user.id, provider)

    if existing_user:
        return existing_user.id

    # Create new user
    new_user = create_user(
        idp_id=auth_user.id,
        email=auth_user.email,
        given_name=auth_user.given_name,
        family_name=auth_user.family_name,
        full_name=auth_user.name,
        photo_url=auth_user.picture,
        email_verified=auth_user.email_verified or False,
        provider=provider,
    )

    logger.info(f"Created new user {auth_user.email} with ID: {new_user.id}")
    return new_user.id
