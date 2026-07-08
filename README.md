# Restaurant Menu Management System

This repository now contains a working full-stack starter for the restaurant digital menu platform described below.

## Stack choice

- **Backend:** Python + FastAPI + SQLModel + JWT auth + OTP demo flow
- **Frontend:** React + Vite + TypeScript for a fast, mobile-first dashboard experience
- **Database:** SQLite for local development (easy to swap to PostgreSQL via `BACKEND_DATABASE_URL`)

## Implemented modules

- Admin dashboard for chef/waitress provisioning, table management, occupancy monitoring, and audit visibility
- Chef dashboard for menu CRUD and availability control
- Waitress dashboard for assisted customer seating and offboarding
- Customer QR + OTP flow that unlocks the currently available menu with veg/non-veg filters
- Seed data for sample users, tables, categories, and menu items
- OpenAPI docs from FastAPI at `/docs`

## Run locally

### Backend

```bash
cd /home/runner/work/restaurant/restaurant/backend
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m app.seed
uvicorn app.main:app --reload
```

### Frontend

```bash
cd /home/runner/work/restaurant/restaurant/frontend
npm install
npm run dev
```

Copy `/home/runner/work/restaurant/restaurant/.env.example` to `.env` if you want to override defaults, especially the backend secret key for non-demo environments.

## Seeded credentials

- `admin / Admin@123`
- `chef1 / Password@123`
- `waitress1 / Password@123`

## Architecture summary

- Customers resolve a table from a QR payload, request an OTP, verify it, and receive a customer JWT.
- Chef and admin users manage menu data; waitress and admin users control occupancy.
- Every privileged action writes an audit record for traceability.
- FastAPI publishes the REST API and OpenAPI contract under `/api/v1`.

## Original build prompt

# Restaurant Menu System — Detailed Execution Prompt

You are a senior full-stack architect and lead developer.  
Design and implement a production-grade **Restaurant Menu Management System** with role-based access, QR table onboarding, OTP customer login, menu availability controlled by chef, and full CRUD workflows.

---

## 1) Business Goal

Build a restaurant digital menu platform where:

- Customers scan a QR code at a table and view the currently available menu.
- Chef manages menu item availability in real-time.
- Waitress manages table occupancy lifecycle and customer offboarding.
- Admin has full control over users, tables, and system settings.

The system must support secure authentication, strict RBAC, auditable actions, and clean API contracts.

---

## 2) Required Roles & Access Rules

Implement **4 roles**:

1. **Admin**
2. **Chef**
3. **Waitress**
4. **Customer**

### Role-wise authentication

- **Admin**: username + password
- **Chef**: username + password (credentials created only by Admin)
- **Waitress**: username + password (credentials created only by Admin)
- **Customer**: mobile number + OTP authentication only

### Role provisioning constraints

- Only **Admin** can create/update/deactivate **Chef** and **Waitress** accounts.
- Chef/Waitress cannot create other privileged users.
- Customer accounts are created/linked at OTP verification time.

---

## 3) Core Functional Requirements
- JWT-based auth (access + refresh tokens) or secure server sessions.
- OTP flow for customer:
  - Request OTP with mobile number.
  - Verify OTP.
  - On success, assign scanned table to authenticated customer.
- Implement RBAC middleware/guards on every protected endpoint.
- Enforce least privilege access for each role.

## 3.2 Table + QR Flow
- Every table has unique QR payload (e.g., table token / table_id / signed URL).
- Customer scans QR at table (example: Table 1), lands on customer onboarding page.
- After OTP verification:
  - table is assigned to the customer session.
  - customer can access current available menu for that table.
- Prevent double active assignment conflicts (configurable behavior):
  - either deny if occupied,
  - or allow waitress override.

## 3.3 Menu Management (Chef-Controlled Availability)
- Chef can CRUD menu items.
- Chef can mark availability:
  - available / unavailable
  - stock count (optional)
  - time-based availability (optional)
- Only available items are visible to customers.
- Waitress can view current live menu (read-only by default unless configured).

## 3.4 Customer Interface
- Show only currently available menu items.
- Support filters:
  - Veg
  - Non-veg
- Optional category filters (starters, main course, beverages, desserts).
- Mobile-first UI.

## 3.5 Waitress Interface
- View:
  - current menu availability
  - occupied/free table status
  - customer-to-table mapping
- Register a table for customer (assisted seating flow).
- Offboard customer when service is done:
  - close occupancy session
  - free table
- Waitress is the only non-admin role allowed to offboard customers.

## 3.6 Admin Control Panel
Admin has full controls over:
- Chef/Waitress user management (create/update/disable/reset password)
- Menu oversight (full CRUD/audit override)
- Table management (create/edit/deactivate tables, QR regeneration)
- Occupancy monitoring
- Audit logs and reports
- System configuration (OTP limits, session timeout, etc.)

---

## 4) Non-Functional Requirements

- Secure by default (OWASP practices).
- Scalable architecture (modular services).
- API-first design with versioning (`/api/v1`).
- Structured logging + audit trails for critical actions.
- Input validation and centralized error handling.
- Proper rate limiting (especially OTP endpoints).
- Observability readiness (health check, metrics, traces optional).

---

## 5) Suggested Tech Stack (can be adapted)

- **Frontend**: React / Next.js (role-based dashboards)
- **Backend**: Node.js (NestJS/Express) or Java Spring Boot
- **Database**: PostgreSQL
- **Cache/Queue**: Redis (OTP/session/rate limits)
- **Auth**:
  - JWT for staff users
  - OTP provider integration (Twilio/msg gateway) for customer
- **Storage**: S3/local for menu images
- **Deployment**: Docker + CI/CD

---

## 6) Data Model (Minimum)

Design normalized schema with constraints:

- `users`
  - id, role (ADMIN/CHEF/WAITRESS), username, password_hash, status, created_by, timestamps
- `customers`
  - id, mobile_number(unique), is_verified, last_login_at, timestamps
- `otp_requests`
  - id, mobile_number, otp_hash/code_ref, expires_at, attempts, status, created_at
- `tables`
  - id, table_number(unique), qr_code_value(unique), status(active/inactive), timestamps
- `table_sessions` (occupancy)
  - id, table_id, customer_id, started_at, ended_at, status(active/closed), assigned_by(waitress/admin/system), offboarded_by
- `menu_categories`
  - id, name, is_active
- `menu_items`
  - id, name, description, price, category_id, food_type(VEG/NON_VEG), is_available, stock_qty(optional), image_url, updated_by, timestamps
- `audit_logs`
  - id, actor_type(user/customer/system), actor_id, action, entity_type, entity_id, metadata, created_at

---

## 7) API Contract (High-Level)

Create REST APIs with OpenAPI docs.

### Auth
- `POST /api/v1/auth/login` (admin/chef/waitress username+password)
- `POST /api/v1/auth/refresh`
- `POST /api/v1/customer/auth/request-otp`
- `POST /api/v1/customer/auth/verify-otp`

### QR/Table
- `GET /api/v1/customer/table/resolve?qr=...`
- `POST /api/v1/customer/table/assign` (after OTP verify)
- `POST /api/v1/waitress/table/register-customer`
- `POST /api/v1/waitress/table/offboard`
- `GET /api/v1/waitress/tables/status`

### Menu
- `GET /api/v1/customer/menu?foodType=VEG|NON_VEG&available=true`
- `GET /api/v1/waitress/menu`
- `POST /api/v1/chef/menu-items`
- `PUT /api/v1/chef/menu-items/:id`
- `PATCH /api/v1/chef/menu-items/:id/availability`
- `DELETE /api/v1/chef/menu-items/:id`
- Admin override endpoints under `/api/v1/admin/...`

### Admin User Management
- `POST /api/v1/admin/users` (create chef/waitress)
- `PUT /api/v1/admin/users/:id`
- `PATCH /api/v1/admin/users/:id/status`
- `POST /api/v1/admin/users/:id/reset-password`

### Admin Tables
- `POST /api/v1/admin/tables`
- `PUT /api/v1/admin/tables/:id`
- `POST /api/v1/admin/tables/:id/regenerate-qr`
- `GET /api/v1/admin/tables`
