from dataclasses import dataclass, field
from typing import List

@dataclass
class Balance:
    asset: str
    wallet_balance: float
    cross_wallet_balance: float = 0.0

@dataclass
class Account:
    total_wallet_balance: float
    available_balance: float
    balances: List[Balance] = field(default_factory=list)

    def add_balance(self, asset: str, wallet_balance: float, cross_wallet_balance: float = 0.0):
        self.balances.append(Balance(asset, wallet_balance, cross_wallet_balance))

    def get_balance(self, asset: str) -> float:
        for balance in self.balances:
            if balance.asset == asset:
                return balance.wallet_balance
        return 0.0

    def update_balance(self, asset: str, wallet_balance: float, cross_wallet_balance: float = 0.0):
        for balance in self.balances:
            if balance.asset == asset:
                balance.wallet_balance = wallet_balance
                balance.cross_wallet_balance = cross_wallet_balance
                return
        self.add_balance(asset, wallet_balance, cross_wallet_balance)