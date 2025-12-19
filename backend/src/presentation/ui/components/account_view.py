from src.domain.entities.account import Account
from src.application.services.account_service import AccountService
from src.presentation.ui.renderer import Renderer

class AccountView:
    def __init__(self, account_service: AccountService, renderer: Renderer):
        self.account_service = account_service
        self.renderer = renderer

    def display_account_info(self):
        account: Account = self.account_service.get_account_info()
        account_info = {
            "Total Wallet Balance": account.total_wallet_balance,
            "Available Balance": account.available_balance,
            "Balances": account.balances,
        }
        self.renderer.render(account_info)