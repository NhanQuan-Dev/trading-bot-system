from presentation.ui.styles.formatter import format_number
from presentation.ui.styles.colors import Colors
from application.services.market_data_service import MarketDataService

class MarketDataView:
    def __init__(self, market_data_service: MarketDataService):
        self.market_data_service = market_data_service
        self.colors = Colors()

    def render(self):
        mark_prices = self.market_data_service.get_mark_prices()
        self._render_mark_prices(mark_prices)

    def _render_mark_prices(self, mark_prices):
        print(self.colors.BRIGHT_CYAN + "MARK PRICES" + self.colors.RESET)
        print(self.colors.UNDERLINE + f"{'Symbol':<12}{'Price':>22}" + self.colors.RESET)

        for symbol, price in mark_prices.items():
            price_formatted = format_number(price)
            print(f"{self.colors.BRIGHT_WHITE}{symbol:<12}{self.colors.RESET}{self.colors.WHITE}{price_formatted:>22}{self.colors.RESET}")