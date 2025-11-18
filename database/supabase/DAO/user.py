import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database.supabase.dao.base import BaseDAO
from models.user import User
from schemas.user import UserCreate, UserUpdate

logger = logging.getLogger(__name__)


class UserDAO(BaseDAO[User, UserCreate, UserUpdate]):
    def __init__(self, db: AsyncSession):
        super().__init__(db)
    
    async def create(self, obj_in: UserCreate) -> User:
        """Create a new user."""
        db_user = User(**obj_in.model_dump())
        
        self.db.add(db_user)
        try:
            await self.db.commit()
            await self.db.refresh(db_user)
            logger.info(f"User created: {obj_in.email}")
            return db_user
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Error creating user: {e}")
            raise ValueError("User with this email or ID already exists")
    
    async def get(self, id: str) -> Optional[User]:  # type: ignore
        """Get a user by ID (Google sub)."""
        try:
            result = await self.db.execute(
                select(User).where(User.id == id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get a user by email."""
        try:
            result = await self.db.execute(
                select(User).where(User.email == email)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            return None
    
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get all users with pagination."""
        try:
            result = await self.db.execute(
                select(User).offset(skip).limit(limit)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []
    
    async def update(self, id: str, obj_in: UserUpdate) -> Optional[User]:  # type: ignore
        """Update a user."""
        try:
            db_user = await self.get(id)
            if not db_user:
                return None
            
            update_data = obj_in.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(db_user, field, value)
            
            # Always update the updated_at timestamp
            setattr(db_user, 'updated_at', datetime.utcnow())
            
            await self.db.commit()
            await self.db.refresh(db_user)
            logger.info(f"User updated: {id}")
            return db_user
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating user: {e}")
            return None
    
    async def delete(self, id: str) -> bool:  # type: ignore
        """Permanently delete a user."""
        try:
            db_user = await self.get(id)
            if not db_user:
                return False
            
            await self.db.delete(db_user)
            await self.db.commit()
            logger.info(f"User permanently deleted: {id}")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting user: {e}")
            return False
    
    async def create_or_update(self, user_data: dict) -> Optional[User]:
        """
        Create a new user or update existing user information.
        Uses upsert logic to handle both cases.
        
        Args:
            user_data: Dictionary containing user information from OAuth provider
                Required fields: id (sub), email, name
                Optional fields: picture, given_name, family_name, email_verified, provider
        
        Returns:
            The created or updated user record, or None if operation failed
        """
        try:
            # Prepare user data with defaults
            user_id = user_data.get("sub") or user_data.get("id")
            if not user_id:
                raise ValueError("User ID (sub) is required")
                
            email = user_data.get("email")
            if not email:
                raise ValueError("Email is required")
                
            name = user_data.get("name")
            if not name:
                raise ValueError("Name is required")
            
            # Check if user exists
            existing_user = await self.get(user_id)
            
            if existing_user:
                # Update existing user
                update_data = UserUpdate(
                    email=email,
                    name=name,
                    picture=user_data.get("picture"),
                    given_name=user_data.get("given_name"),
                    family_name=user_data.get("family_name"),
                    email_verified=user_data.get("email_verified", False),
                    provider=user_data.get("provider", "google")
                )
                return await self.update(user_id, update_data)
            else:
                # Create new user
                create_data = UserCreate(
                    id=user_id,
                    email=email,
                    name=name,
                    picture=user_data.get("picture"),
                    given_name=user_data.get("given_name"),
                    family_name=user_data.get("family_name"),
                    email_verified=user_data.get("email_verified", False),
                    provider=user_data.get("provider", "google")
                )
                return await self.create(create_data)
                
        except Exception as e:
            logger.error(f"Error creating/updating user: {e}")
            return None


# Convenience functions for backwards compatibility
async def get_user_by_id(user_id: str, db: AsyncSession) -> Optional[dict]:
    """Get a user by their ID (Google sub) - backwards compatibility function"""
    try:
        user_dao = UserDAO(db)
        user = await user_dao.get(user_id)
        return user.__dict__ if user else None
    except Exception as e:
        logger.error(f"Error getting user by ID: {e}")
        return None


async def get_user_by_email(email: str, db: AsyncSession) -> Optional[dict]:
    """Get a user by their email - backwards compatibility function"""
    try:
        user_dao = UserDAO(db)
        user = await user_dao.get_by_email(email)
        return user.__dict__ if user else None
    except Exception as e:
        logger.error(f"Error getting user by email: {e}")
        return None


async def create_or_update_user(user_data: dict, db: AsyncSession) -> Optional[dict]:
    """Create or update user - backwards compatibility function"""
    try:
        user_dao = UserDAO(db)
        user = await user_dao.create_or_update(user_data)
        return user.__dict__ if user else None
    except Exception as e:
        logger.error(f"Error creating/updating user: {e}")
        return None


async def delete_user(user_id: str, db: AsyncSession) -> bool:
    """Delete user - backwards compatibility function"""
    try:
        user_dao = UserDAO(db)
        return await user_dao.delete(user_id)
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        return False