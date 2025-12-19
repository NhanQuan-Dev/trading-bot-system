"""Get order by ID use case."""
import uuid

from ....domain.order import Order
from ....interfaces.repositories.order_repository import IOrderRepository
from ....shared.exceptions.business import NotFoundError


class GetOrderByIdUseCase:
    """Use case for retrieving a specific order by ID."""
    
    def __init__(self, order_repository: IOrderRepository):
        self._order_repository = order_repository
    
    async def execute(self, user_id: uuid.UUID, order_id: uuid.UUID) -> Order:
        """Execute get order by ID use case."""
        
        order = await self._order_repository.get_by_id(order_id, user_id)
        
        if not order:
            raise NotFoundError(f"Order {order_id} not found")
        
        return order
