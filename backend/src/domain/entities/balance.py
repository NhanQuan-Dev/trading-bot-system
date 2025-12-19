class Balance:
    def __init__(self, asset: str, wallet_balance: float, cross_wallet_balance: float = 0.0):
        self.asset = asset
        self.wallet_balance = wallet_balance
        self.cross_wallet_balance = cross_wallet_balance

    def total_balance(self) -> float:
        return self.wallet_balance + self.cross_wallet_balance

    def __repr__(self):
        return f"Balance(asset={self.asset}, wallet_balance={self.wallet_balance}, cross_wallet_balance={self.cross_wallet_balance})"