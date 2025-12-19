def format_number(value) -> str:
    """Format số: loại bỏ số 0 thừa phía sau
    5000.000 -> 5000
    5000.200 -> 5000.2
    0.00100 -> 0.001
    """
    try:
        num = float(value)
        formatted = f"{num:.8f}".rstrip('0').rstrip('.')
        return formatted
    except ValueError:
        return str(value)