from abc import ABC, abstractmethod
from typing import Generic, List, Optional, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar('T')
CreateSchemaType = TypeVar('CreateSchemaType')
UpdateSchemaType = TypeVar('UpdateSchemaType')

class BaseDAO(ABC, Generic[T, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, db: AsyncSession):
        self.db = db
    
    @abstractmethod
    async def create(self, obj_in: CreateSchemaType) -> T:
        pass
    
    @abstractmethod
    async def get(self, id: int) -> Optional[T]:
        pass
    
    @abstractmethod
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        pass
    
    @abstractmethod
    async def update(self, id: int, obj_in: UpdateSchemaType) -> Optional[T]:
        pass
    
    @abstractmethod
    async def delete(self, id: int) -> bool:
        pass