import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database.supabase.dao.base import BaseDAO
from models.user_plaid_item import UserPlaidItem
from schemas.user_plaid_item import UserPlaidItemCreate, UserPlaidItemUpdate

logger = logging.getLogger(__name__)

class UserPlaidItemDAO(BaseDAO[UserPlaidItem, UserPlaidItemCreate, UserPlaidItemUpdate]):
    def __init__(self, db: AsyncSession):
        super().__init__(db)
    
    async def create(self, obj_in: UserPlaidItemCreate) -> UserPlaidItem:
        """Create a new Plaid item for a user."""
        db_item = UserPlaidItem(**obj_in.model_dump())
        
        self.db.add(db_item)
        try:
            await self.db.commit()
            await self.db.refresh(db_item)
            logger.info(f"Plaid item created for user {obj_in.user_id}: {obj_in.item_id}")
            return db_item
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Error creating Plaid item: {e}")
            raise ValueError("Plaid item with this item_id already exists")
    
    async def get(self, id: int) -> Optional[UserPlaidItem]:
        """Get a Plaid item by ID."""
        try:
            result = await self.db.execute(
                select(UserPlaidItem).where(UserPlaidItem.id == id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting Plaid item: {e}")
            return None
    
    async def get_by_item_id(self, item_id: str) -> Optional[UserPlaidItem]:
        """Get a Plaid item by Plaid's item_id."""
        try:
            result = await self.db.execute(
                select(UserPlaidItem).where(UserPlaidItem.item_id == item_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting Plaid item by item_id: {e}")
            return None
    
    async def get_user_items(self, user_id: str, active_only: bool = True) -> List[UserPlaidItem]:
        """Get all Plaid items for a user."""
        try:
            query = select(UserPlaidItem).where(UserPlaidItem.user_id == user_id)
            
            if active_only:
                query = query.where(UserPlaidItem.is_active == True)
            
            result = await self.db.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error getting user Plaid items: {e}")
            return []
    
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[UserPlaidItem]:
        """Get all Plaid items with pagination."""
        try:
            result = await self.db.execute(
                select(UserPlaidItem).offset(skip).limit(limit)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error getting all Plaid items: {e}")
            return []
    
    async def update(self, id: int, obj_in: UserPlaidItemUpdate) -> Optional[UserPlaidItem]:
        """Update a Plaid item."""
        try:
            db_item = await self.get(id)
            if not db_item:
                return None
            
            update_data = obj_in.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(db_item, field, value)
            
            # Always update the updated_at timestamp
            setattr(db_item, 'updated_at', datetime.utcnow())
            
            await self.db.commit()
            await self.db.refresh(db_item)
            logger.info(f"Plaid item updated: {id}")
            return db_item
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating Plaid item: {e}")
            return None
    
    async def delete(self, id: int) -> bool:
        """Permanently delete a Plaid item."""
        try:
            db_item = await self.get(id)
            if not db_item:
                return False
            
            await self.db.delete(db_item)
            await self.db.commit()
            logger.info(f"Plaid item permanently deleted: {id}")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting Plaid item: {e}")
            return False
    
    async def soft_delete(self, user_id: str, item_id: str) -> bool:
        """Soft delete a Plaid item by setting is_active to False."""
        try:
            result = await self.db.execute(
                select(UserPlaidItem).where(
                    and_(
                        UserPlaidItem.user_id == user_id,
                        UserPlaidItem.item_id == item_id
                    )
                )
            )
            db_item = result.scalar_one_or_none()
            
            if not db_item:
                return False
            
            setattr(db_item, 'is_active', False)
            setattr(db_item, 'updated_at', datetime.utcnow())
            
            await self.db.commit()
            logger.info(f"Plaid item soft deleted: {item_id} for user {user_id}")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error soft deleting Plaid item: {e}")
            return False
    
    async def get_encrypted_token(self, user_id: str, item_id: str) -> Optional[str]:
        """Get encrypted access token for a specific item."""
        try:
            result = await self.db.execute(
                select(UserPlaidItem.access_token_encrypted).where(
                    and_(
                        UserPlaidItem.user_id == user_id,
                        UserPlaidItem.item_id == item_id,
                        UserPlaidItem.is_active == True
                    )
                )
            )
            token = result.scalar_one_or_none()
            return token
        except Exception as e:
            logger.error(f"Error getting encrypted token: {e}")
            return None
    
    async def update_sync_cursor(self, item_id: str, cursor: str) -> bool:
        """Update the sync cursor for incremental updates."""
        try:
            result = await self.db.execute(
                select(UserPlaidItem).where(UserPlaidItem.item_id == item_id)
            )
            db_item = result.scalar_one_or_none()
            
            if not db_item:
                return False
            
            setattr(db_item, 'cursor', cursor)
            setattr(db_item, 'last_sync', datetime.utcnow())
            setattr(db_item, 'updated_at', datetime.utcnow())
            
            await self.db.commit()
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating sync cursor: {e}")
            return False