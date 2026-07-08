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

## 3.1 Authentication & Authorization
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

Add indexes on:
- mobile_number, table_number, qr_code_value, active table sessions, menu availability.

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

---

## 8) Critical Business Rules

1. Customer can access menu only after successful OTP verification.
2. Table assignment requires valid QR context or waitress registration.
3. Only one active customer session per table (unless override policy enabled).
4. Chef controls menu availability; unavailable items never shown to customer.
5. Waitress can offboard customer and close session; closure frees table immediately.
6. Admin can perform all actions, including emergency overrides.
7. All privileged actions must be audit logged.

---

## 9) Security Requirements

- Passwords hashed with bcrypt/argon2.
- OTP expiration (e.g., 2–5 min), retry limits, resend cooldown.
- Rate limits per IP + mobile for OTP endpoints.
- JWT expiration + refresh rotation.
- CSRF/XSS/CORS protections as applicable.
- Encrypt sensitive data at rest where needed.
- Avoid exposing internal IDs in QR payload without signing.

---

## 10) UI/UX Modules

- **Admin Dashboard**
  - user management
  - table management + QR generation
  - menu supervision
  - logs/reports
- **Chef Dashboard**
  - add/edit/delete items
  - toggle availability quickly
  - stock-aware status indicators
- **Waitress Dashboard**
  - live table occupancy board
  - register customer to table
  - offboard workflow
  - view current menu
- **Customer Web View (QR)**
  - mobile login via OTP
  - table confirmation
  - menu list + veg/non-veg filters

---

## 11) Edge Cases to Handle

- OTP expired / invalid / too many attempts.
- QR invalid or table inactive.
- Table already occupied when customer verifies OTP.
- Chef marks item unavailable while customer is browsing.
- Waitress tries to offboard already closed session.
- Network retries causing duplicate assignments (ensure idempotency keys or transactional locks).

---

## 12) Testing Strategy

- Unit tests for services/validators/guards.
- Integration tests for auth, table assignment, RBAC, menu visibility.
- E2E tests:
  1. QR scan -> OTP -> table assignment -> menu view.
  2. Chef toggles availability -> customer menu reflects instantly.
  3. Waitress register + offboard lifecycle.
  4. Admin creates chef/waitress and verifies access.
- Security tests for auth and OTP abuse prevention.

---

## 13) Delivery Plan (Milestones)

1. Project setup + DB schema + auth scaffolding.
2. Admin user management for chef/waitress.
3. Customer OTP + QR table assignment.
4. Chef menu CRUD + availability controls.
5. Waitress occupancy/offboarding flows.
6. Customer menu filters and UI polish.
7. Audit logs, hardening, and test completion.
8. Production deployment + runbook.

---

## 14) Definition of Done

The implementation is complete only when:

- All role-based login mechanisms work as specified.
- Admin-only creation of chef/waitress credentials is enforced.
- Customer OTP auth and automatic table assignment works via QR flow.
- Chef can control live menu availability.
- Waitress can monitor occupancy, register, and offboard customers.
- Customer sees only available menu with veg/non-veg filters.
- Admin has full controls and audit visibility.
- Test suite passes and API documentation is published.

---

## 15) Output Requirements for the Implementer

Produce:

1. Architecture diagram (logical components + data flow)
2. DB schema (ERD + SQL migrations)
3. OpenAPI specification
4. Backend implementation with RBAC and OTP workflows
5. Frontend role-based dashboards/views
6. Seed scripts (admin + sample tables/menu)
7. Test reports (unit/integration/E2E)
8. Deployment guide and `.env.example`
9. Postman/Insomnia collection
10. Operational runbook (monitoring, rollback, incident steps)
