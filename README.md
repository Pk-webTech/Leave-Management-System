# LeaveTrack — Leave Management System

<div align="center">

![LeaveTrack Banner](screenshots/login.png)

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Django](https://img.shields.io/badge/Django-5.2-092E20?style=flat-square&logo=django&logoColor=white)](https://djangoproject.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-7952B3?style=flat-square&logo=bootstrap&logoColor=white)](https://getbootstrap.com)
[![DRF](https://img.shields.io/badge/DRF-3.15-red?style=flat-square&logo=django&logoColor=white)](https://django-rest-framework.org)
[![License](https://img.shields.io/badge/License-Educational-blue?style=flat-square)](#license)

**A production-grade, role-based leave management system built with Django 5.2, featuring multi-level approval workflows, dynamic org-hierarchy, REST API, real-time AJAX quota checking, and automated email notifications.**

[Features](#-features) · [Tech Stack](#️-tech-stack) · [Architecture](#-architecture) · [Installation](#️-installation) · [API Docs](#-rest-api) · [Screenshots](#-screenshots)

</div>

---

## 📌 Overview

LeaveTrack is a full-stack Django web application that automates the entire lifecycle of employee leave management — from submission through multi-level hierarchical approval to email notification. It was built as a training assignment extending a base leave system with advanced Django concepts including signals, middleware, DRF, django-filter, AJAX, and token-based authentication.

### What makes it non-trivial

- **Dynamic org hierarchy** — manager chain is computed at runtime by walking a self-referential FK; no hardcoded L1/L2 fields. Adding a 3rd or 4th approval level requires zero schema changes.
- **Approval state machine** — `workflow.py` is a pure state machine (no side effects) that `process_leave_decision()` drives; views call it and handle emails based on the returned outcome.
- **Quota computed from source** — `LeaveQuota.used` and `.remaining` are `@property` methods that re-query `LeaveRequest` rows live, so cancellations and rejections automatically free up quota without any counter synchronization logic.
- **Security by default** — forced password change on first login (enforced by middleware at the request pipeline level, not just the view), token-based forgot-password flow, and auto-role assignment via signals.

---

## ✨ Features

### 🔐 Authentication & Security
| Feature | Implementation |
|---|---|
| Forced first-login password change | `must_change_password` flag + `ForcePasswordChangeMiddleware` blocks all pages until changed |
| Forgot password | Token-based reset link via `default_token_generator` + `urlsafe_base64` |
| Admin/Manager password reset | Generates temp password, forces change on next login, emails user |
| Auto role assignment | Signal-driven: new users start as Employee, auto-upgraded to Manager when someone reports to them |
| RBAC | Django `Group`-based (Admin / Manager / Employee) enforced via custom view decorators |
| Real SMTP email | Gmail App Password via `.env` + `python-dotenv`; falls back to console in dev |

### 🏢 Org Hierarchy
| Feature | Implementation |
|---|---|
| Dynamic manager chain | Self-referential `EmployeeProfile.manager` FK; chain walked at runtime by `get_manager_chain()` |
| Unlimited depth | `LEAVE_APPROVAL_MAX_LEVELS` setting controls depth; no schema change needed for more levels |
| Subordinate traversal | `get_all_subordinates()` recursively walks the org chart downward |

### 📋 Leave Workflow
| Feature | Implementation |
|---|---|
| Leave type yearly quotas | `LeaveQuota` model: 12 Casual / 10 Sick / 5 Emergency days per year (configurable) |
| Quota enforcement | `LeaveRequestForm.clean()` + DRF serializer `validate()` both enforce limits |
| Overlap prevention | Blocks applications whose dates intersect any existing PENDING/APPROVED request |
| Multi-level approval | `LeaveApproval` rows (one per level); L1 approves → auto-escalates to L2 |
| Rejection short-circuits | Any rejection terminates immediately; employee notified; never reaches next level |
| Real-time quota AJAX | Apply Leave form fetches `/api/leave-quota/check/` live — shows balance without reload |

### 📊 Reports & Dashboards
| Report | Scope |
|---|---|
| Admin Dashboard | Org-wide totals, recent leaves, recent users |
| Manager Dashboard | Team-scoped; splits "awaiting my approval" vs "awaiting others" |
| Team Leave Summary | Per-employee breakdown with used/remaining quota |
| Monthly Leave Stats | Bar chart by month for selected year |
| Leave Type Breakdown | Count + % share with progress bars |
| Hierarchy-aware filtering | All manager views scoped to their subordinate tree only |

### 🌐 REST API (DRF)
| Endpoint | Method | Description |
|---|---|---|
| `/api/leave-requests/` | GET | List leaves (own for employee, team for manager) with django-filter |
| `/api/leave-requests/` | POST | Submit a new leave request |
| `/api/leave-requests/<id>/` | GET | Leave request detail with full approval timeline |
| `/api/leave-requests/<id>/quick-action/` | POST | Approve/reject without page reload (AJAX) |
| `/api/leave-quota/` | GET | Current year quotas for authenticated user |
| `/api/leave-quota/check/` | GET | Real-time balance check (used by AJAX on Apply Leave form) |

### 📧 Email Notifications
| Trigger | Recipient |
|---|---|
| Account created | New user (includes temp password + login link) |
| Password reset (admin/manager initiated) | Affected user |
| Forgot password link | Requesting user |
| Password changed confirmation | Affected user |
| Leave applied | L1 Manager |
| Leave escalated | L2 (next-level) Manager |
| Leave fully approved | Employee |
| Leave rejected (at any level) | Employee (includes comment) |

---

## 🛠️ Tech Stack

### Backend
- **Python 3.11+** · **Django 5.2** (MVT monolith)
- **Django REST Framework 3.15** — API layer
- **django-filter** — declarative queryset filtering for API
- **python-dotenv** — environment variable management

### Frontend
- **Django Templates** (server-rendered, no SPA)
- **Bootstrap 5.3.2** + **Bootstrap Icons 1.11**
- **Vanilla JavaScript** + **Fetch API** (AJAX quota checking)
- **Google Fonts** — Inter

### Database
- **PostgreSQL 16** — primary datastore
- **Django ORM** only (no raw SQL)
- **Django Migrations** for schema versioning

### Auth & Security
- Django session-based auth + custom RBAC
- `default_token_generator` for password reset tokens
- Gmail SMTP via App Password (dev: console backend)

---

## 🏗️ Architecture

```
Browser
   │  HTTP
   ▼
Django Dev Server (WSGI)
   │
   ▼
Middleware Chain
  SecurityMiddleware → SessionMiddleware → CsrfViewMiddleware
  → AuthenticationMiddleware → ForcePasswordChangeMiddleware ★
  → MessageMiddleware → XFrameOptionsMiddleware
   │
   ▼
URL Router (leave_system/urls.py → leaveapp/urls.py)
   │
   ├── Traditional Views (leaveapp/views.py)  ←  RBAC decorators
   │     ├── Auth Views      (login, logout, force-change, forgot-pw, reset)
   │     ├── Admin Views     (dashboard, user management)
   │     ├── Manager Views   (approvals, reports, team)
   │     └── Employee Views  (dashboard, apply, my-leaves)
   │
   └── REST API (leaveapp/api_views.py)  ←  Token + Session auth
         ├── LeaveRequestListCreateAPIView
         ├── LeaveRequestDetailAPIView
         ├── LeaveQuotaAPIView
         ├── LeaveQuotaCheckAPIView  ←  AJAX target
         └── QuickLeaveActionAPIView ←  AJAX approve/reject
   │
   ▼
Business Logic Layer
  ├── workflow.py   — pure approval state machine
  ├── utils.py      — org hierarchy traversal, quota helpers
  ├── emails.py     — 8 notification builders → send_mail()
  └── filters.py    — MyLeaveFilter, TeamLeaveFilter (django-filter)
   │
   ▼
Data Models (Django ORM)
  ├── User / Group          (Django built-in)
  ├── EmployeeProfile       (manager FK → org hierarchy, must_change_password)
  ├── LeaveRequest          (type, dates, status, current_level)
  ├── LeaveApproval         (one row per approval level — unlimited depth)
  └── LeaveQuota            (yearly quota; used/remaining computed live)
   │
   ▼
PostgreSQL
```

### Key Design Decisions

**Why `LeaveApproval` rows instead of L1/L2 fields?**
Storing one row per approval level means bumping `LEAVE_APPROVAL_MAX_LEVELS` from 2 to 3 adds a 3rd level with zero schema changes. The `workflow.py` state machine handles any depth.

**Why compute quota live instead of storing a counter?**
`LeaveQuota.used` queries `LeaveRequest` rows with status `PENDING/APPROVED` at read time. When a request is cancelled or rejected, quota is automatically freed — no counter update needed, no possibility of drift.

**Why `ForcePasswordChangeMiddleware` instead of a view-level check?**
Middleware intercepts at the request pipeline level before any view runs. A user with `must_change_password=True` literally cannot reach any dashboard route regardless of how they construct the URL.

---

## 📂 Project Structure

```
Leave-Management-System/
│
├── leave_system/                  # Django project config
│   ├── settings.py                # All config including DRF, email, quotas
│   ├── urls.py                    # Project-level router
│   ├── wsgi.py
│   └── asgi.py
│
├── leaveapp/                      # Main application
│   ├── models.py                  # EmployeeProfile, LeaveRequest, LeaveApproval, LeaveQuota
│   ├── views.py                   # All traditional Django views (auth, admin, manager, employee)
│   ├── api_views.py               # DRF ViewSets and APIViews
│   ├── serializers.py             # DRF serializers
│   ├── filters.py                 # django-filter FilterSets
│   ├── workflow.py                # Leave approval state machine
│   ├── emails.py                  # Email notification builders
│   ├── utils.py                   # Org hierarchy helpers, quota utils
│   ├── middleware.py              # ForcePasswordChangeMiddleware
│   ├── decorators.py              # RBAC view decorators
│   ├── signals.py                 # Auto-create profile, seed quotas, sync roles
│   ├── forms.py                   # All Django forms with validation
│   ├── urls.py                    # App-level URL routing (traditional + API)
│   ├── admin.py                   # Customised Django Admin
│   └── migrations/
│       ├── 0001_initial.py
│       └── 0002_...
│
├── leaveapp/management/
│   └── commands/
│       └── seed_leave_quotas.py   # Backfill quotas for existing users
│
├── templates/
│   ├── base.html                  # Main layout with dynamic sidebar
│   ├── base_auth.html             # Auth pages layout
│   ├── login.html
│   ├── no_role.html
│   ├── auth/
│   │   ├── force_change_password.html
│   │   ├── forgot_password.html
│   │   ├── reset_password_confirm.html
│   │   └── reset_password_invalid.html
│   ├── admin/
│   │   ├── admin_dashboard.html
│   │   ├── user_list.html
│   │   ├── create_user.html
│   │   ├── confirm_delete.html
│   │   └── confirm_reset_password.html
│   ├── manager/
│   │   ├── manager_dashboard.html
│   │   ├── leave_requests.html
│   │   ├── leave_details.html     # Approval timeline + action panel
│   │   ├── reports.html           # Hierarchy-aware reports + monthly bar chart
│   │   ├── employee_history.html
│   │   ├── team.html
│   │   └── confirm_reset_password.html
│   └── employee/
│       ├── employee_dashboard.html # Live quota display
│       ├── apply_leave.html        # AJAX real-time quota checker
│       ├── my_leaves.html
│       ├── leave_detail.html       # Approval timeline view
│       └── confirm_cancel.html
│
├── static/
│   ├── css/main.css
│   ├── js/main.js
│   └── images/leavetrack_logo.png
│
├── screenshots/                   # UI screenshots
├── .env.example                   # Environment variable template
├── .gitignore
├── manage.py
├── requirements.txt
└── README.md
```

---

## 🗄️ Database Schema

```
┌─────────────────┐     ┌──────────────────────┐
│   auth_user     │────▶│   EmployeeProfile     │
│  (Django)       │     │  ─────────────────    │
│  id             │     │  user (1:1)           │
│  username       │     │  manager FK → User    │  ← org hierarchy
│  email          │     │  department           │
│  password       │     │  phone                │
│  groups (M:M)   │     │  must_change_password │
└─────────────────┘     └──────────────────────┘
         │
         │ 1:M
         ▼
┌─────────────────┐     ┌──────────────────────┐
│  LeaveRequest   │────▶│   LeaveApproval       │
│  ─────────────  │     │  ─────────────────    │
│  employee FK    │     │  leave_request FK     │
│  leave_type     │     │  level (1, 2, 3...)   │
│  start_date     │     │  approver FK          │
│  end_date       │     │  status               │
│  reason         │     │  comment              │
│  status         │     │  acted_on             │
│  current_level  │     └──────────────────────┘
│  manager_comment│
└─────────────────┘
         │
         │ computed
         ▼
┌─────────────────┐
│   LeaveQuota    │
│  ─────────────  │
│  employee FK    │
│  leave_type     │
│  year           │
│  total_quota    │
│  used  (@prop)  │  ← computed live from LeaveRequest
│  remaining      │  ← computed live from LeaveRequest
└─────────────────┘
```

---

## ⚙️ Installation

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Git
- Gmail account with 2-Step Verification enabled (for real emails)

### 1. Clone the repository

```bash
git clone https://github.com/Pk-webTech/Leave-Management-System.git
cd Leave-Management-System
```

### 2. Create and activate virtual environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / Mac
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env`:

```env
EMAIL_HOST_USER=your-gmail@gmail.com
EMAIL_HOST_PASSWORD=your-16-char-app-password
DEFAULT_FROM_EMAIL=LeaveTrack <your-gmail@gmail.com>
```

> **Gmail App Password**: Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) → create a new app password. Use this 16-character password, not your real Gmail password. Requires 2-Step Verification to be enabled.
>
> **Dev mode**: If `.env` is not configured, the app automatically falls back to the console email backend — emails print to the terminal.

### 5. Configure PostgreSQL

```python
# leave_system/settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'django_db',
        'USER': 'django_user',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### 6. Run migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Seed default leave quotas

```bash
python manage.py seed_leave_quotas
```

This creates `LeaveQuota` rows for all existing users:
- Casual Leave: 12 days/year
- Sick Leave: 10 days/year
- Emergency Leave: 5 days/year

### 8. Create superuser (Admin)

```bash
python manage.py createsuperuser
```

### 9. Run the development server

```bash
python manage.py runserver
```

Visit: **http://127.0.0.1:8000/**

---

## 🔐 Authentication Flows

### First Login (Temp Password)
```
Admin creates user
       ↓
System generates temp password → emails user
       ↓
User logs in with temp password
       ↓
ForcePasswordChangeMiddleware intercepts ALL requests
       ↓
User redirected to /force-change-password/
       ↓
User sets new password → must_change_password = False
       ↓
Dashboard access granted
```

### Forgot Password
```
User clicks "Forgot Password"
       ↓
Enters registered email
       ↓
System generates token → emails reset link (one-time use)
       ↓
User clicks link → /reset-password/<uidb64>/<token>/
       ↓
Sets new password → logged out → redirect to login
```

### Admin / Manager Password Reset
```
Admin/Manager clicks reset on a user
       ↓
System generates new temp password
       ↓
must_change_password = True → email sent
       ↓
User forced to change on next login
```

---

## 🔄 Leave Approval Workflow

```
Employee applies for leave
          ↓
  Quota check (form + API)
  Overlap check (form + API)
          ↓
    LeaveRequest created
    LeaveApproval (Level 1) created → L1 Manager emailed
          ↓
     L1 Manager reviews
      ╱           ╲
REJECTED          APPROVED
   ↓                 ↓
Employee         LeaveApproval (Level 2) created
notified         → L2 Manager emailed
                     ↓
              L2 Manager reviews
               ╱           ╲
          REJECTED      APPROVED (Final)
             ↓               ↓
          Employee        Employee
          notified        notified
```

> The depth is controlled by `LEAVE_APPROVAL_MAX_LEVELS = 2` in `settings.py`. Change to 3 to add a third level — no model changes needed.

---

## 🌐 REST API

### Authentication

The API supports both **Token authentication** (for external clients) and **Session authentication** (for the browsable API in browser).

**Get your API token:**
```bash
curl -X POST http://127.0.0.1:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "your_password"}'
```

**Use the token:**
```bash
curl http://127.0.0.1:8000/api/leave-requests/ \
  -H "Authorization: Token your_token_here"
```

### Endpoints

#### List / Create Leave Requests
```
GET  /api/leave-requests/
POST /api/leave-requests/
```

**Filter parameters (GET):**
| Param | Type | Description |
|---|---|---|
| `status` | string | `PENDING`, `APPROVED`, `REJECTED`, `CANCELLED` |
| `leave_type` | string | `Casual Leave`, `Sick Leave`, `Emergency Leave` |
| `start_date_from` | date | Filter by start date ≥ |
| `start_date_to` | date | Filter by start date ≤ |
| `employee_name` | string | Search by name/username (manager view only) |

**POST body:**
```json
{
  "leave_type": "Casual Leave",
  "start_date": "2026-07-01",
  "end_date": "2026-07-03",
  "reason": "Family function"
}
```

#### Leave Request Detail
```
GET /api/leave-requests/<id>/
```

**Response includes full approval timeline:**
```json
{
  "id": 42,
  "employee": { "id": 5, "username": "john", "full_name": "John Doe", "email": "john@example.com" },
  "leave_type": "Casual Leave",
  "start_date": "2026-07-01",
  "end_date": "2026-07-03",
  "status": "PENDING",
  "current_level": 2,
  "duration": 3,
  "approvals": [
    { "level": 1, "approver": { "username": "manager1" }, "status": "APPROVED", "acted_on": "2026-06-27T10:30:00Z" },
    { "level": 2, "approver": { "username": "director1" }, "status": "PENDING", "acted_on": null }
  ]
}
```

#### Quick Approve/Reject (AJAX)
```
POST /api/leave-requests/<id>/quick-action/
```
```json
{
  "decision": "APPROVED",
  "comment": "Approved. Enjoy your time off."
}
```
**Response:**
```json
{
  "outcome": "final_approved",
  "message": "Leave request fully approved.",
  "new_status": "APPROVED",
  "leave_id": 42
}
```

#### Leave Quota
```
GET /api/leave-quota/
GET /api/leave-quota/check/?leave_type=Casual+Leave&days=3&year=2026
```
**Check response:**
```json
{
  "leave_type": "Casual Leave",
  "total_quota": 12,
  "used": 5,
  "remaining": 7,
  "requested_days": 3,
  "sufficient": true
}
```

---

## 📊 Key Django Concepts Demonstrated

| Concept | Where |
|---|---|
| Custom Middleware | `leaveapp/middleware.py` — `ForcePasswordChangeMiddleware` |
| Django Signals | `leaveapp/signals.py` — auto-create profile, seed quotas, sync roles |
| Custom Decorators | `leaveapp/decorators.py` — RBAC enforcement |
| Advanced ORM | Hierarchy queries, annotate/Count, computed properties, Q objects |
| Django Forms + Validation | `leaveapp/forms.py` — quota check + overlap validation in `clean()` |
| Token-based Auth | DRF `TokenAuthentication` for API access |
| Django REST Framework | `api_views.py` — `ListCreateAPIView`, `RetrieveAPIView`, `APIView` |
| DRF Serializers | `serializers.py` — nested serializers, `SerializerMethodField`, custom `validate()` |
| django-filter | `filters.py` — `MyLeaveFilter`, `TeamLeaveFilter` with `CharFilter`, `DateFilter`, custom methods |
| AJAX + Fetch API | `apply_leave.html` — real-time quota check without page reload |
| JSON Responses | `LeaveQuotaCheckAPIView`, `QuickLeaveActionAPIView` |
| Partial UI Updates | Quota banner updates live on type/date change |
| Email (SMTP + Console) | `leaveapp/emails.py` → `send_mail()` → Gmail/console |
| Management Commands | `seed_leave_quotas` — custom `BaseCommand` |
| Template Inheritance | `base.html` + `base_auth.html` with role-aware dynamic sidebar |

---

## 👥 Default Leave Quotas

Configurable in `settings.py`:

```python
DEFAULT_LEAVE_QUOTAS = {
    'Casual Leave': 12,    # days/year
    'Sick Leave': 10,      # days/year
    'Emergency Leave': 5,  # days/year
}
```

---

## 📸 Screenshots

### Login Page
![Login](screenshots/login.png)

### Admin Dashboard
![Admin Dashboard](screenshots/Admin_dashboard.png)

### User Management
![User Management](screenshots/Manage_user.png)

### Create User (Auto Role Assignment)
![Create User](screenshots/Create_user.png)

### Manager Dashboard
![Manager Dashboard](screenshots/Manager_dashboard.png)

### Apply Leave (Real-time Quota AJAX)
![Apply Leave](screenshots/leave_apply.png)

### Leave Approval / Rejection
![Leave Approval](screenshots/Leave_approve_reject.png)

### Hierarchy-Aware Reports
![Reports](screenshots/Leave_report.png)

### Employee Dashboard
![Employee Dashboard](screenshots/Employee_dashboard.png)

---

## 🔧 Configuration Reference

| Setting | Default | Description |
|---|---|---|
| `LEAVE_APPROVAL_MAX_LEVELS` | `2` | Number of approval levels before final approval |
| `DEFAULT_LEAVE_QUOTAS` | `{Casual: 12, Sick: 10, Emergency: 5}` | Default yearly quota per leave type |
| `EMAIL_BACKEND` | Auto (console if no `.env`, SMTP if configured) | Django email backend |
| `EMAIL_HOST` | `smtp.gmail.com` | SMTP host |
| `EMAIL_PORT` | `587` | SMTP port (TLS) |

---

## 👨‍💻 Author

**Piyush Kumar**
B.Tech CSE (Information Security) · VIT Vellore
---
## 📜 License

This project is developed for educational purposes as part of a structured Django training program.
