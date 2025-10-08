import logging
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, status

from database.supabase import friendship as friendship_repo
from database.supabase import user as user_repo
from database.supabase.friendship import Friendship
from database.supabase.user import User
from models.auth_user import AuthUser
from models.friend import (
    FriendListResponse,
    FriendRelationship,
    FriendRequestCreate,
    FriendRequestListResponse,
    FriendUser,
)
from utils.middlewares.auth_user import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/friends", tags=["Friends"])


def _resolve_friend_user(user: User) -> FriendUser:
    name = (
        user.full_name
        or (" ".join(filter(None, [user.given_name, user.family_name])) or None)
        or user.email.split("@")[0]
    )
    return FriendUser(
        id=user.id,
        email=user.email,
        name=name,
        photo_url=user.photo_url,
    )


def _other_party(friendship: Friendship, current_user_id: str) -> str:
    return (
        friendship.friend_user_id
        if friendship.user_id == current_user_id
        else friendship.user_id
    )


def _hydrate_friendships(
    friendships: List[Friendship],
    current_user: AuthUser,
) -> List[FriendRelationship]:
    users_cache: Dict[str, FriendUser] = {}
    results: List[FriendRelationship] = []

    for relation in friendships:
        other_user_id = _other_party(relation, current_user.id)

        if other_user_id not in users_cache:
            user_record = user_repo.get_user_by_id(other_user_id)
            if not user_record:
                logger.warning("Friend user %s not found", other_user_id)
                continue
            users_cache[other_user_id] = _resolve_friend_user(user_record)

        friend_user = users_cache[other_user_id]
        is_incoming = (
            relation.status == "pending"
            and relation.initiator_user_id != current_user.id
        )
        is_outgoing = (
            relation.status == "pending"
            and relation.initiator_user_id == current_user.id
        )

        results.append(
            FriendRelationship(
                friend=friend_user,
                status=relation.status,
                initiator_user_id=relation.initiator_user_id,
                created_at=relation.created_at,
                updated_at=relation.updated_at,
                is_incoming_request=is_incoming,
                is_outgoing_request=is_outgoing,
            )
        )

    return results


@router.get("", response_model=FriendListResponse)
async def list_friends(
    current_user: AuthUser = Depends(get_current_user),
) -> FriendListResponse:
    friendships = friendship_repo.list_friends_for_user(
        current_user.id, only_accepted=True
    )
    hydrated = _hydrate_friendships(friendships, current_user)
    return FriendListResponse(friends=hydrated)


@router.get("/requests", response_model=FriendRequestListResponse)
async def list_friend_requests(
    current_user: AuthUser = Depends(get_current_user),
) -> FriendRequestListResponse:
    pending = friendship_repo.list_friendships_by_status(current_user.id, "pending")
    hydrated = _hydrate_friendships(pending, current_user)
    incoming = [r for r in hydrated if r.is_incoming_request]
    outgoing = [r for r in hydrated if r.is_outgoing_request]
    return FriendRequestListResponse(incoming=incoming, outgoing=outgoing)


@router.post("/requests", response_model=FriendRelationship, status_code=status.HTTP_201_CREATED)
async def send_friend_request(
    payload: FriendRequestCreate,
    current_user: AuthUser = Depends(get_current_user),
) -> FriendRelationship:
    target_email = payload.email.lower()
    target_user = user_repo.get_user_by_email(target_email)
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if target_user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot add yourself as a friend")

    existing = friendship_repo.get_friendship(current_user.id, target_user.id, include_deleted=True)
    if existing and existing.deleted_at is None:
        if existing.status == "accepted":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are already friends")
        if existing.status == "pending":
            if existing.initiator_user_id == current_user.id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Friend request already sent")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Friend request already pending from this user",
            )
        if existing.status == "blocked":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Friendship is blocked")

    friendship = friendship_repo.create_friendship(
        current_user.id,
        target_user.id,
        initiator_user_id=current_user.id,
        status="pending",
    )

    hydrated = _hydrate_friendships([friendship], current_user)
    if not hydrated:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create friend request")

    return hydrated[0]


@router.post("/requests/{friend_user_id}/accept", response_model=FriendRelationship)
async def accept_friend_request(
    friend_user_id: str,
    current_user: AuthUser = Depends(get_current_user),
) -> FriendRelationship:
    friendship = friendship_repo.get_friendship(current_user.id, friend_user_id)
    if not friendship or friendship.status != "pending":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Friend request not found")

    if friendship.initiator_user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot accept a request you sent")

    updated = friendship_repo.update_friendship_status(current_user.id, friend_user_id, "accepted")
    hydrated = _hydrate_friendships([updated], current_user)
    if not hydrated:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to load friend data")
    return hydrated[0]


@router.post("/requests/{friend_user_id}/deny", status_code=status.HTTP_204_NO_CONTENT)
async def deny_friend_request(
    friend_user_id: str,
    current_user: AuthUser = Depends(get_current_user),
) -> None:
    friendship = friendship_repo.get_friendship(current_user.id, friend_user_id)
    if not friendship or friendship.status != "pending":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Friend request not found")

    if friendship.initiator_user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deny a request you sent")

    friendship_repo.delete_friendship(current_user.id, friend_user_id)
