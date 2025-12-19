class Renderer:
    def __init__(self):
        self.width = 70

    def clear_screen(self):
        print("\033[2J\033[H", end='')

    def render_mark_prices(self, mark_prices):
        print(self.top_border())
        title = "REAL-TIME FUTURES MONITOR"
        print(self.center_text(title))
        print(self.mid_border())
        
        print(self.pad_line("[MARK PRICES]"))
        print(self.thin_line())
        header = f"{'Symbol':<12}{'Price':>22}"
        print(self.pad_line(header))
        
        for sym, price in mark_prices.items():
            line = f"{sym:<12}{price:>22}"
            print(self.pad_line(line))
        print(self.mid_border())

    def render_balances(self, total_wallet, available, balances):
        print(self.pad_line("[ACCOUNT BALANCES]"))
        print(self.thin_line())
        
        total_str = f"Total: {total_wallet} | Free: {available}"
        print(self.pad_line(total_str))
        print(self.thin_line())
        header = f"{'Asset':<8}{'Wallet':>20}{'Cross':>20}"
        print(self.pad_line(header))
        
        for b in balances:
            line = f"{b['a']:<8}{b['wb']:>20}{b.get('cw', '-'):>20}"
            print(self.pad_line(line))
        print(self.mid_border())

    def render_positions(self, positions):
        print(self.pad_line("[OPEN POSITIONS]"))
        print(self.thin_line())
        header = f"{'Symbol':<10}{'Side':<6}{'Qty':>10}{'Entry':>12}{'uPnL':>12}"
        print(self.pad_line(header))

        for key, pos in positions.items():
            line = f"{key[0]:<10}{pos['positionSide']:<6}{pos['positionAmt']:>10}{pos['entryPrice']:>12}{pos['unrealizedPnL']:>12}"
            print(self.pad_line(line))
        print(self.mid_border())

    def render_orderbook(self, orderbook):
        print(self.pad_line("[ORDERBOOK]"))
        print(self.thin_line())
        header = f"{'Side':<8}{'Price':>18}{'Quantity':>18}"
        print(self.pad_line(header))

        # Render asks (sell orders)
        if "asks" in orderbook:
            for price, qty in orderbook["asks"][:5]:
                line = f"{'ASK':<8}{price:>18}{qty:>18}"
                print(self.pad_line(line))
        
        # Render bids (buy orders)
        if "bids" in orderbook:
            for price, qty in orderbook["bids"][:5]:
                line = f"{'BID':<8}{price:>18}{qty:>18}"
                print(self.pad_line(line))
        print(self.mid_border())

    def top_border(self):
        return "╔" + "═" * (self.width - 2) + "╗"

    def mid_border(self):
        return "╠" + "═" * (self.width - 2) + "╣"

    def pad_line(self, content):
        return f"║ {content} " + " " * (self.width - len(content) - 4) + "║"

    def thin_line(self):
        return self.pad_line("-" * (self.width - 4))

    def center_text(self, text):
        total_pad = self.width - len(text) - 2
        left_pad = total_pad // 2
        right_pad = total_pad - left_pad
        return f"║{' ' * left_pad}{text}{' ' * right_pad}║"