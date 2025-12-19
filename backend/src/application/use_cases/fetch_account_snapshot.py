from src.domain.repositories.account_repository import AccountRepository
from src.shared.exceptions.api_exception import APIException

class FetchAccountSnapshot:
    def __init__(self, account_repository: AccountRepository):
        self.account_repository = account_repository

    def execute(self):
        try:
            account_data = self.account_repository.get_account_snapshot()
            return account_data
        except Exception as e:
            raise APIException("Failed to fetch account snapshot") from e