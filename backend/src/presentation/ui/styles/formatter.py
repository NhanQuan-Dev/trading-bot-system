def format_number(value) -> str:
    try:
        num = float(value)
        formatted = f"{num:.8f}".rstrip('0').rstrip('.')
        return formatted
    except ValueError:
        return str(value)

def format_balance(balance) -> str:
    return format_number(balance)

def format_position(position) -> str:
    return format_number(position)

def format_price(price) -> str:
    return format_number(price)

def format_orderbook_entry(price, quantity) -> str:
    return f"Price: {format_price(price)}, Quantity: {format_number(quantity)}"