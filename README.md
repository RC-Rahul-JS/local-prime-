# 🚀 Local Prime - Loan Management System & GST Invoice Generator

Enterprise-grade Flask REST API for loan lifecycle management (Sanction, EMI Generation, Interest Posting, Waterfall Payments, Penalties, Closure) and ultra-premium ReportLab PDF Invoice generation.

---

## 🏛️ Senior Developer Architecture Rationale

This project was transformed from a 2,000-line single-file script into a modular, production-ready enterprise application adhering to 12-Factor App methodology:

```
bill/
├── .env                    # 🔒 Environment variables (Secrets isolated - GitIgnored)
├── .env.example            # 📄 Environment template for deployment
├── .gitignore              # 🛡️ Excludes .venv, secrets, generated PDFs & cache
├── pyproject.toml          # 📦 Modern Python project metadata
├── requirements.txt        # 📌 Production dependencies with version bounds
├── main.py                 # 🚀 Flask Application Factory server entrypoint
├── loan.py                 # 🔄 Backwards compatible proxy entrypoint
├── generate_invoice.py     # 🔄 Backwards compatible CLI invoice runner
├── app/                    # 🏗️ Core Application Package
│   ├── __init__.py         # 🏭 Application Factory (create_app) & Blueprints
│   ├── config.py           # ⚙️ Centralized environment configuration
│   ├── db.py               # 🗄️ Singleton MongoDB database connection manager
│   ├── services/           # 🧠 Domain Business Logic Services
│   │   ├── loan_service.py # 🧮 EMI amortization (Reducing balance & Flat rate)
│   │   └── invoice_service.py # 🎨 ReportLab PDF Invoice generator engine
│   └── routes/             # 🛣️ Modular REST API Controllers (Flask Blueprints)
│       ├── loan_routes.py    # 💳 /loan-calculator, /loan-sanction, /loan-closure
│       ├── payment_routes.py # 💸 /loan-disbursement, /generate-emi-due, /customer-payment, /penalty-posting
│       ├── interest_routes.py# 📊 /interest-posting, /interest-posting-list, /interest-posting-batch
│       └── invoice_routes.py # 🧾 /generate-invoice API
```

### Why This Architecture?
1. **Modularity & Scalability**: Splitting endpoint handlers into Blueprint domains (`loan`, `payment`, `interest`, `invoice`) prevents monolithic code smells and enables independent feature extension.
2. **Security Standards**: Extracted database credentials (`MONGO_URI`) from source code into environment variables (`.env`).
3. **Pure Business Logic Layer**: Moved financial calculations (EMI, Reducing Balance vs Flat rate, waterfall payment allocation) out of controllers into reusable domain services (`app/services/`).
4. **Git Hygiene**: Prevented virtual environments (`.venv`), cached credentials, and generated PDFs from cluttering the repository via `.gitignore`.

---

## 📡 API Endpoint Reference

| Endpoint | Method | Description |
| :--- | :---: | :--- |
| `/health` | `GET` | System health check and version info |
| `/loan-calculator` | `POST` | Calculate EMI amortization schedule (Reducing/Flat) |
| `/loan-sanction` | `POST` | Create & sanction new customer loan |
| `/loan-disbursement` | `POST` | Disburse sanctioned loan funds to bank account |
| `/generate-emi-due` | `POST` | Generate monthly/weekly EMI due for active loan |
| `/customer-payment` | `POST` | Process customer payment with Waterfall logic (Penalty → Interest → Principal) |
| `/interest-posting` | `POST` | Accrue and post interest for a single loan |
| `/interest-posting-list` | `GET` | List loans pending interest posting for a given date |
| `/interest-posting-batch` | `POST` | Batch process interest posting for all due loans |
| `/penalty-posting` | `POST` | Assess & post late payment penalty fees |
| `/loan-closure-list` | `GET` | List loans eligible for closure |
| `/loan-closure` | `POST` | Formally close fully-repaid loan account |
| `/generate-invoice` | `POST` | Generate and download ReportLab PDF invoice |

---

## 🛠️ Quick Start Guide

### 1. Install Dependencies
```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Environment
Create or verify `.env` file:
```env
MONGO_URI=mongodb+srv://igold:gold0011@igold.eazpfbp.mongodb.net/?retryWrites=true&w=majority&appName=igold
PORT=5001
FLASK_ENV=development
SECRET_KEY=local-prime-secret-key
```

### 3. Run Application Server
```bash
python main.py
# Server runs at http://localhost:5001
```

---

## 🐙 Git Repository Setup (`https://github.com/RC-Rahul-JS/local-prime-.git`)

To link this structured codebase to your Git repository, run the following commands in your terminal:

```bash
# 1. Initialize Git repository if not already done
git init

# 2. Add remote origin
git remote add origin https://github.com/RC-Rahul-JS/local-prime-.git
# (Or if remote exists, update url:)
# git remote set-url origin https://github.com/RC-Rahul-JS/local-prime-.git

# 3. Stage clean files
git add .

# 4. Create initial structured commit
git commit -m "refactor: modularize loan management API and PDF engine into senior developer architecture"

# 5. Push to main branch
git branch -M main
git push -u origin main
```
