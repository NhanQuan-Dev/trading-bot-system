import logging
import uuid
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import UserModel

logger = logging.getLogger(__name__)

DEFAULT_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

async def seed_users(session: AsyncSession):
    """Seed initial users."""
    try:
        # Check if default user exists
        result = await session.execute(
            select(UserModel).where(UserModel.id == DEFAULT_USER_ID)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            logger.info(f"Seeding default user {DEFAULT_USER_ID}")
            user = UserModel(
                id=DEFAULT_USER_ID,
                email="dev@example.com",
                password_hash="hashed_secret",  # Insecure but fine for dev/seed
                is_active=True,
                full_name="Developer"
            )
            session.add(user)
            await session.commit()
        else:
            logger.info("Default user already exists")
            
    except Exception as e:
        logger.error(f"Error seeding users: {e}")
        raise
