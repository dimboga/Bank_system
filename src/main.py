from abc import ABC, abstractmethod
import uuid

class AccountFrozenError(Exception):
    pass

class AccountClosedError(Exception):
    pass

class InvalidOperationError(Exception):
    pass

class InsufficientFundsError(Exception):
    pass


class AbstractAccount(ABC):

    def __init__(self, account_id: str, client_personal_data: dict, account_status: str = 'active', protected_balance: float = 0):
        self._account_id = str(account_id)
        self._client_personal_data = client_personal_data
        self.account_status = account_status
        self._protected_balance = protected_balance         #account gets 0 balance when created

    @property
    def allowed_account_statuses_list(self):
        return ["active", "frozen", "closed"]

    @property
    def account_id(self):
        return self._account_id

    @property
    def client_personal_data(self):
        return self._client_personal_data

    @property
    def protected_balance(self):
        """Balance of the client that can't be changed from outside"""
        return self._protected_balance

    @property
    def account_status(self):
        return self._account_status

    @account_status.setter
    def account_status(self, account_status: str):
        """Account status validation"""
        if not account_status in self.allowed_account_statuses_list:
            raise ValueError(f"Incorrect account status! Please choose from {self.allowed_account_statuses_list}")
        else:
            self._account_status = account_status

    @abstractmethod
    def deposit(self, amount: float):
        pass

    @abstractmethod
    def withdraw(self, amount: float):
        pass

    @abstractmethod
    def get_account_info(self):
        pass

class BankAccount(AbstractAccount):

    def __init__(self, client_personal_data: dict, currency: str, account_id = None):
        """If the client doesn't have an account id, it will be generated"""
        self.currency = currency
        if account_id is None:
            generated_id = str(uuid.uuid4())
        else:
            generated_id = str(self.account_id)
        super().__init__(generated_id, client_personal_data)

    def __str__(self):
        return (f"{self._account_id} account info:\n"
              f"Account type: {self.__class__.__name__}\n"
              f"Client name: {self._client_personal_data['name']} {self._client_personal_data['surname']}\n"
              f"Client phone number: ****{self._client_personal_data['phone'][-4:]}"
              f"Account status: {self._account_status}\n"
              f"Account balance: {self._protected_balance} {self._currency}")


    @property
    def bank_account_allowed_currencies_list(self):
        return ["RUB", "USD", "EUR", "KZT", "CNY"]

    @property
    def bank_account_required_personal_data_attributes_list(self):
        return ['name', 'surname', 'phone_number']

    @property
    def account_id(self):
        return self._account_id

    @property
    def currency(self):
        return self._currency

    @currency.setter
    def currency(self, currency: str):
        if not currency in self.bank_account_allowed_currencies_list:
            raise ValueError(f"Incorrect currency! Please choose from {self.bank_account_allowed_currencies_list}")
        else:
            self._currency = currency

    @property
    def client_personal_data(self):
        return self._client_personal_data

    @client_personal_data.setter
    def client_personal_data(self, client_personal_data: dict):
        if not isinstance(client_personal_data, dict):
            raise ValueError("Incorrect format of client personal data! Please, send dictionary")
        for attribute in self.bank_account_required_personal_data_attributes_list:
            if not attribute in client_personal_data:
                raise ValueError(f"Personal data dictionary should contain {attribute} key and value!")
        if len(client_personal_data['phone_number']) < 8:
            raise ValueError("Phone number is too short!")
        self._client_personal_data = client_personal_data


    def deposit(self, amount: float):
        if self.account_status == 'closed':
            raise AccountClosedError("Account is closed. Deposit is not allowed.")
        elif amount <= 0:
            raise InvalidOperationError("Amount must be positive.")
        else:
            self._protected_balance += amount
        print(f"{amount} {self.currency} has been deposited.")

    def withdraw(self, amount: float):
        if self.account_status == 'frozen':
            raise AccountFrozenError("Account is frozen. Withdraw is not allowed.")
        elif amount <= 0:
            raise InvalidOperationError("Amount must be positive.")
        elif self.account_status == 'closed':
            raise AccountClosedError("Account is closed. Withdraw is not allowed.")
        elif self._protected_balance < amount:
            raise InsufficientFundsError("Insufficient funds.")
        else:
            self._protected_balance -= amount
        print(f"{amount} {self._currency} has been withdrawn.")

    def get_account_info(self):
        print(f"{self._account_id} account info:\n"
              f"Account type: {self.__class__.__name__}\n"
              f"Client name: {self._client_personal_data['name']} {self._client_personal_data['surname']}\n"
              f"Client phone number: ****{self._client_personal_data['phone'][-4:]}"
              f"Account status: {self._account_status}\n"
              f"Account balance: {self._protected_balance} {self._currency}")

if __name__ == "__main__":
    print("=== Bank system test (Day 1) ===\n")

    # Successful creation test
    try:
        acc1 = BankAccount(
            client_personal_data={"name": "Joe",
                                  "surname": "Black",
                                  "phone_number": "+1555555555"},
            currency="USD"
        )
        print(f"Account created: {acc1}")
        print(f"Account balance: {acc1.protected_balance} {acc1.currency}")
        acc1.deposit(500)
        print(f"Balance after deposit: {acc1.protected_balance} {acc1.currency}")
    except Exception as e:
        print(f"Unexpected error!: {e}")

    print("\n" + "-"*40 + "\n")

    # 2. Frozen account test
    try:
        acc2 = BankAccount(
            client_personal_data={"name": "Petrov"},
            protected_balance=5000.0,
            account_status="frozen",
            currency="USD"
        )
        print(f"ЗАМОРОЖЕННЫЙ СЧЕТ: {acc2}")
        print("Попытка снятия денег...")
        acc2.withdraw(100)
    except AccountFrozenError as e:
        print(f"✅ Успешно перехвачено ожидаемое исключение: {e}")
    except Exception as e:
        print(f"❌ Ошибка! Ожидалось AccountFrozenError, но получили: {type(e).__name__}")

    # И так далее для остальных случаев...
