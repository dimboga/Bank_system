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
        self._protected_balance = protected_balance
        print(f"Account {self._account_id} is successfully created!")

    @property
    def allowed_account_statuses_list(self) -> list:
        return ["active", "frozen", "closed"]

    @property
    def account_id(self) -> str:
        """Protected account id attribute"""
        return self._account_id

    @property
    def client_personal_data(self) -> dict:
        """Protected balance attribute"""
        return self._client_personal_data

    @property
    def protected_balance(self) -> float:
        """Balance of the client that can't be changed from outside"""
        return self._protected_balance

    @property
    def account_status(self) -> str:
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

    MINIMAL_PHONE_NUMBER_LENGTH = 8

    BANK_ACCOUNT_ALLOWED_CURRENCIES_LIST = ["RUB", "USD", "EUR", "KZT", "CNY"]

    BANK_ACCOUNT_REQUIRED_PERSONAL_DATA_ATTRIBUTES_LIST = ["name", "surname", "phone_number"]

    PERCENT_FACTOR = 100

    DEFAULT_WITHDRAWAL_COMMISSION_PERCENTAGE = 0.5

    def __init__(self, client_personal_data: dict, currency: str, account_id:str = None, account_status: str = 'active', protected_balance: float = 0):
        """If the client doesn't have an account id, it will be generated"""
        if account_id is None:
            generated_id = str(uuid.uuid4())
        else:
            generated_id = str(account_id)
        super().__init__(generated_id, client_personal_data, account_status, protected_balance)
        if not currency in self.BANK_ACCOUNT_ALLOWED_CURRENCIES_LIST:
            raise ValueError(f"Incorrect currency! Please choose from {self.BANK_ACCOUNT_ALLOWED_CURRENCIES_LIST}")
        else:
            self._currency = currency
        self.client_personal_data = client_personal_data

    def __str__(self):
        return (f"{self._account_id} account info:\n"
              f"Account type: {self.__class__.__name__}\n"
              f"Client name: {self._client_personal_data.get('name', 'N/A')} {self._client_personal_data.get('surname', 'N/A')}\n"
              f"Client phone number: ****{self._client_personal_data.get('phone_number', 'N/A')[-4:]}\n"
              f"Account status: {self._account_status}\n"
              f"Account balance: {self._protected_balance} {self._currency}")

    @property
    def currency(self) -> str:
        """Protected currency attribute"""
        return self._currency

    @property
    def client_personal_data(self) -> dict:
        return self._client_personal_data

    @client_personal_data.setter
    def client_personal_data(self, client_personal_data: dict):
        if not isinstance(client_personal_data, dict):
            raise ValueError("Incorrect format of client personal data! Please, send dictionary")
        for attribute in self.BANK_ACCOUNT_REQUIRED_PERSONAL_DATA_ATTRIBUTES_LIST:
            if not attribute in client_personal_data:
                raise ValueError(f"Personal data dictionary should contain {attribute} key and value!")
        if len(client_personal_data['phone_number']) < self.MINIMAL_PHONE_NUMBER_LENGTH:
            raise ValueError("Phone number is too short!")
        self._client_personal_data = client_personal_data


    def deposit(self, amount: float):
        if self._account_status == 'closed':
            raise AccountClosedError("Account is closed. Deposit is not allowed.")
        elif self._account_status == 'frozen':
            raise AccountFrozenError("Account is frozen. Deposit is not allowed.")
        elif amount <= 0:
            raise InvalidOperationError("Amount must be positive.")
        else:
            self._protected_balance += amount
        print(f"{amount} {self._currency} has been deposited.\n"
              f"Current balance: {self._protected_balance} {self._currency}.")

    def withdraw(self, amount: float):
        if self._account_status == 'closed':
            raise AccountClosedError("Account is closed. Withdraw is not allowed.")
        elif self._account_status == 'frozen':
            raise AccountFrozenError("Account is frozen. Withdraw is not allowed.")
        elif amount <= 0:
            raise InvalidOperationError("Amount must be positive.")
        elif self._protected_balance < amount:
            raise InsufficientFundsError("Insufficient funds.")
        else:
            withdraw_commission = amount * (self.DEFAULT_WITHDRAWAL_COMMISSION_PERCENTAGE / self.PERCENT_FACTOR) #default withdrawal commission is dynamic based on the amount
            self._protected_balance -= (amount + withdraw_commission)
        print(f"{amount} {self._currency} has been withdrawn.\n"
              f"{self.DEFAULT_WITHDRAWAL_COMMISSION_PERCENTAGE}% withdrawal commission has been applied ({withdraw_commission} {self._currency})\n"
              f"Current balance: {self._protected_balance} {self._currency}\n")

    def get_account_info(self):
        return(f"Current balance: {self._protected_balance} {self._currency}\n"
              f"Account is {self._account_status}")


class SavingsAccount(BankAccount):

    THRESHOLD_MIN_BALANCE_AMOUNT = {
        "RUB": 10000.0,
        "USD": 100.0,
        "EUR": 100.0,
        "KZT": 50000.0,
        "CNY": 1000.0
    }

    THRESHOLD_MONTHLY_INTEREST_RATES = {
        "RUB": 1.33,
        "USD": 0.4,
        "EUR": 0.35,
        "KZT": 1.5,
        "CNY": 1
    }

    # failsafe values to fill if there is no correspondent value for particular currency
    DEFAULT_MIN_BALANCE_AMOUNT = 1000
    DEFAULT_MONTHLY_INTEREST_RATE = 1

    def __init__(self, client_personal_data: dict, currency: str,
                 account_id:str = None, account_status: str = 'active',
                 protected_balance: float = 0, min_balance: float = None,
                 monthly_interest_rate: float = None):
        super().__init__(client_personal_data, currency, account_id,
                         account_status,protected_balance)
        """Min balance value validation"""
        if min_balance is None:
            self._min_balance = self.THRESHOLD_MIN_BALANCE_AMOUNT.get(self._currency, self.DEFAULT_MIN_BALANCE_AMOUNT)
        elif min_balance > self.THRESHOLD_MIN_BALANCE_AMOUNT.get(self._currency, self.DEFAULT_MIN_BALANCE_AMOUNT):
            raise ValueError(f"Minimal balance is too big!Threshold for {self._currency} "
                             f"is {self.THRESHOLD_MIN_BALANCE_AMOUNT.get(self._currency, self.DEFAULT_MIN_BALANCE_AMOUNT)}.")
        else:
            self._min_balance = min_balance
        """Monthly interest rate value validation"""
        if monthly_interest_rate is None:
            self._monthly_interest_rate = self.THRESHOLD_MONTHLY_INTEREST_RATES.get(self._currency, self.DEFAULT_MONTHLY_INTEREST_RATE)
        elif monthly_interest_rate < self.THRESHOLD_MONTHLY_INTEREST_RATES.get(self._currency, self.DEFAULT_MONTHLY_INTEREST_RATE):
            raise ValueError(f"Monthly rate is too small!Threshold for {self._currency} "
                             f"is {self.THRESHOLD_MONTHLY_INTEREST_RATES.get(self._currency, self.DEFAULT_MONTHLY_INTEREST_RATE)}.")
        else:
            self._monthly_interest_rate = monthly_interest_rate

    def __str__(self):
        parent_str_string = super().__str__()
        return (f"{parent_str_string}\n"
                f"Minimum balance threshold: {self._min_balance} {self._currency}\n"
              f"Monthly interest rate: {self._monthly_interest_rate}%")

    @property
    def min_balance(self) -> float:
        return self._min_balance

    @property
    def monthly_interest_rate(self) -> float:
        return self._monthly_interest_rate

    def apply_monthly_interest(self):
        if self._protected_balance < self._min_balance:
            raise InvalidOperationError(f"To apply monthly interest balance should be equal or more then minimum balance {self._min_balance} {self._currency}.")
        else:
            self._protected_balance += self._protected_balance * (self._monthly_interest_rate / self.PERCENT_FACTOR)
            print(f"Monthly interest has been applied. Current balance: {self._protected_balance} {self._currency}")

    def withdraw(self, amount: float):
        if self._protected_balance - amount < self._min_balance:
            raise InsufficientFundsError("Insufficient funds. Balance can't be lower than minimum balance!")
        super().withdraw(amount)

    def get_account_info(self):
        parent_acc_info_string = super().get_account_info()
        return(f"{parent_acc_info_string}\n"
               f"Monthly interest rate: {self._monthly_interest_rate}%\n"
               f"Minimal balance threshold: {self._min_balance} {self._currency}")

class PremiumAccount(BankAccount):

    THRESHOLD_MAX_WITHDRAWAL_AMOUNT = {
        "RUB": 1000000.0,
        "USD": 12000.0,
        "EUR": 10000.0,
        "KZT": 5000000.0,
        "CNY": 100000.0
    }

    THRESHOLD_OVERDRAFT_AMOUNT = {
        "RUB": 100000.0,
        "USD": 1200.0,
        "EUR": 1000.0,
        "KZT": 500000.0,
        "CNY": 10000.0
    }

    THRESHOLD_FIXED_WITHDRAWAL_COMMISSION_AMOUNT = {
        "RUB": 2500.0,
        "USD": 30.0,
        "EUR": 25.0,
        "KZT": 5000.0,
        "CNY": 250.0
    }

    # failsafe values to fill if there is no correspondent value for particular currency
    DEFAULT_WITHDRAWAL_LIMIT = 100000
    DEFAULT_OVERDRAFT_LIMIT = 10000
    DEFAULT_FIXED_WITHDRAWAL_COMMISSION = 250

    def __init__(self, client_personal_data: dict, currency: str,
                 account_id:str = None, account_status: str = 'active',
                 protected_balance: float = 0, max_withdrawal_limit: float = None,
                 overdraft_limit: float = None, fixed_withdrawal_commission: float = None):

        super().__init__(client_personal_data, currency, account_id,
                         account_status, protected_balance)

        """Withdrawal limit value validation"""
        if max_withdrawal_limit is None:
            self._max_withdrawal_limit = self.THRESHOLD_MAX_WITHDRAWAL_AMOUNT.get(self._currency, self.DEFAULT_WITHDRAWAL_LIMIT)
        elif max_withdrawal_limit < self.THRESHOLD_MAX_WITHDRAWAL_AMOUNT.get(self._currency, self.DEFAULT_WITHDRAWAL_LIMIT):
            raise ValueError(
                f"Withdrawal limit is too small!Threshold for {self._currency} "
                f"is {self.THRESHOLD_MAX_WITHDRAWAL_AMOUNT.get(self._currency, self.DEFAULT_WITHDRAWAL_LIMIT)}.")
        else:
            self._max_withdrawal_limit = max_withdrawal_limit

        """Overdraft limit value validation"""
        if overdraft_limit is None:
            self._overdraft_limit = self.THRESHOLD_OVERDRAFT_AMOUNT.get(self._currency, self.DEFAULT_OVERDRAFT_LIMIT)
        elif overdraft_limit < self.THRESHOLD_OVERDRAFT_AMOUNT.get(self._currency, self.DEFAULT_OVERDRAFT_LIMIT):
            raise ValueError(
                f"Overdraft limit is too small!Threshold for {self._currency} "
                f"is {self.THRESHOLD_OVERDRAFT_AMOUNT.get(self._currency, self.DEFAULT_OVERDRAFT_LIMIT)}.")
        else:
            self._overdraft_limit = overdraft_limit

        """Fixed withdrawal commission value validation"""
        if fixed_withdrawal_commission is None:
            self._fixed_withdrawal_commission = self.THRESHOLD_FIXED_WITHDRAWAL_COMMISSION_AMOUNT.get(self._currency, self.DEFAULT_FIXED_WITHDRAWAL_COMMISSION)
        elif fixed_withdrawal_commission > self.THRESHOLD_FIXED_WITHDRAWAL_COMMISSION_AMOUNT.get(self._currency, self.DEFAULT_FIXED_WITHDRAWAL_COMMISSION):
            raise ValueError(
                f"Fixed withdrawal commission is too big!Threshold for {self._currency} "
                f"is {self.THRESHOLD_FIXED_WITHDRAWAL_COMMISSION_AMOUNT.get(self._currency, self.DEFAULT_FIXED_WITHDRAWAL_COMMISSION)}.")
        else:
            self._fixed_withdrawal_commission = fixed_withdrawal_commission

    def __str__(self):
        parent_str_string = super().__str__()
        return (f"{parent_str_string}\n"
                f"Withdrawal limit: {self._max_withdrawal_limit}\n"
                f"Overdraft limit: {self._overdraft_limit}\n"
                f"Fixed withdrawal commission: {self._fixed_withdrawal_commission}")

    @property
    def max_withdrawal_limit(self) -> float:
        return self._max_withdrawal_limit

    @property
    def overdraft_limit(self) -> float:
        return self._overdraft_limit

    @property
    def fixed_withdrawal_commission(self) -> float:
        return self._fixed_withdrawal_commission

    def withdraw(self, amount: float):
        if self._account_status == 'closed':
            raise AccountClosedError("Account is closed. Withdraw is not allowed.")
        elif self._account_status == 'frozen':
            raise AccountFrozenError("Account is frozen. Withdraw is not allowed.")
        elif amount <= 0:
            raise InvalidOperationError("Amount must be positive.")
        elif amount > self._max_withdrawal_limit:
            raise InvalidOperationError(f"Withdraw amount exceeds limit of {self._max_withdrawal_limit} {self._currency}.")
        elif self._protected_balance - amount < -self._overdraft_limit:
            raise InvalidOperationError(f"Insufficient funds.")
        else:
            self._protected_balance -= (amount + self._fixed_withdrawal_commission)
            print(f"{amount} {self._currency} has been withdrawn.\n"
              f"{self._fixed_withdrawal_commission} {self._currency} withdrawal commission has been applied.\n"
              f"Current balance: {self._protected_balance} {self._currency}\n"
              f"Overdraft available: {self._overdraft_limit + min(self._protected_balance, 0)} {self._currency}") #if balance is below 0, then available overdraft is subtracted by the balance amount

    def get_account_info(self):
        parent_acc_info_string = super().get_account_info()
        return (f"{parent_acc_info_string}\n"
                f"Withdrawal limit: {self._max_withdrawal_limit} {self._currency}\n"
                f"Overdraft available: {self._overdraft_limit + min(self._protected_balance, 0)} {self._currency}"
                f"Fixed withdrawal commission: {self._fixed_withdrawal_commission} {self._currency}")

class InvestmentAccount(BankAccount):

    ALLOWED_ASSETS_LIST = ['stocks', 'bonds', 'etf']

    THRESHOLD_YEARLY_INTEREST_RATES = {
        "stocks": 15,
        "bonds": 5,
        "etf": 10
    }

    #The balance share that should always remain on account
    MINIMAL_CASH_RESERVER_SHARE = 10

    #Ideally we should have a ticker price dict parsed from some API, here we just put the equal price for every asset
    ASSET_CURRENT_PRICE = 100

    def __init__(self, client_personal_data: dict, currency: str,
                 account_id:str = None, account_status: str = 'active',
                 protected_balance: float = 0, portfolios: dict = None):

        super().__init__(client_personal_data, currency, account_id,
                         account_status, protected_balance)
        if portfolios is None:
            self._portfolios = {} #it is possible to open account with empty portfolio
        elif not isinstance(portfolios, dict):
            raise ValueError("Incorrect format of client portfolios! Please, send dictionary with portfolios!")
        else:
            for folio_name, assets_dict in portfolios.items():
                if not assets_dict:
                    raise ValueError(f"Portfolio {folio_name} is empty! Portfolio should contain at least one virtual asset.")
                for asset_name, tickers_dict in assets_dict.items():
                    if asset_name not in self.ALLOWED_ASSETS_LIST:
                        raise ValueError(f"{asset_name} is not eligible type of asset ({self.ALLOWED_ASSETS_LIST})")
                    for ticker_name, ticker_amount in tickers_dict.items():
                        if (not tickers_dict[ticker_name]) or (ticker_amount == 0):
                            raise ValueError(f"Ticker {ticker_name} is empty! Ticker should have its amount.")
                        elif ticker_amount < 0:
                            raise ValueError(f"Ticker amount should be positive.")
            self._portfolios = portfolios

    def __str__(self):
        # 1. Taking the base from the parent class
        res = [super().__str__(), "\nInvesting portfolio:"]

        if not self._portfolios or self._portfolios == {}:
            res.append("   (no assets)")
        else:
            # 2. Iterating through portfolios
            for p_name, assets in self._portfolios.items():
                res.append(f"\n  Portfolio: **{p_name}**")

                # 3. Iterating through assets
                for a_type, tickers in assets.items():
                    if tickers:  # Typing category if it contains anything
                        res.append(f"    {a_type.upper()}:")

                        # 4. Writing tickers
                        for ticker, qty in tickers.items():
                            # :.<15 — left side aligning (15 symbols)
                            # :>10 — right side aligning (10 symbols)
                            res.append(f"      - {ticker:.<15} {qty:>10} pcs.")

        return "\n".join(res)

    @property
    def portfolios(self) -> dict:
        """"Portfolio is also a protected attribute that can me manipulated only through methods"""
        return self._portfolios

    def add_new_portfolio(self, portfolio_name: str):
        """Creates a new portfolio with the set of available assets"""
        if portfolio_name in self._portfolios:
            raise InvalidOperationError(f"Portfolio {portfolio_name} already exists!")
        else:
            self._portfolios[portfolio_name] = {asset_name: {} for asset_name in self.ALLOWED_ASSETS_LIST}

    def buy_asset(self, portfolio_name: str, asset: str, ticker: str, amount: int):

        #Check if the portfolio exists
        if portfolio_name not in self._portfolios:
            self.add_new_portfolio(portfolio_name)

        #Check if the asset is in allowed list
        if asset not in self.ALLOWED_ASSETS_LIST:
            raise InvalidOperationError(f"{asset} is not eligible type of asset!")

        if amount <= 0:
            raise InvalidOperationError("Amount must be positive!")
        else:
            current_qty = self._portfolios[portfolio_name][asset].get(ticker, 0)
            new_qty = current_qty + amount
            self._portfolios[portfolio_name][asset][ticker] = new_qty
            print(f"{amount} {ticker} has been bought.")

    def sell_asset(self, portfolio_name: str, asset: str, ticker: str, amount: int):

        # Check if the portfolio exists
        if portfolio_name not in self._portfolios:
            raise InvalidOperationError(f"{portfolio_name} portfolio does not exist!")
        elif asset not in self._portfolios[portfolio_name].keys():
            raise InvalidOperationError(f"You don't have {asset} in {portfolio_name} portfolio!")

        if amount <= 0:
            raise InvalidOperationError("Amount must be positive!")

        current_qty = self._portfolios[portfolio_name][asset].get(ticker, 0)
        new_qty = current_qty + amount
        if new_qty < 0: # our bank doesn't open short positions yet
            raise InvalidOperationError(f"Not enough ticker amount! Current amount is {current_qty}.")
        elif new_qty == 0:
            del self._portfolios[portfolio_name][asset][ticker]
            print(f"{amount} {ticker} has been sold.")
        else:
            self._portfolios[portfolio_name][asset][ticker] = new_qty
            print(f"{amount} {ticker} has been sold.")

    def withdraw(self, amount: float):
        #Maximum cash to withdraw
        max_available = self._protected_balance * (1 - (self.MINIMAL_CASH_RESERVER_SHARE / self.PERCENT_FACTOR))

        withdraw_commission = amount * (
                    self.DEFAULT_WITHDRAWAL_COMMISSION_PERCENTAGE / self.PERCENT_FACTOR)

        if amount + withdraw_commission > max_available:
            raise InvalidOperationError(f"Amount can't be withdrawn! "
                                        f"No more then {self.PERCENT_FACTOR - self.MINIMAL_CASH_RESERVER_SHARE}% "
                                        f"of balance is allowed to be withdrawn to maintain liquidity.")

    def get_account_info(self):
        # 1. Taking the base from the parent class
        res = [super().get_account_info(), "\nInvesting portfolio:"]

        if not self._portfolios or self._portfolios == {}:
            res.append("   (no assets)")
        else:
            # 2. Iterating through portfolios
            for p_name, assets in self._portfolios.items():
                res.append(f"\n  Portfolio: **{p_name}**")

                # 3. Iterating through assets
                for a_type, tickers in assets.items():
                    if tickers:  # Typing category if it contains anything
                        res.append(f"    {a_type.upper()}:")

                        # 4. Writing tickers
                        for ticker, qty in tickers.items():
                            # :.<15 — left side aligning (15 symbols)
                            # :>10 — right side aligning (10 symbols)
                            res.append(f"      - {ticker:.<15} {qty:>10} pcs.")

        return print("\n".join(res))

    def project_yearly_growth(self, portfolio_name: str):
        """Projected worth for particular portfolio. So that different portfolios can be compared by yearly profit."""
        net_worth_now = 0
        net_worth_year_after = 0
        for asset_name, tickers_dict in self._portfolios[portfolio_name].items():
            for ticker_name, ticker_amount in tickers_dict.items():
                net_worth_now += ticker_amount * self.ASSET_CURRENT_PRICE
                net_worth_year_after += (ticker_amount * self.ASSET_CURRENT_PRICE) * (1 + (self.THRESHOLD_YEARLY_INTEREST_RATES.get(asset_name, 0) / 100))
        return print(f"Projected yearly growth of {portfolio_name} portfolio "
                f"is {((net_worth_year_after / net_worth_now) - 1) * 100:.2f}%\n"
                f"Estimated value of portfolio in a year: {net_worth_year_after:.2f}\n")

# acc = InvestmentAccount(client_personal_data={"name": "Joe",
#                                   "surname": "Black",
#                                   "phone_number": "+1555555555"},
#             currency="USD")
# acc.buy_asset('main', 'stocks', 'AAPL', 100)
# acc.buy_asset('main', 'bonds', 'Govt', 570)
#
# acc.project_yearly_growth('main')

# if __name__ == "__main__":
#     print("=== Bank system test (Day 1) ===\n")
#
#     print("\n" + "-" * 40 + "\n")
#
#     print("1. Successful creation test")
#     try:
#         acc1 = BankAccount(
#             client_personal_data={"name": "Joe",
#                                   "surname": "Black",
#                                   "phone_number": "+1555555555"},
#             currency="USD"
#         )
#         print(f"Account created: {acc1}")
#     except Exception as e:
#         print(f"Unexpected error!: {e}")
#
#     print("\n" + "-"*40 + "\n")
#
#     # 2.1. Frozen account test - withdraw
#     try:
#         acc2 = BankAccount(
#             client_personal_data={"name": "Bill",
#                                   "surname": "Gates",
#                                   "phone_number": "+8547230943843"},
#             protected_balance=5000.0,
#             account_status="frozen",
#             currency="USD"
#         )
#         print(f"Frozen account: {acc2}")
#         print("Withdrawal try...")
#         acc2.withdraw(100)
#         print(f"Balance after withdrawal: {acc2.protected_balance} {acc2.currency}")
#     except AccountFrozenError as e:
#         print(f"The expected exception was successfully caught: {e}")
#     except Exception as e:
#         print(f"Error! Expected AccountFrozenError, got instead: {type(e).__name__}")
#
#     print("\n" + "-" * 40 + "\n")
#
#     print("2.2. Frozen account test - deposit")
#
#     try:
#         acc3 = BankAccount(client_personal_data={"name": "Bill",
#                                   "surname": "Hurley",
#                                   "phone_number": "+854834843843"},
#             protected_balance=5000.0,
#             account_status="frozen",
#             currency="USD")
#         print(f"Frozen account: {acc3}")
#         print("Deposit try...")
#         acc3.deposit(100)
#         print(f"Balance after deposit: {acc3.protected_balance} {acc3.currency}")
#     except AccountFrozenError as e:
#         print(f"The expected exception was successfully caught: {e}")
#     except Exception as e:
#         print(f"Error! Expected AccountFrozenError, got instead: {type(e).__name__}")
#
#     print("\n" + "-" * 40 + "\n")
#
#     print("3. Successful deposit and withdrawal test")
#
#     try:
#         acc4 = BankAccount(
#             client_personal_data={"name": "Joe",
#                                   "surname": "Black",
#                                   "phone_number": "+1555555555"},
#             currency="USD"
#         )
#         print(f"Account created: {acc4}")
#         acc4.deposit(500)
#         print(f"Balance after deposit: {acc4.protected_balance} {acc4.currency}")
#         acc4.withdraw(400)
#         print(f"Balance after withdrawal: {acc4.protected_balance} {acc4.currency}")
#     except Exception as e:
#         print(f"Unexpected error!: {e}")