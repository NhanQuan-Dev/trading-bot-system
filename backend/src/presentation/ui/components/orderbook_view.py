from src.domain.entities.orderbook import OrderBook
from src.application.services.orderbook_service import OrderBookService

class OrderBookView:
    def __init__(self, orderbook_service: OrderBookService):
        self.orderbook_service = orderbook_service

    def display_orderbook(self, symbol: str):
        orderbook: OrderBook = self.orderbook_service.get_orderbook(symbol)
        self.render_orderbook(orderbook)

    def render_orderbook(self, orderbook: OrderBook):
        print(f"Order Book for {orderbook.symbol}:")
        print("Asks:")
        for ask in orderbook.asks:
            print(f"Price: {ask.price}, Quantity: {ask.quantity}")
        print("Bids:")
        for bid in orderbook.bids:
            print(f"Price: {bid.price}, Quantity: {bid.quantity}")