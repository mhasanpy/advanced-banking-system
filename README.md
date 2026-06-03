# 🏦 Advanced Banking System

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A **hard-level learning project** that implements a production-ready banking system using advanced Python concepts. Perfect for mastering OOP, design patterns, concurrency, security, and real-world system design.

## ✨ Features

### Core Banking Operations
- ✅ Create savings, checking, business, or joint accounts
- ✅ Deposit, withdraw, and transfer funds with atomic transactions
- ✅ Real-time balance inquiry and overdraft protection
- ✅ Daily withdrawal limits per account type

### Advanced Capabilities
- 🔒 **Thread-safe operations** with locking mechanisms
- 📊 **Transaction history** with rollback support (last 1000 transactions)
- 💰 **Automated interest calculation** (different rates per account type)
- 🛡️ **Custom exceptions** for insufficient funds, limits, and auth errors
- 📝 **Audit logging** with decorators and file/stream handlers

### Design Patterns Implemented
- **Singleton** – BankDatabase ensures single data source
- **Decorators** – `@audit_log`, `@retry` for resilience
- **Context Manager** – `TransactionContext` for atomic commits/rollbacks
- **Factory** – Account creation based on type
- **Observer** – Logging system listens to events

### Security & Data Management
- 🔐 Unique account numbers with timestamp + random hex
- 💾 Pickle-based backup and restore (`bank_data.pkl`)
- 📂 JSON serialization for transaction objects
- 🧵 Multi-threading support for concurrent operations

### Analytics & Reporting
- Total/average balance across all accounts
- Account distribution by type
- Top accounts by balance or transaction volume
- Generate comprehensive PDF-ready reports

## 🧠 Concepts Covered

| Concept | Implementation |
|---------|----------------|
| OOP (Encapsulation, Inheritance, Polymorphism) | `BankAccount`, `Transaction`, abstract `AccountInterface` |
| Decorators | `@retry`, `@audit_log`, `@wraps` |
| Context Managers | `TransactionContext` with `__enter__` / `__exit__` |
| Exception Handling | Custom `BankException`, `InsufficientFundsError` |
| Multi-threading | `threading.Lock`, concurrent transfer stress test |
| Data Structures | `deque`, `defaultdict`, `Counter` |
| Type Hints & Dataclasses | `@dataclass Transaction` |
| Cryptography basics | `secrets.token_hex`, hashlib (extensible) |
| Logging | `logging` module with file + console handlers |
| Unit Testing | Built-in test suite (`run_unit_tests()`) |

## 📋 Prerequisites

- Python 3.10 or higher
- No external dependencies (uses only standard library)

## 🚀 Installation & Setup

```bash
# 1. Clone the repository
git clone https://github.com/mhasanpy/advanced-banking-system.git
cd advanced-banking-system

# 2. (Optional) Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Run the banking system
python "ADVANCED BANKING SYSTEM - HARD LEVEL LEARNING PROJECT.py"
