from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import uuid
import yfinance as yf

class AccountFrozenError(Exception):
    pass

class AccountClosedError(Exception):
    pass

class InvalidOperationError(Exception):
    pass

class InsufficientFundsError(Exception):
    pass

class Bank:

    #night is considered starting this hour
    NIGHT_OPERATIONS_LOWER_LIMIT_HOUR_NUMBER = 0

    # night is considered finishing this hour
    NIGHT_OPERATIONS_HIGHER_LIMIT_HOUR_NUMBER = 5

    #Threshold to mark transaction as suspicious if it surpasses it
    HIGH_RISK_TRANSACTION_AMOUNT = {
        "RUB": 1000000.0,
        "USD": 12000.0,
        "EUR": 10000.0,
        "KZT": 5000000.0,
        "CNY": 100000.0
    }

    def __init__(self, name: str):
        self._accounts = {}
        self._clients = {}
        self._logins = {}
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def accounts(self) -> dict:
        return self._accounts

    @property
    def clients(self) -> dict:
        return self._clients

    @property
    def logins(self) -> dict:
        return self._logins

    def add_login(self, client: Client, login: str):
        if login in self.logins:
            raise InvalidOperationError(f"Login {login} already exists! Please, choose another one.")
        else:
            self._logins[login] = client

    def add_client(self, client: Client):
        if client not in self._clients.values():
            self._clients[client.client_id] = client
        else:
            raise InvalidOperationError(f"Client {client.client_id} already exists!")

    def open_account(self, account: AbstractAccount):
        if account not in self._accounts.values():
            self._accounts[account.account_id] = account
        else:
            raise InvalidOperationError(f"Account {account.account_id} already exists!")

    def close_account(self, account: AbstractAccount):
        if account not in self._accounts.values():
            raise InvalidOperationError(f"Account {account.account_id} does not exist in {self.name}!")
        elif account.account_status == "closed":
            raise InvalidOperationError(f"Account {account.account_id} is already closed!")
        else:
            account.account_status = "closed"
            print(f"Account {account.account_id} has been closed!")

    def freeze_account(self, account: AbstractAccount):
        if account not in self._accounts.values():
            raise InvalidOperationError(f"Account {account.account_id} does not exist in {self.name}!")
        elif account.account_status != "active":
            raise InvalidOperationError(f"Account {account.account_id} is not active!")
        else:
            account.account_status = "frozen"
            print(f"Account {account.account_id} has been frozen!")

    def unfreeze_account(self, account: AbstractAccount):
        if account not in self._accounts.values():
            raise InvalidOperationError(f"Account {account.account_id} does not exist in {self.name}!")
        elif account.account_status != "frozen":
            raise InvalidOperationError(f"Account {account.account_id} is not frozen!")
        else:
            account.account_status = "active"
            print(f"Account {account.account_id} has been unfrozen!")

    def change_password(self, client: Client, new_password: str):
        if client not in self._clients.values():
            raise InvalidOperationError(f"Client {client.client_id} does not exist in {self.name}!")
        elif client.client_account_status == "fully_blocked":
            raise InvalidOperationError(f"Client account is fully blocked.Changing of password is prohibited.")
        elif len(new_password) < client.MINIMAL_PASSWORD_LENGTH: #Basic password validation
            raise InvalidOperationError(f"Password has to be at least {client.MINIMAL_PASSWORD_LENGTH} characters!")
        else:
            client._client_password = new_password

    def authenticate_client(self, login: str, password: str):
        if login not in self.logins:
            print(f"Login or password is incorrect! Try again.")
        elif self.logins[login].client_account_status == "fully_blocked":
            raise InvalidOperationError(f"Client account {self.logins[login].client_id} is fully blocked! Access to internet banking is prohibited.")
        elif self.logins[login].client_account_status == "temporarily_blocked" or self.logins[login].failed_attempts >= self.logins[login].FAILED_ATTEMPTS_TO_TEMP_BLOCK:
            raise InvalidOperationError(f"Client account {self.logins[login].client_id} is temporarily blocked! Access denied!")
        elif login != self.logins[login].client_login or password != self.logins[login].client_password:
            self.logins[login]._failed_attempts += 1
            if self.logins[login].failed_attempts < 3:
                print(f"Login or password is incorrect! Try again.")
            else:
                raise InvalidOperationError(f"Client account {self.logins[login].client_id} is temporarily blocked! Access denied!")
        else:
            self.logins[login]._failed_attempts = 0
            print(f"Successful authentication! Welcome back, {self.logins[login].client_name}!")

    def search_accounts(self, client: Client):
        if client not in self._clients.values():
            raise InvalidOperationError(f"Client account {client.client_id} does not exist in {self.name}!")
        elif len(client.account_ids) == 0:
            print(f"Client {client.client_id} has no accounts!")
        else:
            print(f"Client {client.client_id} account ids:")
            for account in client.account_ids:
                print(account)

    def is_night_operation_allowed(self, client: Client) -> bool:
        if self.NIGHT_OPERATIONS_LOWER_LIMIT_HOUR_NUMBER <= datetime.now().hour < self.NIGHT_OPERATIONS_HIGHER_LIMIT_HOUR_NUMBER\
                and client.is_night_operations_allowed == False:
            return False
        else:
            return True

    def suspicious_client_marker (self, client: Client, amount: float, currency:str):
        if amount >= self.HIGH_RISK_TRANSACTION_AMOUNT[currency]:
            client.is_suspicious_client = True

    def get_total_balance(self, currency: str) -> float:
        """Deliver total balance of all clients that have accounts in chosen currency"""
        total_balance = 0
        for account in self._accounts.values():
            if account.currency == currency:
                total_balance += account.protected_balance
        return total_balance

    def get_clients_ranking(self, currency: str, number_of_users_in_top: int = None) -> list:
        """Deliver clients ranking by their total balance in chosen currency"""
        clients_ranking = []
        for client_id, client in self._clients.items():
            total_client_balance = 0
            for account in client.account_ids:
                if account.currency == currency:
                    total_client_balance += account.protected_balance
            clients_ranking.append({client_id: total_client_balance})

        #Sorting clients by their balance amount descending
        clients_ranking.sort(key=lambda x: x["protected_balance"], reverse=True)

        #Forming the top of users if specified
        if number_of_users_in_top is not None:
            return clients_ranking[:number_of_users_in_top]
        else:
            return clients_ranking


best_bank = Bank('Best bank') #Insert the name of our bank here :)

class AbstractAccount(ABC):

    ALLOWED_ACCOUNT_STATUSES_LIST = ["active", "frozen", "closed"]

    def __init__(self, account_id: str, client: Client,
                 account_status: str = 'active', protected_balance: float = 0,
                 bank: Bank = best_bank):
        self._account_id = str(account_id)
        self._client = client
        self.account_status = account_status
        self._protected_balance = protected_balance
        self._bank = bank
        self._bank.open_account(self) #Adding account to the list of all accounts
        self._client.link_account(self._account_id)  #Connect client and account
        print(f"Account {self._account_id} has been successfully created!")

    @property
    def bank(self) -> Bank:
        return self._bank

    @property
    def account_id(self) -> str:
        """Protected account id attribute"""
        return self._account_id

    @property
    def client(self) -> Client:
        """Protected client attribute"""
        return self._client

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
        if not account_status in self.ALLOWED_ACCOUNT_STATUSES_LIST:
            raise ValueError(f"Incorrect account status! Please choose from {self.ALLOWED_ACCOUNT_STATUSES_LIST}")
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

    BANK_ACCOUNT_ALLOWED_CURRENCIES_LIST = ["RUB", "USD", "EUR", "KZT", "CNY"]

    PERCENT_FACTOR = 100

    DEFAULT_WITHDRAWAL_COMMISSION_PERCENTAGE = 0.5

    def __init__(self, client: Client, currency: str, account_id:str = None,
                 account_status: str = 'active', protected_balance: float = 0, bank: Bank = best_bank):
        """If the client doesn't have an account id, it will be generated.
        Currency is an immutable attribute after initialization."""
        if account_id is None:
            generated_id = str(uuid.uuid4())
        else:
            generated_id = str(account_id)
        super().__init__(generated_id, client, account_status, protected_balance, bank)
        if not currency in self.BANK_ACCOUNT_ALLOWED_CURRENCIES_LIST:
            raise ValueError(f"Incorrect currency! Please choose from {self.BANK_ACCOUNT_ALLOWED_CURRENCIES_LIST}")
        else:
            self._currency = currency

    def __str__(self):
        mobile_phone_str = f'****{self._client.mobile_phone_number[-4:]}' if self._client.mobile_phone_number else f'None'
        return (f"{self._account_id} account info:\n"
              f"Account type: {self.__class__.__name__}\n"
              f"Client name: {self._client.client_name} {self._client.client_surname} {self._client.client_middle_name}\n"
              f"Client phone number: {mobile_phone_str}\n"
              f"Account status: {self._account_status}\n"
              f"Account balance: {self._protected_balance} {self._currency}")

    @property
    def currency(self) -> str:
        """Protected currency attribute"""
        return self._currency

    def deposit(self, amount: float):
        self._bank.suspicious_client_marker(self._client, amount, self._currency)
        if self._account_status == 'closed':
            raise AccountClosedError("Account is closed. Deposit is not allowed.")
        elif self._account_status == 'frozen':
            raise AccountFrozenError("Account is frozen. Deposit is not allowed.")
        elif amount <= 0:
            raise InvalidOperationError("Amount must be positive.")
        elif not self._bank.is_night_operation_allowed(self._client):
            raise InvalidOperationError(
                f"Night operations until {self._bank.NIGHT_OPERATIONS_HIGHER_LIMIT_HOUR_NUMBER}AM are not allowed!")
        else:
            self._protected_balance += amount
        print(f"{amount} {self._currency} has been deposited.\n"
              f"Current balance: {self._protected_balance} {self._currency}.")

    def withdraw(self, amount: float):
        self._bank.suspicious_client_marker(self._client, amount, self._currency)
        if self._account_status == 'closed':
            raise AccountClosedError("Account is closed. Withdraw is not allowed.")
        elif self._account_status == 'frozen':
            raise AccountFrozenError("Account is frozen. Withdraw is not allowed.")
        elif amount <= 0:
            raise InvalidOperationError("Amount must be positive.")
        elif self._protected_balance < amount:
            raise InsufficientFundsError("Insufficient funds.")
        elif not self._bank.is_night_operation_allowed(self._client):
            raise InvalidOperationError(f"Night operations until {self._bank.NIGHT_OPERATIONS_HIGHER_LIMIT_HOUR_NUMBER}AM are not allowed!")
        else:
            withdraw_commission = amount * (self.DEFAULT_WITHDRAWAL_COMMISSION_PERCENTAGE / self.PERCENT_FACTOR) #default withdrawal commission is dynamic based on the amount
            self._protected_balance -= (amount + withdraw_commission)
        print(f"{amount} {self._currency} has been withdrawn.\n"
              f"{self.DEFAULT_WITHDRAWAL_COMMISSION_PERCENTAGE}% withdrawal commission has been applied ({withdraw_commission} {self._currency})\n"
              f"Current balance: {self._protected_balance} {self._currency}")

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

    def __init__(self, client: Client, currency: str,
                 account_id:str = None, account_status: str = 'active',
                 protected_balance: float = 0, min_balance: float = None,
                 monthly_interest_rate: float = None, bank: Bank = best_bank):
        """Min_balance and monthly_interest_rate are immutable attributes after initialization."""
        super().__init__(client, currency, account_id,
                         account_status,protected_balance, bank)
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

    def __init__(self, client: Client, currency: str,
                 account_id:str = None, account_status: str = 'active',
                 protected_balance: float = 0, max_withdrawal_limit: float = None,
                 overdraft_limit: float = None, fixed_withdrawal_commission: float = None,
                 bank: Bank = best_bank):
        """Withdrawal_limit, Overdraft_limit and Fixed_withdrawal_commission are immutable attributes after initialization."""
        super().__init__(client, currency, account_id,
                         account_status, protected_balance, bank)

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
        self._bank.suspicious_client_marker(self._client, amount, self._currency)
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
        elif not self._bank.is_night_operation_allowed(self._client):
            raise InvalidOperationError(
                f"Night operations until {self._bank.NIGHT_OPERATIONS_HIGHER_LIMIT_HOUR_NUMBER}AM are not allowed!")
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

    ALLOWED_ASSETS_LIST = ['stocks', 'bonds', 'etfs']

    THRESHOLD_YEARLY_INTEREST_RATES = {
        "stocks": 15,
        "bonds": 5,
        "etfs": 10
    }

    #The balance share that should always remain on account
    MINIMAL_CASH_RESERVER_SHARE = 10

    def __init__(self, client: Client, currency: str,
                 account_id:str = None, account_status: str = 'active',
                 protected_balance: float = 0, portfolios: dict = None,
                 bank: Bank = best_bank):
        """Portfolios is a protected attribute after initialization.
        Can be changed only through defined class methods."""
        super().__init__(client, currency, account_id,
                         account_status, protected_balance, bank)
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
        """Adds the specified asset to the portfolio."""
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
        """Sells the specified asset from the portfolio."""
        # Check if the portfolio exists
        if portfolio_name not in self._portfolios:
            raise InvalidOperationError(f"{portfolio_name} portfolio does not exist!")
        elif asset not in self._portfolios[portfolio_name].keys():
            raise InvalidOperationError(f"You don't have {asset} in {portfolio_name} portfolio!")

        if amount <= 0:
            raise InvalidOperationError("Amount must be positive!")

        current_qty = self._portfolios[portfolio_name][asset].get(ticker, 0)
        new_qty = current_qty - amount
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
        else:
            super().withdraw(amount)

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

        print("\n".join(res))

    def project_yearly_growth(self, portfolio_name: str):
        """Projected worth for particular portfolio. So that different portfolios can be compared by yearly profit.
        Prices are available only for assets that are listed on Yahoo Finance."""
        net_worth_now = 0
        net_worth_year_after = 0

        if portfolio_name not in self._portfolios:
            raise InvalidOperationError(f"{portfolio_name} portfolio does not exist!")

        for asset_name, tickers_dict in self._portfolios[portfolio_name].items():
            for ticker_name, ticker_amount in tickers_dict.items():
                try:
                    ticker_yahoo = yf.Ticker(ticker_name)
                    data = ticker_yahoo.history()
                    last_quote = data['Close'].iloc[-1]
                except: #If there is no such ticker in Yahoo Finance it will raise the error, but the code will still compute
                    last_quote = 0
                net_worth_now += ticker_amount * last_quote
                net_worth_year_after += ((ticker_amount * last_quote) *
                                         (1 + (self.THRESHOLD_YEARLY_INTEREST_RATES.get(asset_name, 0) / 100)))

        if net_worth_now > 0:
            print(f"Projected yearly growth of {portfolio_name} portfolio "
                    f"is {((net_worth_year_after / net_worth_now) - 1) * 100:.2f}%\n"
                    f"Current value of portfolio: {net_worth_now:.2f} USD\n"
                    f"Estimated value of portfolio in a year: {net_worth_year_after:.2f} USD\n")
        else:
            print(f"{portfolio_name} portfolio is empty or its assets don't have price data.")

class Client:

    ALLOWED_CLIENT_ACCOUNT_STATUSES_LIST = ['active', 'temporarily_blocked', 'fully_blocked']

    DATE_FORMAT = '%Y-%m-%d'

    AGE_RESTRICTION_YEARS_NUMBER = 18

    FAILED_ATTEMPTS_TO_TEMP_BLOCK = 3

    MINIMAL_PASSWORD_LENGTH = 8

    def __init__(self, client_name: str, client_surname: str,
                 client_contacts: dict, client_birthdate: str,
                 client_login:str, client_password: str,
                 client_middle_name: str = '', client_id: str = None,
                 client_account_status:str = 'active', bank: Bank = best_bank,
                 failed_attempts = 0, is_night_operations_allowed: bool = False,
                 is_suspicious_client = False):
        self.client_name = client_name
        self.client_surname = client_surname
        self.client_middle_name = client_middle_name

        if failed_attempts >= self.FAILED_ATTEMPTS_TO_TEMP_BLOCK:
            self.client_account_status = 'temporarily_blocked'
        else:
            self.client_account_status = client_account_status

        if not isinstance(client_contacts, dict):
            raise ValueError("Incorrect format of client contacts data! Please, send dictionary")
        else:
            self.client_contacts = client_contacts
            self.mobile_phone_number = client_contacts.get('mobile_phone_number', None)
            #Basic email validation
            if client_contacts.get('email', None) is not None and '@' not in client_contacts['email']:
                raise ValueError("Incorrect format of email!")
            else:
                self.email = client_contacts.get('email', None)

        self.client_birthdate = client_birthdate
        self._account_ids = []  # List of all account_ids of the client
        self.is_night_operations_allowed = is_night_operations_allowed
        self.is_suspicious_client = is_suspicious_client

        if client_id is None:
            self._client_id = str(uuid.uuid4())
        else:
            self._client_id = str(client_id)

        self._bank = bank
        self._bank.add_client(self)
        self._failed_attempts = failed_attempts

        self._client_login = client_login
        self._bank.add_login(self, self._client_login)

        if len(client_password) < self.MINIMAL_PASSWORD_LENGTH:
            raise ValueError(f"Password must be at least {self.MINIMAL_PASSWORD_LENGTH} characters!")
        else:
            self._client_password = client_password

        print(f"Client {self._client_id} has been successfully created")


    def __str__(self):
        mobile_phone_str = f'****{self.mobile_phone_number[-4:]}' if self.mobile_phone_number else f'None'
        email_str = (f'{self.email[:4]}'
                     f'{'*'*(len(self.email[:self.email.index('@')]) - 4)}'
                     f'{self.email[self.email.index('@'):]}') if self.email else f'None'
        return (f"Client name: {self.client_name} {self.client_surname} {self.client_middle_name}\n"
                f"Client id: {self._client_id}\n"
                f"Client account status: {self.client_account_status}\n"
                f"Client birthdate: {self.client_birthdate}\n"
                f"Client mobile phone number: {mobile_phone_str}\n"
                f"Client email: {email_str}")

    @property
    def client_login(self) -> str:
        return self._client_login

    @property
    def client_password(self) -> str:
        return self._client_password

    @property
    def failed_attempts(self) -> int:
        return self._failed_attempts

    @property
    def bank(self) -> Bank:
        return self._bank

    @property
    def client_id(self) -> str:
        return self._client_id

    @property
    def client_account_status(self):
        return self._client_account_status

    @client_account_status.setter
    def client_account_status(self, client_account_status: str):
        """Account status validation"""
        if not client_account_status in self.ALLOWED_CLIENT_ACCOUNT_STATUSES_LIST:
            raise ValueError(f"Incorrect account status! Please choose from {self.ALLOWED_CLIENT_ACCOUNT_STATUSES_LIST}")
        else:
            self._client_account_status = client_account_status

    @property
    def client_birthdate(self) -> str:
        return self._client_birthdate

    #There is still a possibility to change the birthday of a client is case of typos while creating.
    @client_birthdate.setter
    def client_birthdate(self, client_birthdate: str):
        """Birthdate validation"""
        try:
            date_obj = datetime.strptime(client_birthdate, self.DATE_FORMAT) #If the format is different there will be an error raised here
            if date_obj + relativedelta(years=self.AGE_RESTRICTION_YEARS_NUMBER) > datetime.now():
                raise InvalidOperationError(f"Client should be {self.AGE_RESTRICTION_YEARS_NUMBER} years or older!")
            else:
                self._client_birthdate = date_obj.strftime(self.DATE_FORMAT)
        except Exception as e:
            raise InvalidOperationError(e)

    @property
    def account_ids(self):
        """The list of account ids is a protected attribute."""
        return self._account_ids

    def link_account(self, account_id: str):
        """Method to connect account to a client."""
        if account_id not in self._account_ids:
            self._account_ids.append(account_id)


if __name__ == "__main__":
    print("=== Bank system testing ===\n")

    print("1.1. Successful client creation test")

    try:
        client_1 = Client(
            client_name="Joe",
            client_surname="Black",
            client_contacts={
                'mobile_phone_number' : "+1555555555",
                'email' : "joeblack@yahoo.com",
                'landline_phone_number' : "+99032359993"
            },
            client_birthdate="1970-01-01",
            client_login = 'joeblack',
            client_password = 'holymary'
        )
    except Exception as e:
        print(f"Unexpected error!: {e}")

    print("\n" + "-" * 40 + "\n")

    print("1.2. Unsuccessful client creation test - invalid password")

    try:
        client_2 = Client(
            client_name="Joe",
            client_surname="Black",
            client_contacts={
                'mobile_phone_number' : "+1555555555",
                'email' : "joeblack@yahoo.com",
                'landline_phone_number' : "+99032359993"
            },
            client_birthdate="1970-01-01",
            client_login = 'joeblack',
            client_password = '123'
        )
    except InvalidOperationError as e:
        print(f"The expected exception was successfully caught: {e}")
    except Exception as e:
        print(f"Unexpected error!: {e}")

    print("\n" + "-" * 40 + "\n")

    print("1.3. Unsuccessful client creation test - age restriction")

    try:
        client_2 = Client(
            client_name="Joe",
            client_surname="Black",
            client_contacts={
                'mobile_phone_number': "+1555555555",
                'email': "joeblack@yahoo.com",
                'landline_phone_number': "+99032359993"
            },
            client_birthdate="2010-01-01",
            client_login='joeblack',
            client_password='holymary'
        )
    except InvalidOperationError as e:
        print(f"The expected exception was successfully caught: {e}")
    except Exception as e:
        print(f"Unexpected error!: {e}")

    print("\n" + "-" * 40 + "\n")

    print("2. Successful account creation test")
    try:
        acc = BankAccount(
            client_1,
            currency="USD"
        )
    except Exception as e:
        print(f"Unexpected error!: {e}")

    print("\n" + "-"*40 + "\n")

    print('2.1. Frozen account test - withdraw')

    try:
        acc = BankAccount(
            client_1,
            protected_balance=5000.0,
            account_status="frozen",
            currency="USD"
        )
        print(f"Frozen account: {acc}")
        print("Withdrawal try...")
        acc.withdraw(100)
    except AccountFrozenError as e:
        print(f"The expected exception was successfully caught: {e}")
    except Exception as e:
        print(f"Error! Expected AccountFrozenError, got instead: {type(e).__name__}")

    print("\n" + "-" * 40 + "\n")

    print("2.2. Frozen account test - deposit")

    try:
        acc = BankAccount(
            client_1,
            protected_balance=5000.0,
            account_status="frozen",
            currency="USD")
        print(f"Frozen account: {acc}")
        print("Deposit try...")
        acc.deposit(100)
    except AccountFrozenError as e:
        print(f"The expected exception was successfully caught: {e}")
    except Exception as e:
        print(f"Error! Expected AccountFrozenError, got instead: {type(e).__name__}")

    print("\n" + "-" * 40 + "\n")

    print("2.3. Successful deposit and withdrawal test")

    try:
        acc = BankAccount(
            client_1,
            currency="USD"
        )
        acc.deposit(500)
        acc.withdraw(400)
    except Exception as e:
        print(f"Unexpected error!: {e}")

    print("\n" + "-" * 40 + "\n")

    print("2.4. Savings account successful creation and operations test")

    try:
        acc = SavingsAccount(
            client_1,
            currency="RUB"
        )
        print(acc)
        acc.deposit(10500)
        acc.withdraw(100)
        acc.apply_monthly_interest()
    except Exception as e:
        print(f"Unexpected error!: {e}")

    print("\n" + "-" * 40 + "\n")

    print("2.5. Savings account failed withdrawal test")

    try:
        acc = SavingsAccount(
            client_1,
            currency="KZT"
        )
        acc.deposit(10000)
        acc.withdraw(500)
        acc.apply_monthly_interest()
    except InsufficientFundsError as e:
        print(f"The expected exception was successfully caught: {e}")
    except Exception as e:
        print(f"Error! Expected InsufficientFundsError, got instead: {type(e).__name__}")

    print("\n" + "-" * 40 + "\n")

    print("2.6. Savings account failed monthly interest application test")

    try:
        acc = SavingsAccount(
            client_1,
            currency="KZT"
        )
        acc.deposit(1000)
        acc.apply_monthly_interest()
    except InvalidOperationError as e:
        print(f"The expected exception was successfully caught: {e}")
    except Exception as e:
        print(f"Error! Expected InvalidOperationError, got instead: {type(e).__name__}")

    print("\n" + "-" * 40 + "\n")

    print("2.7. Premium account successful creation and operations test")

    try:
        acc = PremiumAccount(
            client_1,
            currency="USD"
        )
        print(acc)
        acc.deposit(10000)
        acc.withdraw(10500)
    except Exception as e:
        print(f"Unexpected error!: {e}")

    print("\n" + "-" * 40 + "\n")

    print("2.8. Premium account failed withdrawal test 1")

    try:
        acc = PremiumAccount(
            client_1,
            currency="USD"
        )
        print(acc)
        acc.deposit(100000)
        acc.withdraw(20000)
    except InvalidOperationError as e:
        print(f"The expected exception was successfully caught: {e}")
    except Exception as e:
        print(f"Unexpected error!: {e}")

    print("\n" + "-" * 40 + "\n")

    print("2.9. Premium account failed withdrawal test 2")

    try:
        acc = PremiumAccount(
            client_1,
            currency="USD"
        )
        print(acc)
        acc.deposit(10000)
        acc.withdraw(12000)
    except InsufficientFundsError as e:
        print(f"The expected exception was successfully caught: {e}")
    except Exception as e:
        print(f"Unexpected error!: {e}")

    print("\n" + "-" * 40 + "\n")

    print("2.10. Investment account successful creation and operations test")

    try:
        acc = InvestmentAccount(
            client_1,
            currency="USD"
        )
        print(acc)
        acc.deposit(100000)
        acc.buy_asset('main', 'stocks', 'AAPL', 100)
        acc.buy_asset('main', 'bonds', 'VEXUS', 50) #imagined bond name
        acc.withdraw(50000)
        acc.project_yearly_growth('main') #there will be an error for the bond that is not listed, but code still will function
        acc.get_account_info()
    except Exception as e:
        print(f"Unexpected error!: {e}")

    print("\n" + "-" * 40 + "\n")

    print("2.11. Investment account failed withdrawal test")

    try:
        acc = InvestmentAccount(
            client_1,
            currency="USD"
        )
        print(acc)
        acc.deposit(100000)
        acc.withdraw(100000)
    except InvalidOperationError as e:
        print(f"The expected exception was successfully caught: {e}")
    except Exception as e:
        print(f"Unexpected error!: {e}")

    print("\n" + "-" * 40 + "\n")

    print("2.12. Investment account failed asset sell test")

    try:
        acc = InvestmentAccount(
            client_1,
            currency="USD"
        )
        print(acc)
        acc.buy_asset('main', 'stocks', 'AAPL', 100)
        acc.sell_asset('main', 'stocks', 'AAPL', 200)
    except InvalidOperationError as e:
        print(f"The expected exception was successfully caught: {e}")
    except Exception as e:
        print(f"Unexpected error!: {e}")

    print("\n" + "-" * 40 + "\n")

    print("3.1. Freezing and closing account test")

    try:
        acc = InvestmentAccount(
            client_1,
            currency="USD"
        )
        print(acc)
        best_bank.freeze_account(acc)
        best_bank.close_account(acc)
    except InvalidOperationError as e:
        print(f"The expected exception was successfully caught: {e}")
    except Exception as e:
        print(f"Unexpected error!: {e}")

    print("\n" + "-" * 40 + "\n")

    print("3.2. Unsuccessful freezing test")

    try:
        acc = InvestmentAccount(
            client_1,
            currency="USD"
        )
        print(acc)
        best_bank.close_account(acc)
        best_bank.freeze_account(acc)
    except InvalidOperationError as e:
        print(f"The expected exception was successfully caught: {e}")
    except Exception as e:
        print(f"Unexpected error!: {e}")

    print("\n" + "-" * 40 + "\n")

    print("3.3. Successful authentication test")

    try:
        best_bank.authenticate_client('joeblack', 'holymary')
    except InvalidOperationError as e:
        print(f"The expected exception was successfully caught: {e}")
    except Exception as e:
        print(f"Unexpected error!: {e}")

    print("\n" + "-" * 40 + "\n")

    print("3.3. Unsuccessful authentication test")

    try:
        best_bank.authenticate_client('joeblack', '123')
        best_bank.authenticate_client('joeblack', '123')
        best_bank.authenticate_client('joeblack', '123')
    except InvalidOperationError as e:
        print(f"The expected exception was successfully caught: {e}")
    except Exception as e:
        print(f"Unexpected error!: {e}")