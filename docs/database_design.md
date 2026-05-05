# Database Design

This document describes the MariaDB schema for the LA-Server. Models live in [`app/models.py`](../app/models.py) (Flask-SQLAlchemy). On startup, [`init_db()`](../app/database.py) imports models and runs `db.create_all()` so the schema matches the code. You can also bootstrap an empty database with [`scripts/create_database.py`](../scripts/create_database.py) (creates the DB if needed and relies on the same `create_all()` path).

**Sign-in and tokens** are handled in the HTTP API ([`app/auth/`](../app/auth/)): passwords are verified against `authentications.password_hash`; successful login issues a **JWT** (not stored in this database). This document only covers **persisted** credential and profile data.

## Shared base (`BaseModel`)

All concrete tables inherit from `BaseModel` (`__abstract__ = True`):

| Column       | SQLAlchemy type                         | Notes                                      |
|-------------|-----------------------------------------|--------------------------------------------|
| `id`        | `Integer`, PK, autoincrement            | Surrogate key                              |
| `created_at`| `DateTime(timezone=True)`, default `utc_now` | Set on insert                         |
| `updated_at`| `DateTime(timezone=True)`, default `utc_now`, `onupdate=utc_now` | Refreshed on update |

## Tables overview

| Table              | Model            | Purpose |
|--------------------|------------------|---------|
| `companies`        | `Company`        | Employers / stations that offer jobs |
| `employees`        | `Employee`       | Camp participants in the Spielstadt (children and staff; each has an `employee_number`) |
| `authentications`  | `Authentication` | Optional 1:1 login profile per camp participant: password hash, forced password change flag, app permission group |
| `job_assignments`  | `JobAssignment`  | Links one camp participant (`employees` row) to one company for a placement |

---

## `companies`

| Column         | Type              | Constraints / default   |
|----------------|-------------------|-------------------------|
| `id`           | integer           | PK (from `BaseModel`)   |
| `company_name` | `String(255)`     | `NOT NULL`, `UNIQUE`    |
| `jobs_max`     | integer           | `NOT NULL`              |
| `hourly_pay` | integer           | `NOT NULL` (project units) |
| `active`       | boolean           | `NOT NULL`, default `true` |
| `notes`        | `Text`            | nullable                |
| `created_at`, `updated_at` | datetime (tz) | from `BaseModel` |

**Indexes:** primary key on `id`; unique constraint on `company_name`.

---

## `employees`

| Column            | Type              | Constraints / default   |
|-------------------|-------------------|-------------------------|
| `id`              | integer           | PK (from `BaseModel`)   |
| `first_name`      | `String(255)`     | `NOT NULL`              |
| `last_name`       | `String(255)`     | `NOT NULL`              |
| `employee_number` | `String(16)`      | `NOT NULL`, `UNIQUE`, indexed |
| `role`            | `String(255)`     | `NOT NULL`              |
| `active`          | boolean           | `NOT NULL`, default `true` |
| `notes`           | `Text`            | nullable                |
| `created_at`, `updated_at` | datetime (tz) | from `BaseModel` |

**Indexes:** primary key on `id`; unique index on `employee_number`.

**ORM:** `Employee.authentication` is an optional **one-to-one** to [`Authentication`](#authentications) (`uselist=False`; `passive_deletes=True` so the ORM relies on DB `ON DELETE CASCADE` when a participant row is removed).

Checksum validation for `employee_number` (ISO 7064 Mod 97,10) is **not** enforced in the database; it is applied in the HTTP API and bulk import when `VALIDATE_CHECK_SUM` is enabled. See [Employee numbers and check digits](./employee-numbers.md).

---

## `authentications`

| Column                 | Type              | Constraints / default                          |
|------------------------|-------------------|-----------------------------------------------|
| `id`                   | integer           | PK (from `BaseModel`)                         |
| `employee_id`          | integer           | `NOT NULL`, `UNIQUE`, FK → `employees.id`, `ON DELETE CASCADE` |
| `password_hash`        | `String(255)`     | `NOT NULL` (werkzeug hash; see behaviour)    |
| `password_must_change` | boolean           | `NOT NULL`, default `true`                   |
| `auth_group`           | `String(20)`      | `NOT NULL`, default `employee`                |
| `notes`                | `Text`            | nullable                                      |
| `created_at`, `updated_at` | datetime (tz) | from `BaseModel`                              |

**Indexes:** primary key on `id`; unique constraint on `employee_id` (at most one credential row per camp participant).

**ORM:** `Authentication.employee` ↔ `Employee.authentication`.

**Application values for `auth_group`:** `employee`, `staff`, and `admin` (enforced in the API; not an enum in the database).

---

## `job_assignments`

| Column        | Type        | Constraints / default                          |
|---------------|-------------|------------------------------------------------|
| `id`          | integer     | PK (from `BaseModel`)                          |
| `company_id`  | integer     | `NOT NULL`, FK → `companies.id`, `ON DELETE RESTRICT` |
| `employee_id` | integer     | `NOT NULL`, FK → `employees.id`, `ON DELETE RESTRICT` |
| `notes`       | `Text`      | nullable                                       |
| `created_at`, `updated_at` | datetime (tz) | from `BaseModel`                    |

**Indexes:** primary key on `id`; foreign keys on `company_id` and `employee_id`.

**ORM:** `JobAssignment` exposes `companies` → `Company` and `employees` → `Employee` (`back_populates` with `Company.job_assignments` and `Employee.job_assignments`). The attribute names are plural on the assignment side for historical reasons.

---

## Entity-relationship diagram

```mermaid
erDiagram
    companies {
        int id PK
        string company_name UK
        int jobs_max
        int hourly_pay
        boolean active
        text notes
        datetime created_at
        datetime updated_at
    }
    employees {
        int id PK
        string first_name
        string last_name
        string employee_number UK
        string role
        boolean active
        text notes
        datetime created_at
        datetime updated_at
    }
    authentications {
        int id PK
        int employee_id FK_UK
        string password_hash
        boolean password_must_change
        string auth_group
        text notes
        datetime created_at
        datetime updated_at
    }
    job_assignments {
        int id PK
        int company_id FK
        int employee_id FK
        text notes
        datetime created_at
        datetime updated_at
    }
    companies ||--o{ job_assignments : company_id
    employees ||--o{ job_assignments : employee_id
    employees ||--o| authentications : employee_id
```

---

## Behaviour notes

### Company (`companies`)

- Each row represents an **employer** in the Spielstadt that offers jobs.
- `company_name` must be unique.
- `jobs_max` caps concurrent assignments for that company (enforced with the API).
- `hourly_pay` is amount of money **camp participants** (children and staff in their Spielstadt roles) get for one hour of work.
- `active` marks whether the company is offering jobs. `notes` is optional free text.

### Employee (`employees`)

- Each row is a **camp participant** at the Spielstadt: **children** and **staff** use the same `employees` table and `employee_number`; `role` and `notes` record the distinction in practice.
- **Soft delete:** `active` defaults to `true`. Deleting a camp participant via the API (paths still say `employee`) normally sets `active` to `false` to preserve history; hard delete is a separate API path.
- Login capability is **not** implied by this table alone: see [`authentications`](#authentications).

### Authentication (`authentications`)

- At most one row per `employees.id`. **`ON DELETE CASCADE`:** if a camp participant row is **removed from the database**, their credential row is removed with it (API **soft delete** keeps the `employees` row, so the credential usually remains).
- `password_hash` holds a **werkzeug** hash ([`generate_password_hash`](https://werkzeug.palletsprojects.com/)); the application hashes with [`app/auth/utils.py`](../app/auth/utils.py) (`hash_password` lowercases the plain password before hashing, and `verify_password` lowercases on check), so **sign-in is case-insensitive**.
- `password_must_change`: when `true`, clients should drive the user through the documented **set-password** flow after login. The login API surfaces this flag in its JSON.
- `auth_group` is the **application permission** tier (`employee` / `staff` / `admin`), distinct from the descriptive camp **`role`** string on `employees`.
- **Initial password (not a separate column):** on **`POST /api/employees`**, CSV bulk import, and staff **`POST /api/auth/password/reset-password`**, the server sets `password_hash` from a hash of that participant’s **`employees.last_name`** (trimmed) and sets `password_must_change` to `true`. See the README [Initial password](../README.md#initial-password) section and [developer-guide.md](./developer-guide.md).

### Job assignment (`job_assignments`)

- Links one camp participant (`employees` row) to one company row.
- Foreign keys use **`ON DELETE RESTRICT`**: remove or reassign assignments before deleting a company or camp-participant row at the database level.
- Multiple `job_assignments` rows per camp participant are allowed over time; the **API** enforces at most one current assignment per camp participant when creating assignments.

### Soft-delete strategy

Prefer `employees.active = false` (and similar business rules for companies in the API) over physical deletes unless you intentionally hard-delete and have cleared dependent rows first.
