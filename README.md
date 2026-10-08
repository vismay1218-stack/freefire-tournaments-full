# 🏆 Free Fire Tournament Registration Website

A production-ready full-stack web application designed for Free Fire esports organizers and competitive teams. Features a modern dark gaming aesthetic with neon red/orange accents, real-time client & server validation, manual UPI payment verification workflow, authenticated admin control center, Excel data exports, and a public winners showcase.

---

## 🌟 Key Features

### 👤 Public User Panel
- **Tournament Discovery**: Browse active and upcoming tournaments with real-time capacity progress indicators, registration deadlines, prize pools, and entry fees.
- **3-Step Registration Wizard**:
  - **Step 1**: Team info, captain contact, and 4 player rosters with real-time inline validation (UID format, Level > 30, 10-digit Indian mobile number).
  - **Step 2**: Dynamic UPI payment instructions and entry fee details.
  - **Step 3**: Payment screenshot upload and transaction ID submission.
- **Privacy-Guarded Status Lookup**: Check registration approval status using Registration/Team ID and Captain Phone without risking cross-team data exposure.
- **Winners Showcase**: Public gallery of past champions with verifiable proof screenshots uploaded by organizers.

### 🛡️ Admin Management Panel
- **Security & Session Control**: Rate-limited admin login, hashed passwords, HTTPOnly session cookies, and CSRF protection.
- **Dashboard Metrics**: Live statistics on total tournaments, active events, pending payments, confirmed squads, and rejected entries.
- **Tournament CRUD**: Configure tournament format, maps (Bermuda, Purgatory, Kalahari), deadlines, entry fees, prize pools, rules, and lifecycle states (`DRAFT`, `OPEN`, `CLOSED`, `COMPLETED`).
- **Payment Verification Workflow**:
  - Review submitted transaction IDs and inspect payment screenshots (auth-protected).
  - **Approve**: Assigns official sequential Team ID (e.g. `PV-0001`), marks status as `CONFIRMED`, and locks capacity.
  - **Reject**: Records admin-specified rejection reason (e.g., unreadable slip, invalid transaction) visible to the applicant.
  - **Race-Safe Capacity Guard**: Prevents approving teams beyond `max_teams`.
- **Excel Export**: Download formatted `.xlsx` workbooks filtered by status (`all`, `confirmed`, `pending`, `rejected`) and tournament ID.
- **Winner Proofs**: Upload and toggle publication of winner trophies and tournament proof images.

---

## 📁 Project Directory Structure

```
freefire/
├── app/
│   ├── __init__.py               # Flask application factory, extension initializers
│   ├── cli/                      # Click CLI commands (create-admin)
│   │   ├── __init__.py
│   │   └── admin_cmd.py
│   ├── auth/                     # Authentication decorators & loaders
│   │   ├── __init__.py
│   │   └── admin.py
│   ├── models/                   # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── admin.py              # Admin credentials
│   │   ├── tournament.py         # Tournaments with status & capacity helpers
│   │   ├── registration.py       # Registrations & payment verification state
│   │   ├── player.py             # 4 squad players per registration
│   │   └── winner_proof.py       # Public winner proof banners
│   ├── routes/                   # Blueprints & route handlers
│   │   ├── admin_auth_routes.py  # Admin login, logout, rate limiting
│   │   ├── admin_dashboard_routes.py # Stats, recent entries, pending payments
│   │   ├── admin_tournaments_routes.py # Tournament CRUD
│   │   ├── admin_registrations_routes.py # Approve, reject, view details
│   │   ├── admin_winners_routes.py # Winner proofs management
│   │   ├── admin_export_routes.py # Excel workbook download
│   │   ├── public_routes.py      # Homepage, tournaments list, status lookup
│   │   ├── registrations_routes.py # Public registration submit & REST API
│   │   └── public_media_routes.py # Public winner banner delivery
│   ├── services/
│   │   ├── excel_service.py      # openpyxl workbook generator
│   │   └── upload_service.py     # Pillow verification & UUID file storage
│   ├── static/
│   │   ├── css/style.css         # Dark gaming theme & responsive CSS
│   │   └── js/
│   │       ├── main.js           # Navbar toggle & interactive UI helpers
│   │       └── registration.js   # Client-side 3-step wizard validation
│   └── templates/                # Jinja2 responsive templates
│       ├── base.html             # Base layout with navbar and footer
│       ├── admin/                # Admin templates (dashboard, CRUD, views)
│       ├── public/               # Public templates (home, details, wizard)
│       └── errors/               # Custom 404 and 500 error pages
├── exports/                      # Export directory
├── scripts/
│   └── e2e_smoke.py              # End-to-end zero-to-run automation test
├── tests/                        # Comprehensive Pytest test suite
│   ├── conftest.py               # Fixtures & in-memory test configuration
│   ├── test_auth.py              # Admin authentication & session security
│   ├── test_tournaments.py       # Tournament CRUD & deadline rules
│   ├── test_registration_validation.py # Phone, UID, Level, Duplicate rules
│   ├── test_registration_flow.py # Approval, rejection, capacity capping
│   ├── test_status_privacy.py    # Cross-team data isolation
│   ├── test_excel_export.py      # Openpyxl export & filter accuracy
│   ├── test_winners.py           # Winner upload & visibility
│   └── test_upload_security.py   # MIME inspection & auth guards
├── uploads/                      # Upload storage (gitignored except .gitkeep)
│   ├── payment_screenshots/     # Protected directory (not public)
│   └── winners_public/           # Publicly served via media route
├── .env.example                  # Environment configuration template
├── .gitignore                    # Version control ignore list
├── config.py                     # Configuration settings class
├── pytest.ini                    # Pytest configuration
├── requirements.txt              # Production & test dependencies
├── run.py                        # Local WSGI development server entrypoint
└── run_tests.bat                 # Windows one-click test execution batch script
```

---

## ⚙️ Prerequisites

- **Python**: Version 3.10, 3.11, 3.12, 3.13, or 3.14
- **pip**: Python package manager
- **Virtualenv**: Recommended for dependency isolation

---

## 🚀 Local Setup & Installation (Windows)

Follow these exact steps in Windows PowerShell or Command Prompt:

### 1. Clone & Enter Project Directory
```powershell
cd "c:\Users\Vismay C M\OneDrive\Desktop\freefire"
```

### 2. Create and Activate Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\activate
```

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
copy .env.example .env
```
*(Optionally edit `.env` to configure your custom `SITE_NAME`, `UPI_ID`, and `SECRET_KEY`.)*

### 5. Initialize the Database & Create Admin Account
```powershell
# Create an admin account (email + secure password)
flask create-admin admin@freefire.com Password123!
```

### 6. Start Development Server
```powershell
python run.py
```
Open your browser at:
- **Public Website**: [http://localhost:5000](http://localhost:5000)
- **Admin Login**: [http://localhost:5000/admin/login](http://localhost:5000/admin/login) (Credentials: `admin@freefire.com` / `Password123!`)

---

## 🧪 Testing Instructions

### Run the Automated Pytest Suite
Run all 32 automated unit, integration, and security tests:
```powershell
pytest -v
```
Or execute the Windows batch script:
```powershell
.\run_tests.bat
```

### Run the End-to-End Smoke Test
Verify the complete end-to-end lifecycle (app init -> admin creation -> tournament creation -> 2 public registrations -> approval & rejection -> Excel export validation -> status privacy):
```powershell
python scripts/e2e_smoke.py
```

---

## 🔒 Security Architecture

1. **Password Hashing**: Uses Werkzeug's secure PBKDF2/scrypt password hashing; plaintext passwords are never stored.
2. **Session Security**: Session cookies set with `HttpOnly=True` and `SameSite=Lax` to prevent XSS session theft.
3. **CSRF Protection**: All state-changing HTML forms (`POST`) require valid CSRF tokens provided by `Flask-WTF`.
4. **Rate Limiting**: Admin login is capped via `Flask-Limiter` (10 requests/minute) to stop brute-force attempts.
5. **Image Verification**:
   - Files are validated using Pillow (`PIL.Image.verify`) to check real magic bytes.
   - Disallowed extensions or renamed executables are rejected.
   - Saved files receive random UUID4 names (e.g., `d41d8cd98f00b204e9800998ecf8427e.png`) to avoid path traversal.
6. **Payment Screenshot Isolation**: Payment screenshots are saved in `uploads/payment_screenshots/`, completely outside `static/`. Unauthenticated visitors cannot view or download payment proofs.
7. **Status Privacy**: Public status checks require both the Registration ID and the captain's 10-digit phone number, completely preventing enumeration or cross-team data leaks.

---

## ☁️ Production Deployment Guide

### Deploying to Vercel (Recommended)
This Flask app uses Vercel's Python runtime. PostgreSQL and object storage are required because Vercel's function filesystem is temporary.

1. Push the project to a GitHub repository and import it from the Vercel dashboard.
2. Create a PostgreSQL database with Neon and copy its connection URL. Use the pooled connection URL when available.
3. Create a Supabase project and two **private** Storage buckets:
   - `payment-screenshots`
   - `winner-images`
4. In Vercel project settings, add these environment variables for Production (and Preview if needed):
   - `SECRET_KEY`: a long, random value
   - `FLASK_ENV`: `production`
   - `DATABASE_URL`: the Neon PostgreSQL URL (`postgresql://...`)
   - `ADMIN_EMAIL` and `ADMIN_PASSWORD`: your own admin credentials
   - `SUPABASE_URL`: the Supabase project URL
   - `SUPABASE_SERVICE_ROLE_KEY`: the server-side service role key; never expose it in browser code or commit it
   - `SUPABASE_PAYMENT_BUCKET`: `payment-screenshots`
   - `SUPABASE_WINNERS_BUCKET`: `winner-images`
   - `SITE_NAME`, `UPI_ID`, and `UPI_NAME`: your site and payment details
5. Deploy or redeploy after adding the variables. The app initializes its tables and creates/updates the configured admin account on startup.
6. Test registration, admin-only payment screenshot viewing, and winner image publishing. Keep both Supabase buckets private; the app serves published winner images and protects payment screenshots.

Vercel deployment fails early if required database, storage, or admin environment variables are missing. For local development, copy `.env.example` to `.env`; local uploads continue to use the `uploads/` directory.

### Deploying to Render (Alternative)
1. Push your repository to **GitHub**.
2. In [Render Dashboard](https://dashboard.render.com), create a new **Web Service**.
3. Connect your repository.
4. Set the following settings:
   - **Environment**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn -w 2 -b 0.0.0.0:$PORT run:app`
5. Under **Environment Variables**, set:
   - `SECRET_KEY`: Long random secret string
   - `DATABASE_URL`: Your PostgreSQL connection string
   - `SITE_NAME`: Your esports brand name
   - `UPI_ID`: Your payment UPI ID
   - `UPI_NAME`: Payee Name
6. Create an admin user via Render Shell:
   ```bash
   flask create-admin admin@yourbrand.com StrongPassword123!
   ```

### PostgreSQL Database Configuration
To switch from SQLite to PostgreSQL:
1. Provision a PostgreSQL instance (e.g. Render PostgreSQL, Supabase, Neon).
2. Set `DATABASE_URL` in `.env`:
   ```ini
   DATABASE_URL=postgresql://username:password@hostname:5432/dbname
   ```
3. The ORM models and migrations will automatically create and map tables on startup.
