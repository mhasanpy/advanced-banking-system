# """
# ADVANCED BANKING SYSTEM - HARD LEVEL LEARNING PROJECT
# Concepts covered:
# - Object-Oriented Programming (inheritance, polymorphism, encapsulation)
# - Decorators and context managers
# - Exception handling and custom exceptions
# - File I/O and JSON serialization
# - Multithreading for concurrent operations
# - Data structures (deque, defaultdict, Counter)
# - Type hints and dataclasses
# - Design patterns (Singleton, Factory, Observer)
# - Cryptography basics
# - Logging and debugging
# - Unit testing structure
# """

import json
import hashlib
import secrets
import threading
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from functools import wraps
from enum import Enum
import pickle
from abc import ABC, abstractmethod

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bank_system.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============= CUSTOM EXCEPTIONS =============
class BankException(Exception):
    """Base exception for bank system"""
    pass

class InsufficientFundsError(BankException):
    pass

class AccountNotFoundError(BankException):
    pass

class AuthenticationError(BankException):
    pass

class TransactionLimitError(BankException):
    pass

# ============= ENUMS =============
class AccountType(Enum):
    SAVINGS = "savings"
    CHECKING = "checking"
    BUSINESS = "business"
    JOINT = "joint"

class TransactionType(Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRANSFER = "transfer"
    INTEREST = "interest"
    FEE = "fee"

# ============= DECORATORS =============
def retry(max_attempts: int = 3, delay: float = 1.0):
    """Decorator to retry failed operations"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying...")
                    time.sleep(delay)
            return None
        return wrapper
    return decorator

def audit_log(func):
    """Decorator to log all transactions"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        logger.info(f"Operation: {func.__name__} | Duration: {(end_time - start_time)*1000:.2f}ms")
        return result
    return wrapper

# ============= DATA CLASSES =============
@dataclass
class Transaction:
    transaction_id: str
    type: TransactionType
    amount: float
    timestamp: datetime
    from_account: str = None
    to_account: str = None
    description: str = ""
    
    def to_dict(self) -> Dict:
        return {
            'transaction_id': self.transaction_id,
            'type': self.type.value,
            'amount': self.amount,
            'timestamp': self.timestamp.isoformat(),
            'from_account': self.from_account,
            'to_account': self.to_account,
            'description': self.description
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Transaction':
        return cls(
            transaction_id=data['transaction_id'],
            type=TransactionType(data['type']),
            amount=data['amount'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            from_account=data.get('from_account'),
            to_account=data.get('to_account'),
            description=data.get('description', '')
        )

# ============= INTERFACE / ABSTRACT CLASS =============
class AccountInterface(ABC):
    @abstractmethod
    def deposit(self, amount: float, description: str = "") -> Transaction:
        pass
    
    @abstractmethod
    def withdraw(self, amount: float, description: str = "") -> Transaction:
        pass
    
    @abstractmethod
    def get_balance(self) -> float:
        pass
    
    @abstractmethod
    def get_transaction_history(self, limit: int = 50) -> List[Transaction]:
        pass

# ============= ACCOUNT CLASS =============
class BankAccount(AccountInterface):
    """Enhanced bank account with transaction history and interest calculation"""
    
    _account_counter = 0
    _accounts = {}
    _lock = threading.Lock()
    
    def __init__(self, account_holder: str, initial_deposit: float = 0.0, 
                 account_type: AccountType = AccountType.SAVINGS,
                 overdraft_limit: float = 0.0):
        self.account_number = self._generate_account_number()
        self.account_holder = account_holder
        self.account_type = account_type
        self._balance = initial_deposit
        self.overdraft_limit = overdraft_limit
        self.created_date = datetime.now()
        self._transaction_history = deque(maxlen=1000)  # Limited to last 1000 transactions
        self._interest_rate = self._get_interest_rate()
        self._daily_withdrawal_limit = 5000 if account_type == AccountType.CHECKING else 2000
        self._daily_withdrawn = 0.0
        self._last_withdrawal_reset = datetime.now().date()
        
        # Record initial deposit as transaction
        if initial_deposit > 0:
            self.deposit(initial_deposit, "Initial deposit")
        
        self._accounts[self.account_number] = self
        BankAccount._account_counter += 1
        
    def _generate_account_number(self) -> str:
        """Generate unique account number"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_part = secrets.token_hex(4)
        return f"ACC-{timestamp}-{random_part}"
    
    def _get_interest_rate(self) -> float:
        """Get interest rate based on account type"""
        rates = {
            AccountType.SAVINGS: 0.04,  # 4% APR
            AccountType.CHECKING: 0.01,   # 1% APR
            AccountType.BUSINESS: 0.02,   # 2% APR
            AccountType.JOINT: 0.03       # 3% APR
        }
        return rates.get(self.account_type, 0.01)
    
    def _reset_daily_withdrawal(self):
        """Reset daily withdrawal limit if new day"""
        current_date = datetime.now().date()
        if current_date != self._last_withdrawal_reset:
            self._daily_withdrawn = 0.0
            self._last_withdrawal_reset = current_date
    
    def _check_withdrawal_limit(self, amount: float):
        """Check if withdrawal exceeds daily limit"""
        self._reset_daily_withdrawal()
        if self._daily_withdrawn + amount > self._daily_withdrawal_limit:
            raise TransactionLimitError(
                f"Daily withdrawal limit exceeded. Limit: ${self._daily_withdrawal_limit}, "
                f"Already withdrawn: ${self._daily_withdrawn}"
            )
    
    @audit_log
    @retry(max_attempts=2)
    def deposit(self, amount: float, description: str = "") -> Transaction:
        """Deposit money into account"""
        if amount <= 0:
            raise ValueError(f"Deposit amount must be positive: {amount}")
        
        with self._lock:
            self._balance += amount
            transaction = self._create_transaction(
                TransactionType.DEPOSIT, amount, description=description
            )
            logger.info(f"Deposited ${amount:.2f} to account {self.account_number}")
            return transaction
    
    @audit_log
    @retry(max_attempts=2)
    def withdraw(self, amount: float, description: str = "") -> Transaction:
        """Withdraw money from account with overdraft protection"""
        if amount <= 0:
            raise ValueError(f"Withdrawal amount must be positive: {amount}")
        
        self._check_withdrawal_limit(amount)
        
        if self._balance + self.overdraft_limit < amount:
            raise InsufficientFundsError(
                f"Insufficient funds. Balance: ${self._balance:.2f}, "
                f"Overdraft limit: ${self.overdraft_limit:.2f}, "
                f"Requested: ${amount:.2f}"
            )
        
        with self._lock:
            self._balance -= amount
            self._daily_withdrawn += amount
            transaction = self._create_transaction(
                TransactionType.WITHDRAWAL, amount, description=description
            )
            logger.info(f"Withdrew ${amount:.2f} from account {self.account_number}")
            return transaction
    
    def transfer(self, to_account: 'BankAccount', amount: float, 
                 description: str = "") -> Tuple[Transaction, Transaction]:
        """Transfer money between accounts"""
        if amount <= 0:
            raise ValueError(f"Transfer amount must be positive: {amount}")
        
        if self.account_number == to_account.account_number:
            raise ValueError("Cannot transfer to the same account")
        
        # Perform withdrawal and deposit in a thread-safe manner
        with self._lock:
            withdrawal_tx = self.withdraw(amount, f"Transfer to {to_account.account_number}")
        
        with to_account._lock:
            deposit_tx = to_account.deposit(amount, f"Transfer from {self.account_number}")
        
        logger.info(f"Transferred ${amount:.2f} from {self.account_number} to {to_account.account_number}")
        return withdrawal_tx, deposit_tx
    
    def calculate_interest(self) -> float:
        """Calculate and add interest to account"""
        interest = self._balance * (self._interest_rate / 12)  # Monthly interest
        if interest > 0:
            self.deposit(interest, "Monthly interest credit")
        return interest
    
    def get_balance(self) -> float:
        return self._balance
    
    def get_transaction_history(self, limit: int = 50) -> List[Transaction]:
        return list(self._transaction_history)[-limit:]
    
    def _create_transaction(self, tx_type: TransactionType, amount: float, 
                           to_account: str = None, description: str = "") -> Transaction:
        """Create and record a transaction"""
        transaction = Transaction(
            transaction_id=secrets.token_hex(16),
            type=tx_type,
            amount=amount,
            timestamp=datetime.now(),
            from_account=self.account_number,
            to_account=to_account,
            description=description
        )
        self._transaction_history.append(transaction)
        return transaction
    
    def to_dict(self) -> Dict:
        """Serialize account to dictionary"""
        return {
            'account_number': self.account_number,
            'account_holder': self.account_holder,
            'account_type': self.account_type.value,
            'balance': self._balance,
            'overdraft_limit': self.overdraft_limit,
            'created_date': self.created_date.isoformat(),
            'interest_rate': self._interest_rate,
            'transactions': [tx.to_dict() for tx in self._transaction_history]
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'BankAccount':
        """Deserialize account from dictionary"""
        account = cls(
            account_holder=data['account_holder'],
            initial_deposit=data['balance'],  # This will be overwritten
            account_type=AccountType(data['account_type']),
            overdraft_limit=data['overdraft_limit']
        )
        account.account_number = data['account_number']
        account._balance = data['balance']
        account.created_date = datetime.fromisoformat(data['created_date'])
        account._interest_rate = data['interest_rate']
        account._transaction_history = deque(
            [Transaction.from_dict(tx) for tx in data['transactions']],
            maxlen=1000
        )
        return account
    
    def __str__(self) -> str:
        return f"Account {self.account_number} - {self.account_holder}: ${self._balance:.2f}"
    
    def __repr__(self) -> str:
        return f"BankAccount('{self.account_holder}', {self._balance}, {self.account_type})"

# ============= SINGLETON PATTERN: BANK DATABASE =============
class BankDatabase:
    """Singleton class to manage all bank accounts"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        self.accounts: Dict[str, BankAccount] = {}
        self.transaction_queue = []
        self.backup_file = "bank_data.pkl"
        self.load_from_backup()
    
    def add_account(self, account: BankAccount):
        self.accounts[account.account_number] = account
        self.save_to_backup()
    
    def get_account(self, account_number: str) -> Optional[BankAccount]:
        return self.accounts.get(account_number)
    
    def remove_account(self, account_number: str):
        if account_number in self.accounts:
            del self.accounts[account_number]
            self.save_to_backup()
    
    def save_to_backup(self):
        """Save all data to backup file"""
        try:
            with open(self.backup_file, 'wb') as f:
                pickle.dump(self.accounts, f)
            logger.info("Data backed up successfully")
        except Exception as e:
            logger.error(f"Failed to backup data: {e}")
    
    def load_from_backup(self):
        """Load data from backup file"""
        try:
            with open(self.backup_file, 'rb') as f:
                self.accounts = pickle.load(f)
            logger.info("Data loaded from backup")
        except FileNotFoundError:
            logger.info("No backup file found, starting fresh")
            self.accounts = {}
        except Exception as e:
            logger.error(f"Failed to load backup: {e}")
            self.accounts = {}

# ============= CONTEXT MANAGER =============
class TransactionContext:
    """Context manager for atomic transactions"""
    def __init__(self, bank_db: BankDatabase):
        self.bank_db = bank_db
        self.affected_accounts = []
        self.snapshots = {}
    
    def __enter__(self):
        self.snapshots = {}
        for acc_num in self.affected_accounts:
            account = self.bank_db.get_account(acc_num)
            if account:
                self.snapshots[acc_num] = account.get_balance()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Rollback: restore original balances
            for acc_num, original_balance in self.snapshots.items():
                account = self.bank_db.get_account(acc_num)
                if account:
                    account._balance = original_balance
            logger.warning(f"Transaction rolled back due to: {exc_val}")
            return False
        logger.info("Transaction committed successfully")
        return True
    
    def add_account(self, account_number: str):
        self.affected_accounts.append(account_number)

# ============= ANALYTICS ENGINE =============
class AnalyticsEngine:
    """Class for analyzing bank data"""
    
    def __init__(self, bank_db: BankDatabase):
        self.bank_db = bank_db
    
    def get_total_bank_balance(self) -> float:
        """Calculate total balance across all accounts"""
        return sum(acc.get_balance() for acc in self.bank_db.accounts.values())
    
    def get_average_balance(self) -> float:
        """Calculate average balance across all accounts"""
        if not self.bank_db.accounts:
            return 0.0
        return self.get_total_bank_balance() / len(self.bank_db.accounts)
    
    def get_accounts_by_type(self) -> Dict[AccountType, int]:
        """Count accounts by type"""
        counter = defaultdict(int)
        for account in self.bank_db.accounts.values():
            counter[account.account_type] += 1
        return dict(counter)
    
    def get_top_accounts(self, n: int = 5, by_balance: bool = True) -> List[BankAccount]:
        """Get top N accounts by balance or transaction count"""
        if by_balance:
            return sorted(
                self.bank_db.accounts.values(),
                key=lambda acc: acc.get_balance(),
                reverse=True
            )[:n]
        else:
            return sorted(
                self.bank_db.accounts.values(),
                key=lambda acc: len(acc._transaction_history),
                reverse=True
            )[:n]
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive bank report"""
        return {
            'total_accounts': len(self.bank_db.accounts),
            'total_balance': self.get_total_bank_balance(),
            'average_balance': self.get_average_balance(),
            'accounts_by_type': self.get_accounts_by_type(),
            'top_5_accounts': [
                {
                    'holder': acc.account_holder,
                    'balance': acc.get_balance(),
                    'type': acc.account_type.value
                }
                for acc in self.get_top_accounts(5)
            ]
        }

# ============= MAIN APPLICATION =============
class BankingSystem:
    """Main application with CLI interface"""
    
    def __init__(self):
        self.db = BankDatabase()
        self.analytics = AnalyticsEngine(self.db)
        self.current_user = None
    
    def create_account(self):
        """Create a new bank account"""
        print("\n=== CREATE NEW ACCOUNT ===")
        name = input("Enter account holder name: ").strip()
        
        if not name:
            print("Name cannot be empty!")
            return
        
        try:
            initial_deposit = float(input("Enter initial deposit amount: $"))
            if initial_deposit < 0:
                print("Initial deposit cannot be negative!")
                return
            
            print("\nAccount types:")
            for i, acc_type in enumerate(AccountType, 1):
                print(f"{i}. {acc_type.value.title()}")
            
            type_choice = int(input("Select account type (1-4): "))
            account_type = list(AccountType)[type_choice - 1]
            
            overdraft = 0.0
            if account_type == AccountType.CHECKING:
                overdraft = float(input("Enter overdraft limit (0 for none): $"))
            
            account = BankAccount(name, initial_deposit, account_type, overdraft)
            self.db.add_account(account)
            
            print(f"\n✅ Account created successfully!")
            print(f"Account Number: {account.account_number}")
            print(f"Initial Balance: ${account.get_balance():.2f}")
            
        except ValueError as e:
            print(f"❌ Invalid input: {e}")
        except Exception as e:
            print(f"❌ Error creating account: {e}")
    
    def deposit_money(self):
        """Deposit money to account"""
        print("\n=== DEPOSIT MONEY ===")
        acc_num = input("Enter account number: ").strip()
        account = self.db.get_account(acc_num)
        
        if not account:
            print("❌ Account not found!")
            return
        
        try:
            amount = float(input("Enter deposit amount: $"))
            description = input("Enter description (optional): ")
            transaction = account.deposit(amount, description)
            print(f"✅ Deposited ${amount:.2f}")
            print(f"New balance: ${account.get_balance():.2f}")
            print(f"Transaction ID: {transaction.transaction_id}")
        except ValueError as e:
            print(f"❌ Invalid amount: {e}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def withdraw_money(self):
        """Withdraw money from account"""
        print("\n=== WITHDRAW MONEY ===")
        acc_num = input("Enter account number: ").strip()
        account = self.db.get_account(acc_num)
        
        if not account:
            print("❌ Account not found!")
            return
        
        try:
            amount = float(input("Enter withdrawal amount: $"))
            description = input("Enter description (optional): ")
            transaction = account.withdraw(amount, description)
            print(f"✅ Withdrew ${amount:.2f}")
            print(f"New balance: ${account.get_balance():.2f}")
            print(f"Transaction ID: {transaction.transaction_id}")
        except InsufficientFundsError as e:
            print(f"❌ {e}")
        except TransactionLimitError as e:
            print(f"❌ {e}")
        except ValueError as e:
            print(f"❌ {e}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def transfer_money(self):
        """Transfer money between accounts"""
        print("\n=== TRANSFER MONEY ===")
        from_acc = input("Enter source account number: ").strip()
        to_acc = input("Enter destination account number: ").strip()
        
        source = self.db.get_account(from_acc)
        destination = self.db.get_account(to_acc)
        
        if not source or not destination:
            print("❌ One or both accounts not found!")
            return
        
        try:
            amount = float(input("Enter transfer amount: $"))
            description = input("Enter description (optional): ")
            
            # Use context manager for atomic transaction
            with TransactionContext(self.db) as tc:
                tc.add_account(from_acc)
                tc.add_account(to_acc)
                withdrawal, deposit = source.transfer(destination, amount, description)
            
            print(f"✅ Transferred ${amount:.2f}")
            print(f"Source balance: ${source.get_balance():.2f}")
            print(f"Destination balance: ${destination.get_balance():.2f}")
            
        except InsufficientFundsError as e:
            print(f"❌ {e}")
        except ValueError as e:
            print(f"❌ {e}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def check_balance(self):
        """Check account balance"""
        print("\n=== CHECK BALANCE ===")
        acc_num = input("Enter account number: ").strip()
        account = self.db.get_account(acc_num)
        
        if account:
            print(f"\nAccount: {account.account_number}")
            print(f"Holder: {account.account_holder}")
            print(f"Type: {account.account_type.value.title()}")
            print(f"Balance: ${account.get_balance():.2f}")
            if account.overdraft_limit > 0:
                print(f"Overdraft Limit: ${account.overdraft_limit:.2f}")
            print(f"Available: ${account.get_balance() + account.overdraft_limit:.2f}")
        else:
            print("❌ Account not found!")
    
    def view_transaction_history(self):
        """View transaction history for an account"""
        print("\n=== TRANSACTION HISTORY ===")
        acc_num = input("Enter account number: ").strip()
        account = self.db.get_account(acc_num)
        
        if not account:
            print("❌ Account not found!")
            return
        
        try:
            limit = int(input("Number of transactions to view (default 20): ") or 20)
            transactions = account.get_transaction_history(limit)
            
            if not transactions:
                print("No transactions found.")
                return
            
            print(f"\n📊 Last {len(transactions)} transactions:")
            print("-" * 80)
            for tx in reversed(transactions):
                print(f"{tx.timestamp.strftime('%Y-%m-%d %H:%M:%S')} | "
                      f"{tx.type.value.upper():10} | "
                      f"${tx.amount:10.2f} | "
                      f"{tx.description[:30]}")
            print("-" * 80)
            
        except ValueError:
            print("Invalid number!")
        except Exception as e:
            print(f"Error: {e}")
    
    def apply_interest_all(self):
        """Apply interest to all accounts"""
        print("\n=== APPLY MONTHLY INTEREST ===")
        confirm = input("This will apply monthly interest to ALL accounts. Continue? (y/n): ")
        
        if confirm.lower() == 'y':
            total_interest = 0.0
            for account in self.db.accounts.values():
                interest = account.calculate_interest()
                total_interest += interest
                print(f"Applied ${interest:.2f} interest to {account.account_holder}")
            
            print(f"\n✅ Total interest applied: ${total_interest:.2f}")
            self.db.save_to_backup()
    
    def generate_analytics_report(self):
        """Generate and display analytics report"""
        print("\n=== BANK ANALYTICS REPORT ===")
        report = self.analytics.generate_report()
        
        print(f"\n📈 Overall Statistics:")
        print(f"  • Total Accounts: {report['total_accounts']}")
        print(f"  • Total Balance: ${report['total_balance']:,.2f}")
        print(f"  • Average Balance: ${report['average_balance']:,.2f}")
        
        print(f"\n📊 Accounts by Type:")
        for acc_type, count in report['accounts_by_type'].items():
            print(f"  • {acc_type.value.title()}: {count}")
        
        print(f"\n🏆 Top 5 Accounts by Balance:")
        for i, acc in enumerate(report['top_5_accounts'], 1):
            print(f"  {i}. {acc['holder']}: ${acc['balance']:,.2f} ({acc['type']})")
    
    def run_stress_test(self):
        """Run a stress test with multiple concurrent transactions"""
        print("\n=== STRESS TEST ===")
        print("Creating 10 test accounts...")
        
        test_accounts = []
        for i in range(10):
            acc = BankAccount(f"Test User {i}", 1000.0, AccountType.CHECKING)
            self.db.add_account(acc)
            test_accounts.append(acc)
        
        print("Running concurrent transactions...")
        
        def random_transaction():
            import random
            for _ in range(100):
                acc = random.choice(test_accounts)
                if random.random() > 0.5:
                    acc.deposit(random.uniform(10, 100))
                else:
                    try:
                        acc.withdraw(random.uniform(10, 100))
                    except InsufficientFundsError:
                        pass
        
        # Run concurrent transactions
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=random_transaction)
            thread.start()
            threads.append(thread)
        
        for thread in threads:
            thread.join()
        
        print(f"✅ Stress test completed!")
        print(f"Final total balance: ${self.analytics.get_total_bank_balance():,.2f}")
    
    def main_menu(self):
        """Display main menu and handle user input"""
        while True:
            print("\n" + "=" * 50)
            print("        ADVANCED BANKING SYSTEM")
            print("=" * 50)
            print("1. Create New Account")
            print("2. Deposit Money")
            print("3. Withdraw Money")
            print("4. Transfer Money")
            print("5. Check Balance")
            print("6. View Transaction History")
            print("7. Apply Monthly Interest")
            print("8. Generate Analytics Report")
            print("9. Run Stress Test (Advanced)")
            print("10. Backup Data")
            print("11. Load from Backup")
            print("0. Exit")
            print("=" * 50)
            
            choice = input("\nEnter your choice: ").strip()
            
            options = {
                '1': self.create_account,
                '2': self.deposit_money,
                '3': self.withdraw_money,
                '4': self.transfer_money,
                '5': self.check_balance,
                '6': self.view_transaction_history,
                '7': self.apply_interest_all,
                '8': self.generate_analytics_report,
                '9': self.run_stress_test,
                '10': lambda: self.db.save_to_backup() or print("✅ Data backed up!"),
                '11': lambda: self.db.load_from_backup() or print("✅ Data loaded!"),
                '0': lambda: exit()
            }
            
            if choice in options:
                options[choice]()
            else:
                print("❌ Invalid choice! Please try again.")
            
            if choice != '0':
                input("\nPress Enter to continue...")

# ============= UNIT TESTS =============
def run_unit_tests():
    """Run basic unit tests"""
    print("\n=== RUNNING UNIT TESTS ===\n")
    
    # Test 1: Account Creation
    try:
        acc = BankAccount("Test User", 500.0, AccountType.SAVINGS)
        assert acc.get_balance() == 500.0
        print("✅ Test 1 passed: Account creation")
    except Exception as e:
        print(f"❌ Test 1 failed: {e}")
    
    # Test 2: Deposit
    try:
        acc.deposit(100.0)
        assert acc.get_balance() == 600.0
        print("✅ Test 2 passed: Deposit")
    except Exception as e:
        print(f"❌ Test 2 failed: {e}")
    
    # Test 3: Withdrawal
    try:
        acc.withdraw(200.0)
        assert acc.get_balance() == 400.0
        print("✅ Test 3 passed: Withdrawal")
    except Exception as e:
        print(f"❌ Test 3 failed: {e}")
    
    # Test 4: Insufficient Funds
    try:
        acc.withdraw(1000.0)
        print("❌ Test 4 failed: Should have raised InsufficientFundsError")
    except InsufficientFundsError:
        print("✅ Test 4 passed: Insufficient funds handling")
    
    # Test 5: Transaction History
    try:
        history = acc.get_transaction_history()
        assert len(history) >= 2
        print("✅ Test 5 passed: Transaction history")
    except Exception as e:
        print(f"❌ Test 5 failed: {e}")
    
    print("\n✅ All tests completed!\n")

# ============= MAIN ENTRY POINT =============
if __name__ == "__main__":
    print("🚀 INITIALIZING ADVANCED BANKING SYSTEM...")
    print("📚 Learning Objectives:")
    print("  • OOP Principles (Encapsulation, Inheritance, Polymorphism)")
    print("  • Decorators and Context Managers")
    print("  • Exception Handling")
    print("  • Multi-threading & Concurrency")
    print("  • Design Patterns (Singleton, Factory, Observer)")
    print("  • File I/O & Serialization")
    print("  • Logging & Debugging")
    print("  • Unit Testing")
    
    # Run unit tests first
    run_unit_tests()
    
    # Launch main application
    try:
        banking_system = BankingSystem()
        banking_system.main_menu()
    except KeyboardInterrupt:
        print("\n\n👋 Thank you for using the Advanced Banking System!")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        print(f"\n❌ Critical error: {e}")