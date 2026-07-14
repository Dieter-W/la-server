# Developer Guide

## Overview

The **LA-Server** (Kinderspielstadt Los Ämmerles) is a Flask application backed by **MariaDB**. It exposes a JSON REST API for companies, **camp participants** (children and staff; “employees” in paths and JSON), daily **check-in / check-out** attendance, job assignments during the summer camp, and **Spielstadt branding / configuration** (read from `village_data/` on the server: `village.ini` plus static images). Clients (e.g. gate scanners and job center apps) call these endpoints over HTTP.

For environment variables, production setup (`setup.ps1` / `setup.sh` with `init-env` or `provision`), **`village_data/`** layout, and CSV bulk import, see the main [README.md](../README.md). A short pointer to this development guide is under *Development* in the [README](../README.md).

---

# Client developer (API usage)

## Base URL

By default the server listens on **`http://localhost:5000`**. In deployment, use `http://<HOST>:<PORT>` where `HOST` and `PORT` come from `.env` (see [.env.example](../.env.example)). TLS termination is assumed to happen in a reverse proxy if you serve HTTPS.

## Authentication

**Normative reference:** Full **request/response shapes and HTTP status codes** for every auth route are under **[Auth API](#auth-api)** — start with [Login service](#login-service) and [Me service](#me-service), then the `POST` operations in that section. **This heading** explains **how JWTs fit into client calls** and includes a **short walkthrough**; it is **not** the complete specification for each endpoint.

As a **client developer**, you are responsible for the sign-in experience, for **keeping tokens safe**, and for **attaching the right credential on every API call** that requires it. The camp issues accounts (linked to a participant and a company in the server’s data model; see [`app/models.py`](../app/models.py)); your app collects the user name and password only during sign-in and password flows, not on ordinary data requests.

**Tokens after sign-in (short):** a successful **`POST /api/auth/login`** returns **two** opaque JWT strings: **`token`** (short-lived **access**) and **`refresh_token`** (long-lived **refresh**). Both encode claims such as **`auth_group`** (`employee`, `staff`, or `admin`—not the descriptive camp **`role`** on the participant) and **`employee_number`**, plus **expiry** (lifetime differs between access and refresh; see [`app/config.py`](../app/config.py)). Company and full profile fields come from API responses (for example **`GET /api/auth/me`**), not from decoding the payloads yourself.

- Use **`token`** as **`Authorization: Bearer …`** on almost every protected route.
- **`POST /api/auth/refresh`** is different: send **`Authorization: Bearer <refresh_token>`** — the Bearer value must be the **refresh** JWT returned at login, **not** the access token.

Do not modify JWT strings yourself; rotate them only via the documented endpoints.

**What you do on a normal API call**

1. **Use HTTPS** in real deployments so tokens are not exposed on the network.
2. **Send the access JWT** (`token`) on each request that requires authentication: add an HTTP header
   `Authorization: Bearer <your_access_token>`
   (replace `<your_access_token>` with the stored access JWT, no quotes). Omit this header only for calls that the server documents as public (for example some health checks).
3. **Do not** send the user’s password on regular CRUD calls—only where the server explicitly expects it (sign-in, password set/change, etc., when those flows are documented).
4. If the server rejects a request because the **access** token is missing, invalid, or **expired**, but your **refresh** token is **still valid**, call **`POST /api/auth/refresh`** with **`Authorization: Bearer <refresh_token>`**; the response carries a **new** access **`token`** (see [Refresh session](#refresh-session)). Replace the stored access token and **retry** the original request with the updated Bearer header.
5. If the **refresh** token is **expired** or unusable—or you no longer have it—**sign in again** to obtain new **`token`** and **`refresh_token`**.

**Sign-in and token storage:** persist **both** values in **secure storage** for your platform (not plain logs, not easy-to-read app bundles): keep the access JWT for ordinary API calls, and keep the refresh JWT **only** for calling **`POST /api/auth/refresh`** (same header name—do not confuse the two). After a successful refresh, replace the stored **access** `token`; the server does **not** return a new **`refresh_token`** on refresh, so retain the existing refresh JWT until login again or it expires.

**Expiry:** treat a short-lived access token as routine: refresh with a valid **`refresh_token`**, then continue with a fresh Bearer access token on data calls. Plan for **re-login** when both tokens are no longer acceptable.

**Sign-out:** clear all stored tokens from the device and return the user to the sign-in screen. Unless the server documents a separate revoke step, assume the main effect is on the client side.

**Password changes:** the camp may reset an account or ask the user to set a password the first time; changing an existing password should still require the old password when the account is already active. After a successful password flow, the server may issue new tokens—replace your stored JWTs accordingly. Password checks use the same **case-insensitive** comparison as sign-in ([`hash_password` / `verify_password` in `app/auth/utils.py`](../app/auth/utils.py)); use lowercase when testing to avoid surprises.

**Deployment note:** some environments may still rely on a private network or proxy in addition to JWTs. Your integration should still follow the header rule above whenever the server expects a bearer token.

### Example walkthrough - /api/auth/login and /api/auth/me

*Illustrative walkthrough only; exact fields and status codes are in **[Auth API](#auth-api)** ([Login service](#login-service), [Me service](#me-service)).*

Use a real **employee number** (with valid ISO 7064 Mod 97,10 checksum when `VALIDATE_CHECK_SUM` is on; see [employee-numbers.md](./employee-numbers.md)) and base URL.

**1. Sign in** — `POST /api/auth/login` with JSON `employee_number` and `password`. On success the body includes **`token`** (short-lived access JWT) and **`refresh_token`** (long-lived refresh JWT).

```http
POST /api/auth/login HTTP/1.1
Host: localhost:5000
Content-Type: application/json

{"employee_number": "M00155", "password": "your-password"}
```

```bash
curl -s -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"employee_number":"M00155","password":"your-password"}'
```

**JSON response** (success)

```json
{
  "message": "Authenticated",
  "token": "<jwt-access-token>",
  "refresh_token": "<jwt-refresh-token>",
  "auth_group": "employee",
  "password_must_change": false
}
```

Store **`token`** and **`refresh_token`** securely. Use **`token`** as **`Authorization: Bearer …`** on **`GET /api/auth/me`** and other protected routes; do **not** put the refresh JWT on those headers—send it **only** on **`POST /api/auth/refresh`** as **`Authorization: Bearer <refresh_token>`**. After a refresh, replace the saved **`token`** with the one from the refresh response ([Refresh session](#refresh-session)).

**2. Current user** — `GET /api/auth/me` with the access token:

```http
GET /api/auth/me HTTP/1.1
Host: localhost:5000
Authorization: Bearer <jwt-access-token>
```

```bash
TOKEN="<paste-token-from-login>"
curl -s http://localhost:5000/api/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

**JSON response** (success — fields match the employee record plus session `auth_group`)

```json
{
  "id": 1,
  "first_name": "Ada",
  "last_name": "Example",
  "employee_number": "M00155",
  "age": 10,
  "can_leave_alone": true,
  "role": "participant",
  "company": "Example Co",
  "active": true,
  "notes": null,
  "created_at": "2025-06-01T10:00:00",
  "updated_at": "2025-06-01T10:00:00",
  "full_time": false,
  "workday": "today",
  "shift": "morning",
  "checked_in": false,
  "auth_group": "employee"
}
```

## Errors and status codes

- Most validation and not-found cases use response body `{"error": "<CODE>"}` and an HTTP status (often `400`, `404`).
- Database constraint issues may return `**409`** with `{"error": "CONSTRAINT_VIOLATION", "message": "Create failed, because entry is already in database"}` (duplicate / unique violation) or `{"error": "CONSTRAINT_VIOLATION", "message": "Delete failed, because related entries in JobAssignment table"}` (delete blocked by related rows), as implemented in [`app/errors.py`](../app/errors.py).
- Uncaught DB errors: `**500**` with `DATABASE_ERROR`. Unhandled exceptions: `**500**` with `INTERNAL_SERVER_ERROR`, per [`app/errors.py`](../app/errors.py). For both, a **`message`** field is included in the JSON **only when** server **`DEBUG`** is enabled (otherwise the body is just `{"error": "<CODE>"}`).

**Common error codes** include: `REQUEST_BODY_MUST_BE_A_JSON_OBJECT`, `REQUEST_BODY_NOT_ALLOWED`, `REQUIRED_JSON_INPUT_MISSING_OR_EMPTY`, `INVALID_AGE_IN_JSON`, `INVALID_JSON_BOOLEAN_IN_JSON`, `INVALID_PART_TIME_WORKDAY`, `INVALID_PART_TIME_SHIFT`, `INVALID_PART_TIME_COMBINATION`, `INVALID_JOBS_MAX`, `INVALID_ATTENDANCE_WORKDAY`, `PART_TIME_NOT_FOUND`, `COMPANY_JOBS_MAX_NOT_FOUND`, `COMPANY_NOT_FOUND`, `EMPLOYEE_NOT_FOUND`, `COMPANY_NOT_ACTIVE`, `EMPLOYEE_NOT_ACTIVE`, `ATTENDANCE_NOT_CHECKED_IN`, `ATTENDANCE_CHECK_IN_REQUIRED`, `JOB_ALREADY_ASSIGNED`, `NO_JOB_LEFT`, `NO_JOB_ASSIGNED`, `EMPLOYEE_NUMBER_WRONG`, `BAD_CREDENTIALS`, `FORBIDDEN_WRONG_AUTH_GROUP`, `OLD_PASSWORD_IS_INCORRECT`, `AUTHORIZATION_REQUIRED`, `EXPIRED_TOKEN`, `INVALID_TOKEN`, `DATABASE_ERROR`, `INTERNAL_SERVER_ERROR`, and variants with `_IN_JSON` where applicable.

JWT responses from Flask-JWT-Extended include a `message` next to `error` where applicable; see [`app/__init__.py`](../app/__init__.py). **HTTP mapping:** missing `Authorization` / Bearer → **`401`** `AUTHORIZATION_REQUIRED`; expired JWT → **`401`** `EXPIRED_TOKEN`; malformed or invalid Bearer / wrong token type for the loader → **`422`** `INVALID_TOKEN`.

For **village / Spielstadt config** endpoints: `VILLAGE_DATA_NOT_FOUND` (missing `village_data/village.ini`), `VILLAGE_LOGO_NOT_CONFIGURED` / `VILLAGE_FAVICON_NOT_CONFIGURED` (INI lacks the key under `[village-images]`), `FILE_NOT_FOUND` (path in INI points to a file that does not exist on disk), `INVALID_FILE_PATH` (unsafe or absolute path in INI), `VILLAGE_DATA_INVALID` (INI parse failure on the server).

## Employee numbers and checksums

When `VALIDATE_CHECK_SUM=true` in `.env` (default), employee numbers must satisfy the **ISO 7064 Mod 97,10** checksum on paths and JSON fields that carry `employee_number`. See [employee-numbers.md](./employee-numbers.md). Set `VALIDATE_CHECK_SUM=false` only for local testing if needed.

---

## Endpoint index

In the table, **Authorization** is shorthand for:

- **public** — no sign-in needed.
- **employee or higher** — signed in as a camp participant (any normal login).
- **staff or higher** — signed in as staff or admin.
- **admin required** — signed in as an admin.

If an admin changes another person’s access (`POST /api/auth/set-auth-group`), that person should **sign in again** so the app remembers the new permissions.

**List endpoints (no pagination):** `GET /api/companies`, `GET /api/employees`, `GET /api/job-assignments`, and staff-only `GET /api/job-assignment-history` return the **full** result set in one response (no `limit`/`offset`). Plan accordingly for large datasets or future API versions.

| Method | Path                                           | Summary                                     | Authorization                    |
| ------ | ---------------------------------------------- | ------------------------------------------- | -------------------------------- |
| GET    | `/api/health`                                  | Liveness                                    | public                           |
| GET    | `/api/health/db`                               | Database connectivity                       | public                           |
| GET    | `/api/health/runtime`                          | Pool, peaks, redacted DB (no customer data) | admin required                   |
| POST   | `/api/auth/login`                              | Sign in                                     | public                           |
| GET    | `/api/auth/me`                                 | Current employee profile                    | employee or higher               |
| POST   | `/api/auth/set-auth-group`                     | Change another user’s permission level      | admin required                   |
| POST   | `/api/auth/password/set-password`              | Change password                             | employee or higher               |
| POST   | `/api/auth/password/reset-password`            | Reset password to initial value             | staff or higher                  |
| POST   | `/api/auth/refresh`                            | Refresh session token                       | employee or higher               |
| POST   | `/api/auth/logout`                             | Logout                                      | employee or higher               |
| GET    | `/api/companies`                               | List companies                              | public                           |
| GET    | `/api/companies/<company_name>`                | List one company                            | public                           |
| POST   | `/api/companies`                               | Create company                              | admin required                   |
| PUT    | `/api/companies/<company_name>`                | Update company                              | admin required                   |
| DELETE | `/api/companies/<company_name>`                | Delete company                              | admin required                   |
| GET    | `/api/company-jobs-max/<company_name>`         | List stored job-capacity schedule rows      | public                           |
| POST   | `/api/company-jobs-max/<company_name>`         | Create schedule row                         | admin required                   |
| PUT    | `/api/company-jobs-max/<company_name>`         | Update schedule row                         | admin required                   |
| DELETE | `/api/company-jobs-max/<company_name>`         | Delete all schedule rows                    | admin required                   |
| DELETE | `/api/company-jobs-max/<company_name>?workday=&shift=` | Delete one schedule row           | admin required                   |
| GET    | `/api/employees`                               | List employees                              | public                           |
| GET    | `/api/employees/<employee_number>`             | List one employee                           | public                           |
| POST   | `/api/employees`                               | Create employee                             | admin required                   |
| PUT    | `/api/employees/<employee_number>`             | Update employee                             | admin required                   |
| DELETE | `/api/employees/<employee_number>`             | Soft or hard delete employee                | admin required                   |
| GET    | `/api/part-time/<employee_number>`             | List stored part-time rows                  | public                           |
| POST   | `/api/part-time/<employee_number>`             | Create part-time row                        | admin required                   |
| PUT    | `/api/part-time/<employee_number>`             | Update part-time row                        | admin required                   |
| DELETE | `/api/part-time/<employee_number>`             | Delete all part-time rows                   | admin required                   |
| DELETE | `/api/part-time/<employee_number>?workday=`    | Delete one part-time row                    | admin required                   |
| POST   | `/api/attendance/check-in/<employee_number>`   | Record check-in for camp today              | staff or higher                  |
| POST   | `/api/attendance/check-out/<employee_number>`  | Record optional check-out for camp today    | staff or higher                  |
| GET    | `/api/attendance/check-ins?workday=`           | List check-ins for a camp day               | public                           |
| GET    | `/api/attendance/check-outs?workday=`          | List check-outs for a camp day              | public                           |
| GET    | `/api/attendance/<employee_number>`            | Attendance history (optional day filter)    | public                           |
| GET    | `/api/job-assignments`                         | List job assignments                        | public                           |
| POST   | `/api/job-assignments`                         | Create job assignment                       | employee or higher               |
| DELETE | `/api/job-assignments/<job_assignment_number>` | Remove assignment by assignment number      | employee or higher               |
| POST   | `/api/job-assignments/reset`                   | Reset assignments (optional filter)         | admin required                   |
| GET    | `/api/job-assignment-history`                  | List archived employment snapshots (optional filters) | staff or higher          |
| GET    | `/api/job-assignment-history/export`           | Download filtered history as CSV            | staff or higher                  |
| GET    | `/api/job-assignment-history/<employee_number>` | One participant's employment history       | staff or higher                  |
| GET    | `/api/job-assignment-history/<employee_number>/export` | Download one participant's history as CSV | staff or higher          |
| GET    | `/api/village-data`                            | Spielstadt config JSON (`village.ini`)      | public                           |
| GET    | `/api/village-data/logo`                       | Logo image (path from INI)                  | public                           |
| GET    | `/api/village-data/favicon`                    | Favicon image (path from INI)               | public                           |
| GET    | `/api/openapi.json`                            | OpenAPI 3.0 schema (machine-readable)       | public                           |
| GET    | `/api/docs`                                    | Swagger UI (interactive explorer)           | public                           |


## OpenAPI / Swagger

- **`GET /api/openapi.json`** — OpenAPI 3.0 document generated from [`app/openapi_spec.py`](../app/openapi_spec.py).
- **`GET /api/docs`** — Swagger UI in the browser (UI assets from a CDN). Use **Authorize** with the **access** JWT from login: the **`token`** field from **`POST /api/auth/login`** (paste the token only; Swagger UI adds the `Bearer` prefix for the `bearerAuth` scheme). That matches almost all protected operations.
- **Refresh vs Authorize:** **`POST /api/auth/refresh`** must send the **refresh** JWT (`refresh_token` from login) in **`Authorization: Bearer …`**, not the access token. Swagger UI exposes a **single** global **Authorize** value for `bearerAuth`, so it cannot hold access and refresh at once. For **Try it out** on **refresh**, either temporarily replace **Authorize** with the refresh token, or call the endpoint with a client or manual header that sends the refresh JWT.

Operation summaries and security in the spec mirror this guide; exact JSON bodies, status codes, and error `error` codes are documented in the sections below.

Each operation below uses the same blocks: **Explanation**, **Parameters**, **Endpoint sample**, **JSON request** (if any), **JSON response** (if any), **HTTP status codes**. When the index marks a route as **employee or higher**, **staff or higher**, or **admin required**, add **`Authorization: Bearer <token>`** (see [**Authentication**](#authentication)); many samples below already show that header—if one omits it, add it when the route is protected.

---

## Health

The `GET /api/health` and `GET /api/health/db` APIs are for client developers to validate the communication with the server works **correctly**. The third API (`GET /api/health/runtime`) provides runtime information, which **is** usually not needed by a client developer.

### Liveness - /api/health

**Explanation**
Returns a simple JSON payload so load balancers and monitors can verify the process is up. Does not check the database.

**Parameters**
None.

**Endpoint sample**

```http
GET /api/health HTTP/1.1
Host: localhost:5000
```

```bash
curl -s http://localhost:5000/api/health
```

**JSON request**
None.

**JSON response** (example)

```json
{
  "status": "ok",
  "service": "Kinderspielstadt Los Ämmerles - LA-Server"
}
```

**HTTP status codes**


| Code | Meaning |
| ---- | ------- |
| 200  | OK      |


---

### Database connectivity - /api/health/db

**Explanation**
Runs `SELECT 1` against the configured database to verify connectivity.

**Parameters**
None.

**Endpoint sample**

```http
GET /api/health/db HTTP/1.1
Host: localhost:5000
```

```bash
curl -s http://localhost:5000/api/health/db
```

**JSON request**
None.

**JSON response** (success)

```json
{
  "status": "ok",
  "database": "connected"
}
```

**JSON response** (failure — body shape may include error detail)

```json
{
  "status": "error",
  "database": "<driver error message>"
}
```

**HTTP status codes**


| Code | Meaning            |
| ---- | ------------------ |
| 200  | Database reachable |
| 503  | Query failed       |


---

### Runtime diagnostics - /api/health/runtime

**Explanation**
Returns **operational** JSON for debugging and monitoring: process/runtime facts (Python version, platform, PID, app uptime), non-secret config flags (`DEBUG`, `TESTING`, `LOG_LEVEL`), a **password-redacted** database URL summary (host, port, database name, driver), SQLAlchemy **connection pool** statistics, and **`concurrency`**: process-local **historic peaks** for pool checkouts (parallel DB connections) and for Flask requests that have entered the per-request DB session lifecycle (`active` / `max_historic` each). Counts reset when the process restarts. It does **not** expose customer or business data.

**Authorization:** admin required — send `Authorization: Bearer <token>` for an admin session ([Endpoint index](#endpoint-index), [Authentication](#authentication)).

**Privacy / deployment**
The response still reveals infrastructure details (for example DB host and database name). Use on trusted networks or behind a reverse proxy if you do not want that metadata publicly reachable.

**Parameters**
None.

**Endpoint sample**

```http
GET /api/health/runtime HTTP/1.1
Host: localhost:5000
Authorization: Bearer <jwt-access-token>
```

```bash
curl -s http://localhost:5000/api/health/runtime \
  -H "Authorization: Bearer $TOKEN"
```

**JSON request**
None.

**JSON response** (example — numeric and string fields vary with load and environment)

```json
{
  "service": "Kinderspielstadt Los Ämmerles - LA-Server",
  "runtime": {
    "python_version": "3.14.3",
    "platform": "win32",
    "pid": 12345,
    "uptime_seconds": 3600.125
  },
  "config": {
    "DEBUG": false,
    "TESTING": false,
    "LOG_LEVEL": "INFO"
  },
  "database": {
    "url_redacted": "mysql+pymysql://user:***@db.example.com:3306/kinderspielstadt",
    "drivername": "mysql+pymysql",
    "host": "db.example.com",
    "port": 3306,
    "database": "kinderspielstadt"
  },
  "concurrency": {
    "pool_connections": { "active": 0, "max_historic": 3 },
    "requests_with_db_session": { "active": 1, "max_historic": 2 }
  },
  "pool": {
    "pool_type": "QueuePool",
    "size": 5,
    "checked_in": 4,
    "checked_out": 1,
    "overflow": -4,
    "status": "Pool size: 5  Connections in pool: 4 Current overflow: -4 Current Checked out connections: 1"
  }
}
```

**HTTP status codes**


| Code | Meaning |
| ---- | ------- |
| 200  | OK      |
| 403  | Error: `{"error": "FORBIDDEN_WRONG_AUTH_GROUP"}` (not admin) |

Missing or invalid JWT behavior matches [Errors and status codes](#errors-and-status-codes).


---

## Auth API

**Login:** [Login service](#login-service). **Current user profile:** [Me service](#me-service). **Other routes** in this section expect `Authorization: Bearer <token>` when the endpoint index marks them as protected (bearer usage: [Authentication](#authentication)).

---

<a id="login-service"></a>

### Login service - /api/auth/login

**Explanation**
Public sign-in. The server checks the JSON **`employee_number`** and **`password`** against the participant’s row in [`Authentication`](../app/models.py). On success it returns two JWT strings — **`token`** (short-lived **access**) and **`refresh_token`** (long-lived **refresh**) — plus **`auth_group`** (`employee`, `staff`, or `admin`) and **`password_must_change`**. HTTP handler: [`app/auth/routes.py`](../app/auth/routes.py) (`authenticate`); logic in **`AuthService`** — [`app/services/auth.py`](../app/services/auth.py). Use **`token`** as `Authorization: Bearer …` on protected routes; keep **`refresh_token`** only for **`POST /api/auth/refresh`** ([Authentication](#authentication)).

**Parameters**
None (JSON body).

**Endpoint sample**

```http
POST /api/auth/login HTTP/1.1
Host: localhost:5000
Content-Type: application/json

{"employee_number": "M00155", "password": "your-password"}
```

```bash
curl -s -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"employee_number":"M00155","password":"your-password"}'
```

**JSON request**

| Field               | Required | Type   | Description |
| ------------------- | -------- | ------ | ----------- |
| `employee_number`   | Yes      | string | Participant number; when `VALIDATE_CHECK_SUM` is on, must satisfy ISO 7064 Mod 97,10 ([Employee numbers and checksums](#employee-numbers-and-checksums)). |
| `password`          | Yes      | string | Plain text password (use **HTTPS** in production). |

**JSON response** (success — `200`)

```json
{
  "message": "Authenticated",
  "token": "<jwt-access-token>",
  "refresh_token": "<jwt-refresh-token>",
  "auth_group": "employee",
  "password_must_change": false
}
```

**HTTP status codes**

| Code | Meaning |
| ---- | ------- |
| 200  | OK — body includes `token`, `refresh_token`, `auth_group`, `password_must_change`. |
| 400  | `REQUEST_BODY_MUST_BE_A_JSON_OBJECT`, `REQUIRED_JSON_INPUT_MISSING_OR_EMPTY`, `EMPLOYEE_NUMBER_WRONG_IN_JSON`, or `{"error": "EMPLOYEE_NOT_ACTIVE"}`. |
| 401  | `{"error": "BAD_CREDENTIALS"}`. |
| 404  | `{"error": "EMPLOYEE_NOT_FOUND"}`. |

Other auth-related error codes are listed under [Errors and status codes](#errors-and-status-codes).

---

<a id="me-service"></a>

### Me service - /api/auth/me

**Explanation**
Returns the signed-in **participant** (employee) as JSON: profile fields from the database plus **`auth_group`** from the **JWT** (not the camp descriptive **`role`** on the record), contextual **`full_time`** / **`workday`** / **`shift`**, and derived **`checked_in`**. Requires a valid access token whose claim **`auth_group`** is one of `employee`, `staff`, or `admin`. HTTP handler: [`app/auth/routes.py`](../app/auth/routes.py) (`me`); **`AuthService`** — [`app/services/auth.py`](../app/services/auth.py).

**Parameters**
None.

**Endpoint sample**

```http
GET /api/auth/me HTTP/1.1
Host: localhost:5000
Authorization: Bearer <jwt-access-token>
```

```bash
TOKEN="<paste-access-token>"
curl -s http://localhost:5000/api/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

**JSON request**
None.

**JSON response** (success — `200`)

| Field               | Type    | Description |
| ------------------- | ------- | ----------- |
| `id`                | integer | Employee primary key. |
| `first_name`        | string  | |
| `last_name`         | string  | |
| `employee_number`   | string  | |
| `age`               | integer | Age in whole years. |
| `can_leave_alone`   | boolean | Whether the participant may leave the camp alone. |
| `role`              | string  | Camp role (e.g. participant); distinct from JWT `auth_group`. |
| `company`           | string  | Company name (empty string if none resolved from job assignment join). |
| `active`            | boolean | |
| `notes`             | string or null | |
| `created_at`        | string or null | ISO 8601 timestamp. |
| `updated_at`        | string or null | ISO 8601 timestamp. |
| `full_time`         | boolean | `true` when the participant has no part-time rows — they work **Monday through Sunday** (every day of the camp week), same **calendar coverage** as a stored **`all-week`** row but modelled as zero rows with **`shift`: `all-day`**, not as part-time data. `false` when at least one `part_times` record exists (part-time schedule; may cover only some days, e.g. **`weekdays`** Mon–Fri). |
| `workday`           | string or null | Contextual weekday label: **`today`**, a weekday slug (`monday` … `sunday`), or **`null`** when a **part-time** participant has no slot for the context day. When **`full_time`** is **`true`**, always the context label (see [Part-time context on employee responses](#part-time-context-on-employee-responses)). |
| `shift`             | string or null | Shift on the context **`workday`**: **`all-day`**, **`morning`**, or **`afternoon`**. When **`full_time`** is **`true`**, always **`all-day`**. **`null`** when **`workday`** is **`null`**. Use **`full_time`** to tell full-time **`all-day`** from a part-time row stored as **`all-day`**. |
| `checked_in`        | boolean | **`true`** when an attendance row exists for **calendar today** in camp timezone; **`false`** otherwise. Derived at response time — not a DB column. **`checkout_at` is ignored** (row exists ⇒ checked in). See [Attendance and `checked_in`](#attendance-and-checked_in). |
| `auth_group`        | string  | `employee`, `staff`, or `admin` from the JWT. |

Example:

```json
{
  "id": 1,
  "first_name": "Ada",
  "last_name": "Example",
  "employee_number": "M00155",
  "age": 10,
  "can_leave_alone": true,
  "role": "participant",
  "company": "Example Co",
  "active": true,
  "notes": null,
  "created_at": "2025-06-01T10:00:00",
  "updated_at": "2025-06-01T10:00:00",
  "full_time": false,
  "workday": "today",
  "shift": "morning",
  "checked_in": false,
  "auth_group": "employee"
}
```

**HTTP status codes**

| Code | Meaning |
| ---- | ------- |
| 200  | OK — body is the employee object above. |
| 400  | `{"error": "EMPLOYEE_NOT_ACTIVE"}`. |
| 403  | `{"error": "FORBIDDEN_WRONG_AUTH_GROUP"}` — JWT `auth_group` not allowed for this route (see [`employee_required`](../app/auth/decorations.py)). |
| 404  | `{"error": "EMPLOYEE_NOT_FOUND"}` — no row for the JWT’s `employee_number`. |

Missing, invalid, or expired JWT responses (`AUTHORIZATION_REQUIRED`, `INVALID_TOKEN`, `EXPIRED_TOKEN`) match [Errors and status codes](#errors-and-status-codes) and [`app/__init__.py`](../app/__init__.py) JWT loaders.

---

### Set auth group - /api/auth/set-auth-group

**Explanation**
Admin updates another user’s app permission `auth_group` (`employee`, `staff`, or `admin`). The target employee must exist and be active. The affected user should sign in again so their JWT reflects the new group.

**Parameters**
None (JSON body).

**Endpoint sample**

```http
POST /api/auth/set-auth-group HTTP/1.1
Host: localhost:5000
Content-Type: application/json
Authorization: Bearer <jwt-access-token>
```

```bash
curl -s -X POST http://localhost:5000/api/auth/set-auth-group \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"employee_number":"M00155","auth_group":"staff"}'
```

**JSON request**

| Field              | Required | Type   | Description                                      |
| ------------------ | -------- | ------ | ------------------------------------------------ |
| `employee_number`  | Yes      | string | Target participant (`employee_number`)           |
| `auth_group`       | Yes      | string | One of `employee`, `staff`, `admin`           |

Example:

```json
{
  "employee_number": "M00155",
  "auth_group": "staff"
}
```

**JSON response** (success)

```json
{
  "message": "Auth group set",
  "auth_group": "staff",
  "employee_number": "M00155"
}
```

**HTTP status codes**


| Code | Meaning |
| ---- | ------- |
| 200  | OK |
| 400  | Validation errors, checksum / `INVALID_AUTH_GROUP_IN_JSON`, or `{"error": "EMPLOYEE_NOT_ACTIVE"}` |
| 403  | Error: `{"error": "FORBIDDEN_WRONG_AUTH_GROUP"}` (caller is not admin) |
| 404  | Error: `{"error": "EMPLOYEE_NOT_FOUND"}` |


---

### Set password - /api/auth/password/set-password

**Explanation**
Signed-in user changes their own password. `old_password` must match the stored hash; `new_password` replaces it. Sets `password_must_change` to false.

**Parameters**
None (JSON body).

**Endpoint sample**

```http
POST /api/auth/password/set-password HTTP/1.1
Host: localhost:5000
Content-Type: application/json
Authorization: Bearer <jwt-access-token>
```

```bash
curl -s -X POST http://localhost:5000/api/auth/password/set-password \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"old_password":"current","new_password":"next"}'
```

**JSON request**

| Field           | Required | Type   | Description        |
| --------------- | -------- | ------ | ------------------ |
| `old_password`  | Yes      | string | Current password   |
| `new_password`  | Yes      | string | New password       |

**JSON response** (success)

```json
{
  "message": "Password set"
}
```

**HTTP status codes**


| Code | Meaning |
| ---- | ------- |
| 200  | OK |
| 400  | Error: `{"error": "REQUEST_BODY_MUST_BE_A_JSON_OBJECT"}` or `{"error": "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"}` |
| 403  | Error: `{"error": "OLD_PASSWORD_IS_INCORRECT"}` |
| 404  | Error: `{"error": "EMPLOYEE_NOT_FOUND"}` |
| 400  | Error: `{"error": "EMPLOYEE_NOT_ACTIVE"}` |


---

### Reset password - /api/auth/password/reset-password

**Explanation**
Staff or admin resets another user’s password to a hash of that user’s **`last_name`** (same rules as [`hash_password`](../app/auth/utils.py) / login: comparison is case-insensitive for verification). Sets `password_must_change` to true so the user must pick a new password via `set-password`. This reproduces the **same initial-password rule** as **new accounts**: admin **`POST /api/employees`** and the **CSV bulk import** script also store the initial hash from **`last_name`** and set `password_must_change` to true, so a reset behaves like a freshly created or re-imported participant for login purposes.

**Parameters**
None (JSON body).

**Endpoint sample**

```http
POST /api/auth/password/reset-password HTTP/1.1
Host: localhost:5000
Content-Type: application/json
Authorization: Bearer <jwt-access-token>
```

```bash
curl -s -X POST http://localhost:5000/api/auth/password/reset-password \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"employee_number":"M00155"}'
```

**JSON request**

| Field              | Required | Type   | Description                            |
| ------------------ | -------- | ------ | -------------------------------------- |
| `employee_number`  | Yes      | string | Target participant                     |

**JSON response** (success)

```json
{
  "message": "Password reset"
}
```

**HTTP status codes**


| Code | Meaning |
| ---- | ------- |
| 200  | OK |
| 400  | Error: `{"error": "REQUEST_BODY_MUST_BE_A_JSON_OBJECT"}` or `{"error": "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"}` or `EMPLOYEE_NUMBER_WRONG_IN_JSON` |
| 403  | Error: `{"error": "FORBIDDEN_WRONG_AUTH_GROUP"}` (caller is not staff or admin) |
| 404  | Error: `{"error": "EMPLOYEE_NOT_FOUND"}` |


---

<a id="refresh-session"></a>

### Refresh session - /api/auth/refresh

**Explanation**
Requires the **refresh** JWT from **`POST /api/auth/login`** (the **`refresh_token`** response field): send **`Authorization: Bearer <jwt-refresh-token>`** — **not** the access token. While that refresh JWT is valid, the response includes a **new** **access** JWT in **`token`** for the same `employee_number` and `auth_group`; store it and use it as Bearer on ordinary protected routes. See [**Authentication**](#authentication).

**Parameters**
None.

**Endpoint sample**

```http
POST /api/auth/refresh HTTP/1.1
Host: localhost:5000
Authorization: Bearer <jwt-refresh-token>
```

```bash
REFRESH_TOKEN="<paste-refresh-token-from-login>"
curl -s -X POST http://localhost:5000/api/auth/refresh \
  -H "Authorization: Bearer $REFRESH_TOKEN"
```

**JSON request**
None.

**JSON response** (success)

```json
{
  "message": "Token refreshed",
  "token": "<new-access-jwt>",
  "employee_number": "M00155"
}
```

**HTTP status codes**

| Code | Meaning |
| ---- | ------- |
| 200  | OK — body includes new access `token` and `employee_number`. |
| 401  | `AUTHORIZATION_REQUIRED` — missing `Authorization` header or Bearer value ([`app/__init__.py`](../app/__init__.py)). |
| 401  | `EXPIRED_TOKEN` — refresh JWT expired (`message`: token expired). |
| 422  | `INVALID_TOKEN` — Bearer JWT malformed or otherwise invalid (`message` from Flask-JWT-Extended). |
| 404  | `{"error": "EMPLOYEE_NOT_FOUND"}` — employee removed since login while refresh JWT still valid. |
| 400  | `{"error": "EMPLOYEE_NOT_ACTIVE"}` |

Sending an **access** JWT instead of a **refresh** JWT typically yields **`422`** `INVALID_TOKEN` (wrong token type). Other JWT conventions: [Errors and status codes](#errors-and-status-codes).


---

### Logout - /api/auth/logout

**Explanation**
Acknowledges logout. Response includes `token` set to the literal `INVALID-TOKEN`; clear stored tokens on the client regardless.

**Parameters**
None.

**Endpoint sample**

```http
POST /api/auth/logout HTTP/1.1
Host: localhost:5000
Authorization: Bearer <jwt-access-token>
```

```bash
curl -s -X POST http://localhost:5000/api/auth/logout \
  -H "Authorization: Bearer $TOKEN"
```

**JSON request**
None.

**JSON response**

```json
{
  "message": "Logged out",
  "token": "INVALID-TOKEN"
}
```

**HTTP status codes**


| Code | Meaning |
| ---- | ------- |
| 200  | OK |

JWT handling errors match [Errors and status codes](#errors-and-status-codes).


---

## Companies

<a id="company-jobs-max-context-on-company-responses"></a>

### Company jobs max context on company responses

**Two APIs, two jobs:** use **`GET /api/companies`** for kiosk / job-center display — responses show **`default_jobs_max`**, contextual **`workday`** / **`shift`**, and effective **`jobs.max`** / **`jobs.available`**. Use **`/api/company-jobs-max/{company_name}`** for **admin maintenance** of stored schedule rows (`workday`, `shift`, `jobs_max`, `notes` as persisted, including aggregate slugs). Do **not** write schedule data via company POST/PUT. See [Company jobs max API](#company-jobs-max-api).

**Camp timezone and shift:** **`general.timezone`** in **`village_data/village.ini`** defines which calendar day is **“today”**. **`camp_shift()`** (code constant **`13:00`** camp-local — morning before 13:00, afternoon from 13:00 inclusive) defines the current shift. Neither accepts client query parameters on company GET. See [database_design.md — Camp shift boundary](./database_design.md#camp-shift-boundary).

| Field | Meaning |
|-------|---------|
| **`default_jobs_max`** | `true` when the company has **zero** schedule rows — effective cap is always **`companies.jobs_max`**. Parallel to employee **`full_time`**. |
| **`workday`** | **`today`** when a schedule row matches camp now; **`null`** when rows exist but none match (cap still falls back to stored default). **Never** aggregate slugs. |
| **`shift`** | **`all-day`** when **`default_jobs_max`**; matching row shift otherwise; **`null`** when no slot matches. |
| **`jobs.max`** | Effective cap **right now** (override or fallback). |
| **`jobs.available`** | **`jobs.max`** minus current assignment count; may be **negative** if the cap was lowered below existing assignments. |

**Example:** Bank has `jobs_max` = 10 (stored default), plus rows `weekdays/morning` → 5 and `weekdays/afternoon` → 2. On Wednesday at **12:59** camp time → **`jobs.max`: 5**, **`workday`: `"today"`**, **`shift`: `"morning"`**. At **13:00** → **`jobs.max`: 2**, **`shift`: `"afternoon"`**. On Saturday (no matching row) → **`jobs.max`: 10**, **`workday`/`shift`: `null`**, **`default_jobs_max`: false**.

Allowed **stored** workday and shift values are listed under **`la-server.company_jobs_max_workdays`** and **`la-server.company_jobs_max_shifts`** on **`GET /api/village-data`**.

### List companies - /api/companies

**Explanation**
Returns all companies, optionally filtered by `active`.

**Parameters** (query)


| Name     | Required | Description                                                                                                        |
| -------- | -------- | ------------------------------------------------------------------------------------------------------------------ |
| `active` | No       | If `true` / `1` / `yes`, only active companies. If `false` / `0` / `no`, only inactive. If omitted, all companies. |


**Endpoint sample**

```http
GET /api/companies?active=true HTTP/1.1
Host: localhost:5000
```

```bash
curl -s "http://localhost:5000/api/companies"
curl -s "http://localhost:5000/api/companies?active=true"
curl -s "http://localhost:5000/api/companies?active=false"
```

**JSON request**
None.

**JSON response** (example)

```json
{
  "companies": [
    {
      "id": 1,
      "company_name": "Bank",
      "default_jobs_max": false,
      "workday": "today",
      "shift": "morning",
      "jobs": { "available": 3, "max": 5 },
      "hourly_pay": 10,
      "active": true,
      "notes": null,
      "created_at": "2026-01-15T10:00:00+00:00",
      "updated_at": "2026-01-15T10:00:00+00:00"
    },
    {
      "id": 2,
      "company_name": "Bauhof",
      "default_jobs_max": true,
      "workday": "today",
      "shift": "all-day",
      "jobs": { "available": 4, "max": 4 },
      "hourly_pay": 10,
      "active": false,
      "notes": null,
      "created_at": "2026-01-15T10:00:00+00:00",
      "updated_at": "2026-01-15T10:00:00+00:00"
    }
  ],
  "count": 2
}
```

**HTTP status codes**


| Code | Meaning |
| ---- | ------- |
| 200  | OK      |


---

### Get company - /api/companies/<company_name>

**Explanation**
Returns one company by exact `company_name` (URL path).

**Parameters** (path)


| Name           | Required | Description                         |
| -------------- | -------- | ----------------------------------- |
| `company_name` | Yes      | Exact name as stored (e.g. `Bank`). |


**Endpoint sample**

```http
GET /api/companies/Bank HTTP/1.1
Host: localhost:5000
```

```bash
curl -s "http://localhost:5000/api/companies/Bank"
```

**JSON request**
None.

**JSON response** (example — same shape as one element of `companies` in the list response)

```json
{
  "id": 1,
  "company_name": "Bank",
  "default_jobs_max": false,
  "workday": "today",
  "shift": "morning",
  "jobs": { "available": 3, "max": 5 },
  "hourly_pay": 10,
  "active": true,
  "notes": null,
  "created_at": "2026-01-15T10:00:00+00:00",
  "updated_at": "2026-01-15T10:00:00+00:00"
}
```

**HTTP status codes**


| Code | Meaning                                           |
| ---- | ------------------------------------------------- |
| 200  | OK                                                |
| 404  | Error: `{"error": "COMPANY_NOT_FOUND"}`                  |


---

### Create company - /api/companies

**Explanation**
Creates a new company row. **Authorization:** admin required — send `Authorization: Bearer <token>` for an admin session ([Endpoint index](#endpoint-index), [Authentication](#authentication)).

**Parameters**
None (body is JSON).

**Endpoint sample**

```http
POST /api/companies HTTP/1.1
Host: localhost:5000
Content-Type: application/json
Authorization: Bearer <jwt-access-token>
```

```bash
curl -s -X POST http://localhost:5000/api/companies \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"company_name":"Bank","jobs_max":8,"hourly_pay":10,"active":true}'
```

**JSON request**

| Field          | Required | Type           | Description                |
| -------------- | -------- | -------------- | -------------------------- |
| `company_name` | Yes      | string         | Unique name                |
| `jobs_max`     | Yes      | integer        | Max concurrent assignments |
| `hourly_pay` | Yes      | integer        | payment per hour           |
| `active`       | No       | boolean        | Default `true`  (optional) |
| `notes`        | No       | string or null | Free text  (optional)      |


Example:

```json
{
  "company_name": "Bank",
  "jobs_max": 8,
  "hourly_pay": 10,
  "active": true,
  "notes": null
}
```

**JSON response** (example)

```json
{
  "id": 1,
  "company_name": "Bank",
  "default_jobs_max": true,
  "workday": "today",
  "shift": "all-day",
  "jobs": { "available": 8, "max": 8 },
  "hourly_pay": 10,
  "active": true,
  "notes": null,
  "created_at": "2026-01-15T10:00:00+00:00",
  "updated_at": "2026-01-15T10:00:00+00:00"
}
```

**HTTP status codes**


| Code | Meaning                                                                                            |
| ---- | -------------------------------------------------------------------------------------------------- |
| 201  | Created                                                                                            |
| 400  | Error: `{"error": "REQUEST_BODY_MUST_BE_A_JSON_OBJECT"}` or `{"error": "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"}` |
| 403  | Error: `{"error": "FORBIDDEN_WRONG_AUTH_GROUP"}` (not admin)                                     |
| 409  | Error: `{"error": "CONSTRAINT_VIOLATION", "message": "Create failed, because entry is already in database"}` |


---

### Update company - /api/companies/<company_name>

**Explanation**
Updates any fields present in the JSON body. Lookup is by URL `company_name` before updates (including if you rename via `company_name` in the body). **Authorization:** admin required — send `Authorization: Bearer <token>` for an admin session ([Endpoint index](#endpoint-index), [Authentication](#authentication)).

**Parameters** (path)


| Name           | Required | Description                       |
| -------------- | -------- | --------------------------------- |
| `company_name` | Yes      | Current name used to find the row |


**Endpoint sample**

```http
PUT /api/companies/Bank HTTP/1.1
Host: localhost:5000
Content-Type: application/json
Authorization: Bearer <jwt-access-token>
```

```bash
curl -s -X PUT "http://localhost:5000/api/companies/Bank" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"hourly_pay":12}'
```

**JSON request** (all optional keys; only sent fields are updated)

| Field          | Required | Type           | Description                            |
| -------------- | -------- | -------------- | -------------------------------------- |
| `company_name` | Yes      | string         | Unique name  (optional)                |
| `jobs_max`     | Yes      | integer        | Max concurrent assignments  (optional) |
| `hourly_pay` | Yes      | integer        | payment per hour  (optional)           |
| `active`       | No       | boolean        | Default `true`  (optional)             |
| `notes`        | No       | string or null | Free text  (optional)                  |

```json
{
  "company_name": "Bank Filiale",
  "jobs_max": 10,
  "hourly_pay": 12,
  "active": true,
  "notes": "Updated"
}
```

**JSON response**
Same shape as `GET` one company (current state after update).

**HTTP status codes**


| Code | Meaning                                           |
| ---- | ------------------------------------------------- |
| 200  | OK                                                |
| 400  | Error: `{"error": "REQUEST_BODY_MUST_BE_A_JSON_OBJECT"}` |
| 403  | Error: `{"error": "FORBIDDEN_WRONG_AUTH_GROUP"}` (not admin) |
| 404  | Error: `{"error": "COMPANY_NOT_FOUND"}`                  |
| 409  | Error: `{"error": "CONSTRAINT_VIOLATION", "message": "Create failed, because entry is already in database"}` |


---

### Delete company - /api/companies/<company_name>

**Explanation**
Permanently deletes the company. Fails if foreign keys still reference it (e.g. job assignments). **Authorization:** admin required — send `Authorization: Bearer <token>` for an admin session ([Endpoint index](#endpoint-index), [Authentication](#authentication)).

**Parameters** (path)


| Name           | Required | Description       |
| -------------- | -------- | ----------------- |
| `company_name` | Yes      | Company to delete |


**Endpoint sample**

```http
DELETE /api/companies/Bank HTTP/1.1
Host: localhost:5000
Authorization: Bearer <jwt-access-token>
```

```bash
curl -s -X DELETE "http://localhost:5000/api/companies/Bank" \
  -H "Authorization: Bearer $TOKEN"
```

**JSON request**
None.

**JSON response**

```json
{
  "message": "company deleted permanently"
}
```

**HTTP status codes**


| Code | Meaning                                             |
| ---- | --------------------------------------------------- |
| 200  | Deleted                                             |
| 403  | Error: `{"error": "FORBIDDEN_WRONG_AUTH_GROUP"}` (not admin) |
| 404  | Error: `{"error": "COMPANY_NOT_FOUND"}`                    |
| 409  | Error: `{"error": "CONSTRAINT_VIOLATION", "message": "Delete failed, because related entries in JobAssignment table"}` |


---

<a id="company-jobs-max-api"></a>

## Company jobs max API

Admin CRUD on stored **`company_jobs_max`** rows at **`/api/company-jobs-max/{company_name}`**. Normal camp processing (company lists, job center, assignment capacity) continues to use **`/api/companies`** for derived **`default_jobs_max`**, **`workday`**, **`shift`**, and effective **`jobs.max`** — see [Company jobs max context on company responses](#company-jobs-max-context-on-company-responses).

| Need | Call |
| ---- | ---- |
| Effective cap / availability right now | **`GET /api/companies`** (derived fields) |
| What schedule rows are stored for editing? | **`GET /api/company-jobs-max/{company_name}`** |
| Admin edit schedule | **`POST`** / **`PUT`** / **`DELETE /api/company-jobs-max/{company_name}`** |

**Default cap everywhere** = **delete all** schedule rows (`DELETE /api/company-jobs-max/{company_name}` with no query), not an aggregate **`all-day`** row. The stored default remains **`companies.jobs_max`**.

Every route validates path **`company_name`** before database access (same rules as the Company API): empty name → **`400`** **`COMPANY_NAME_PATH_EMPTY`**; unknown company → **`404`** **`COMPANY_NOT_FOUND`**.

**Write validation** (POST, PUT, and DELETE-one **`?workday=&shift=`**):

1. **`verify_part_time_stored_workday`** → **`400`** **`INVALID_PART_TIME_WORKDAY`**
2. **`verify_part_time_shift`** → **`400`** **`INVALID_PART_TIME_SHIFT`**
3. **`validate_part_time_combination`** → **`400`** **`INVALID_PART_TIME_COMBINATION`**
4. **`verify_jobs_max`** (POST/PUT when `jobs_max` present) → **`400`** **`INVALID_JOBS_MAX`**

Allowed stored **`workday`** and **`shift`** values are listed under **`la-server.company_jobs_max_workdays`** and **`la-server.company_jobs_max_shifts`** on **`GET /api/village-data`**.

### List stored schedule rows - /api/company-jobs-max/<company_name>

**Explanation**
Returns **stored** slugs for one company — not contextual **`today`**. Rows are ordered by workday then shift. Reject any **`?workday=`** or **`?shift=`** query on GET → **`400`** **`INVALID_PART_TIME_WORKDAY`** / **`INVALID_PART_TIME_SHIFT`**.

**Parameters** (path)

| Name           | Required | Description   |
| -------------- | -------- | ------------- |
| `company_name` | Yes      | e.g. `Bank` |

**Endpoint sample**

```http
GET /api/company-jobs-max/Bank HTTP/1.1
Host: localhost:5000
```

```bash
curl -s "http://localhost:5000/api/company-jobs-max/Bank"
```

**JSON request**
None.

**JSON response** (example)

```json
{
  "company_name": "Bank",
  "company_jobs_max": [
    {
      "id": 1,
      "workday": "weekdays",
      "shift": "morning",
      "jobs_max": 5,
      "notes": null,
      "created_at": "2026-01-15T10:00:00+00:00",
      "updated_at": "2026-01-15T10:00:00+00:00"
    },
    {
      "id": 2,
      "workday": "weekdays",
      "shift": "afternoon",
      "jobs_max": 2,
      "notes": null,
      "created_at": "2026-01-15T10:00:00+00:00",
      "updated_at": "2026-01-15T10:00:00+00:00"
    }
  ],
  "count": 2
}
```

**HTTP status codes**

| Code | Meaning |
| ---- | ------- |
| 200  | OK |
| 400  | `{"error": "INVALID_PART_TIME_WORKDAY"}` or `{"error": "INVALID_PART_TIME_SHIFT"}` (spurious query params) |
| 404  | `{"error": "COMPANY_NOT_FOUND"}` |

---

### Create schedule row - /api/company-jobs-max/<company_name>

**Explanation**
Creates one stored row. **`workday`** and **`jobs_max`** are required; **`shift`** defaults to **`all-day`**; **`notes`** is optional. Duplicate **`(workday, shift)`** for the same company → **`409`** **`CONSTRAINT_VIOLATION`** (`uq_company_jobs_max_company_workday_shift`). **Authorization:** admin required.

**Parameters** (path)

| Name           | Required | Description   |
| -------------- | -------- | ------------- |
| `company_name` | Yes      | Target company |

**Endpoint sample**

```http
POST /api/company-jobs-max/Bank HTTP/1.1
Host: localhost:5000
Content-Type: application/json
Authorization: Bearer <jwt-access-token>
```

```bash
curl -s -X POST "http://localhost:5000/api/company-jobs-max/Bank" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"workday":"weekdays","shift":"morning","jobs_max":5}'
```

**JSON request**

| Field      | Required | Description |
| ---------- | -------- | ----------- |
| `workday`  | Yes      | Stored slug (`monday` … `sunday`, `weekdays`, `all-week`) |
| `jobs_max` | Yes      | Override cap (non-negative integer) |
| `shift`    | No       | Default **`all-day`** |
| `notes`    | No       | Optional free text |

**JSON response** (created row — **`201`**)

```json
{
  "id": 3,
  "workday": "weekdays",
  "shift": "morning",
  "jobs_max": 5,
  "notes": null,
  "created_at": "2026-01-15T10:00:00+00:00",
  "updated_at": "2026-01-15T10:00:00+00:00"
}
```

**HTTP status codes**

| Code | Meaning |
| ---- | ------- |
| 201  | Created |
| 400  | Validation errors (`INVALID_PART_TIME_WORKDAY`, `INVALID_PART_TIME_SHIFT`, `INVALID_PART_TIME_COMBINATION`, `INVALID_JOBS_MAX`, …) |
| 403  | `{"error": "FORBIDDEN_WRONG_AUTH_GROUP"}` (not admin) |
| 404  | `{"error": "COMPANY_NOT_FOUND"}` |
| 409  | `{"error": "CONSTRAINT_VIOLATION", "message": "Create failed, because entry is already in database"}` |

---

### Update schedule row - /api/company-jobs-max/<company_name>

**Explanation**
Partial update by stored **`workday`** + **`shift`** lookup keys (neither is renamable). Include **`jobs_max`** and/or **`notes`** to change them. Unknown row → **`404`** **`COMPANY_JOBS_MAX_NOT_FOUND`**. **Authorization:** admin required.

**Parameters** (path)

| Name           | Required | Description   |
| -------------- | -------- | ------------- |
| `company_name` | Yes      | Target company |

**Endpoint sample**

```http
PUT /api/company-jobs-max/Bank HTTP/1.1
Host: localhost:5000
Content-Type: application/json
Authorization: Bearer <jwt-access-token>
```

```bash
curl -s -X PUT "http://localhost:5000/api/company-jobs-max/Bank" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"workday":"weekdays","shift":"morning","jobs_max":6,"notes":"Peak hours"}'
```

**JSON request**

| Field      | Required | Description |
| ---------- | -------- | ----------- |
| `workday`  | Yes      | Lookup key (stored slug) |
| `shift`    | Yes      | Lookup key (stored slug) |
| `jobs_max` | No       | New cap when present |
| `notes`    | No       | New notes; send `null` to clear |

**JSON response**
Same shape as create (**`200`**).

**HTTP status codes**

| Code | Meaning |
| ---- | ------- |
| 200  | OK |
| 400  | Validation errors |
| 403  | Not admin |
| 404  | `{"error": "COMPANY_NOT_FOUND"}` or `{"error": "COMPANY_JOBS_MAX_NOT_FOUND"}` |

---

### Delete all schedule rows - /api/company-jobs-max/<company_name>

**Explanation**
Removes every stored row for the company (idempotent when already empty). Restores default-cap behaviour: **`GET /api/companies/{company_name}`** then shows **`default_jobs_max`: true**, **`workday`: `"today"`**, **`shift`: `"all-day"`**, and **`jobs.max`** from **`companies.jobs_max`**. **Authorization:** admin required. When **`?workday=&shift=`** is present, see [Delete one schedule row](#delete-one-schedule-row---apicompanys-jobs-maxcompany_nameworkdayshift).

**Parameters** (path)

| Name           | Required | Description   |
| -------------- | -------- | ------------- |
| `company_name` | Yes      | Target company |

**Endpoint sample**

```http
DELETE /api/company-jobs-max/Bank HTTP/1.1
Host: localhost:5000
Authorization: Bearer <jwt-access-token>
```

```bash
curl -s -X DELETE "http://localhost:5000/api/company-jobs-max/Bank" \
  -H "Authorization: Bearer $TOKEN"
```

**JSON request**
None.

**JSON response**

```json
{
  "message": "company jobs max rows deleted",
  "count": 2
}
```

**HTTP status codes**

| Code | Meaning |
| ---- | ------- |
| 200  | OK |
| 403  | Not admin |
| 404  | `{"error": "COMPANY_NOT_FOUND"}` |

---

<a id="delete-one-schedule-row---apicompanys-jobs-maxcompany_nameworkdayshift"></a>

### Delete one schedule row - /api/company-jobs-max/<company_name>?workday=&shift=

**Explanation**
Deletes the row for one stored **`workday`** + **`shift`** pair. Both query parameters are required together. Unknown row → **`404`** **`COMPANY_JOBS_MAX_NOT_FOUND`**. **Authorization:** admin required.

**Parameters** (path)

| Name           | Required | Description   |
| -------------- | -------- | ------------- |
| `company_name` | Yes      | Target company |

**Parameters** (query)

| Name      | Required | Description |
| --------- | -------- | ----------- |
| `workday` | Yes      | Stored slug |
| `shift`   | Yes      | Stored slug |

**Endpoint sample**

```http
DELETE /api/company-jobs-max/Bank?workday=weekdays&shift=morning HTTP/1.1
Host: localhost:5000
Authorization: Bearer <jwt-access-token>
```

```bash
curl -s -X DELETE "http://localhost:5000/api/company-jobs-max/Bank?workday=weekdays&shift=morning" \
  -H "Authorization: Bearer $TOKEN"
```

**JSON request**
None.

**JSON response**

```json
{
  "message": "company jobs max row deleted"
}
```

**HTTP status codes**

| Code | Meaning |
| ---- | ------- |
| 200  | OK |
| 400  | Validation errors (`INVALID_PART_TIME_WORKDAY`, `INVALID_PART_TIME_SHIFT`, …) |
| 403  | Not admin |
| 404  | `{"error": "COMPANY_NOT_FOUND"}` or `{"error": "COMPANY_JOBS_MAX_NOT_FOUND"}` |

---

## Employees

In domain language, each row is a **camp participant** (child or staff). The API keeps the historical names *employee* / `employee_number`.

<a id="part-time-context-on-employee-responses"></a>

### Part-time context on employee responses

Employee list, get-one, and **`GET /api/auth/me`** responses include **`full_time`**, **`workday`**, **`shift`**, and **`checked_in`**. The first three are **derived** from optional **`part_times`** database rows (see [database_design.md](./database_design.md#part_times)), not separate columns on the employee. **`checked_in`** is derived from **`attendances`** rows — see [Attendance and `checked_in`](#attendance-and-checked_in).

**Two APIs, two jobs:** use **`GET /api/employees`** (and filters) for rosters, kiosk display, and “who works today?” — responses show contextual labels such as **`today`**. Use **`/api/part-time/{employee_number}`** for **admin maintenance** of stored rows (`workday`, `shift`, `notes` as persisted, including aggregate slugs). Do **not** write part-time data via employee POST/PUT. See [Part-time API](#part-time-api).

**Camp timezone:** **`general.timezone`** in **`village_data/village.ini`** (IANA name, e.g. `Europe/Berlin`) defines which calendar day is **“today”** for the camp. The server reads it via **`get_camp_timezone()`** ([`app/village_config.py`](../app/village_config.py)); missing or invalid values fall back to **`Europe/Berlin`**. The same key appears under **`general`** in **`GET /api/village-data`**.

**Response labels** (full-time participants, or when a matching part-time slot exists for the context weekday):

| List `workday` query | Context weekday | Example `workday` in JSON |
| -------------------- | --------------- | ------------------------- |
| omitted or **`all`** (default) | Calendar today in camp TZ | **`today`** |
| **`today`** | Calendar today in camp TZ | **`today`** |
| **`tuesday`** (any weekday slug) | That weekday | **`tuesday`** |

**Get one** and **`GET /api/auth/me`** always use **calendar today** in camp timezone → **`today`** when the participant works that day (full-time or matching part-time slot), or **`null`** when part-time with no slot today — regardless of list filters.

**Full-time participants** (no `part_times` rows): **`full_time`** is **`true`** — they work **every calendar day Mon–Sun** (same day span as **`all-week`**, but **not** stored as a part-time row). **`workday`** is the context label (**`today`** on get-one / **`/api/auth/me`**, or the list context weekday), **`shift`** is always **`all-day`**. Do **not** confuse with **`weekdays`** (Mon–Fri only).

**`null`** on **`workday`** / **`shift`** means **part-time but not scheduled on the context day** — not full-time.

**Client usage:** **`workday !== null`** means the participant works on the context day (full-time or part-time). Use **`full_time`** for schedule type; use **`shift`** for display (`morning`, `afternoon`, or `all-day`).

**List filters** on **`GET /api/employees`**:

| Query param | Default | Effect |
| ----------- | ------- | ------ |
| **`workday`** | **`all`** | **`all`**: no part-time filter; each row’s **`workday`** / **`shift`** describe the slot for calendar **today**. **`today`**: only participants with an effective part-time slot today (including via **`weekdays`** or **`all-week`**). A calendar slug (`monday` … `sunday`): filter to that day using the same precedence as slot lookup; row labels use the same slug. **`weekdays`** and **`all-week`** are **not** valid filter values → **`400`**. |
| **`shift`** | omitted | Optional when **`workday`** ≠ **`all`**: **`all-day`**, **`morning`**, or **`afternoon`**. Ignored when **`workday=all`**. |
| **`active`** | unchanged | Same as before. |

**List filter vs response:** **`?workday=today`** and weekday filters match only participants with **`part_times`** rows (full-time staff have none, so they are **excluded** from filtered lists). With default **`workday=all`**, full-time rows still appear and show contextual **`workday`** / **`all-day`** **`shift`**.

Allowed **list-filter** weekday values are calendar slugs plus **`all`** and **`today`**. Allowed **stored** workday values (including aggregates) are listed under **`la-server.part_time_workdays`** on **`GET /api/village-data`**. Invalid list **`workday`** → **`400`** **`INVALID_PART_TIME_WORKDAY`**; invalid **`shift`** → **`400`** **`INVALID_PART_TIME_SHIFT`**.

<a id="aggregate-part-time-patterns"></a>

### Aggregate part-time patterns

Staff enter **stored** `part_times` rows (including aggregate slugs). Precedence when several rows apply on the same calendar day is defined in [database_design.md — Aggregate workdays](./database_design.md#aggregate-workdays-weekdays-all-week) (rules 6–7 and worked examples).

#### Terminology

| Term | Meaning |
|------|---------|
| **`workday` (column / API field)** | The part-time schedule key — singular field name, unchanged |
| **Calendar workday** | Stored slug `monday` … `sunday` — one day |
| **`weekdays` (stored slug)** | **Monday through Friday** — German *Werktage*; **not** the field name |
| **`all-week` (stored slug)** | **Monday through Sunday** — every calendar day |
| **`all-day` (shift slug)** | Full day on the matched day — analogous to how aggregate slugs span multiple days |
| **`workday=all` (list query only)** | Do not filter by part-time day — **never stored** |
| **`full_time` (API field)** | **Monday through Sunday** — zero `part_times` rows; works every day of the camp week. Same calendar coverage as **`all-week`**, but authoritative via **`full_time`: `true`**, not a stored aggregate. |

When someone works the **same shift on many days**, you can store **one aggregate row** instead of repeating five or seven calendar-day rows.

| Plain language | Stored row |
| -------------- | ---------- |
| “Morning every weekday (Mon–Fri)” | `{ "workday": "weekdays", "shift": "morning" }` |
| “Morning every day of the camp week” | `{ "workday": "all-week", "shift": "morning" }` |

**`weekdays`** means Monday through Friday only (*Werktage*). **`all-week`** means every day Mon–Sun.

#### Full-time vs aggregate + `all-day` (design rule 7)

**Full-time = zero rows.** A participant who works the **full camp week (Monday through Sunday)** has **no** `part_times` rows at all (`full_time`: **`true`**, **`workday`**: context label such as **`today`**, **`shift`**: **`all-day`** in employee JSON). That is the same **Mon–Sun** calendar span as **`all-week`**, but full-time is expressed by **deleting all part-time rows**, not by storing `{ "workday": "all-week", … }`. **`full_time`** remains the authoritative flag — do not infer full-time from **`shift: "all-day"`** alone (part-time calendar rows can also use that shift).

**Do not** model full-time with an aggregate row:

```json
{ "workday": "all-week", "shift": "all-day" }
```

That combination is **invalid**. Aggregate slugs (**`weekdays`**, **`all-week`**) may pair only with **`morning`** or **`afternoon`**. The same applies to **`weekdays`** + **`all-day`**. **`POST`** / **`PUT /api/part-time/{employee_number}`** return **`400`** with **`INVALID_PART_TIME_COMBINATION`**. To restore full-time, **delete all** part-time rows for that employee via **`DELETE /api/part-time/{employee_number}`** — do not substitute an aggregate **`all-day`** row.

See [database_design.md — rule 7](./database_design.md#part-time-design-decisions) and [`validate_part_time_combination()`](../app/schemas/part_time.py).

**Does not apply on Saturday/Sunday:** a stored **`weekdays`** row never supplies a slot on Saturday or Sunday. On those days the employee JSON shows **`workday`: null** and **`shift`: null** unless they also have a calendar row for that day or an **`all-week`** row. List filters **`?workday=saturday`** and **`?workday=sunday`** **exclude** participants who only have a **`weekdays`** row; **`?workday=friday`** **includes** them.

#### Five rows vs one `weekdays` row

**Before (five stored rows):**

```json
[
  { "workday": "monday", "shift": "morning" },
  { "workday": "tuesday", "shift": "morning" },
  { "workday": "wednesday", "shift": "morning" },
  { "workday": "thursday", "shift": "morning" },
  { "workday": "friday", "shift": "morning" }
]
```

**After (one aggregate row):**

```json
[
  { "workday": "weekdays", "shift": "morning" }
]
```

#### Seven rows vs one `all-week` row

**Before (seven stored rows):**

```json
[
  { "workday": "monday", "shift": "morning" },
  { "workday": "tuesday", "shift": "morning" },
  { "workday": "wednesday", "shift": "morning" },
  { "workday": "thursday", "shift": "morning" },
  { "workday": "friday", "shift": "morning" },
  { "workday": "saturday", "shift": "morning" },
  { "workday": "sunday", "shift": "morning" }
]
```

**After (one aggregate row):**

```json
[
  { "workday": "all-week", "shift": "morning" }
]
```

#### What clients see in employee JSON

The API **never** returns **`"weekdays"`** or **`"all-week"`** in the employee **`workday`** field. It always shows the **context day**:

- On a **Wednesday** list with default **`workday=all`**, a participant stored as **`weekdays/morning`** appears as **`"workday": "today"`** (if today is Wednesday) or **`"workday": "wednesday"`** when the list filter is **`?workday=wednesday`** — with **`"shift": "morning"`**.
- On **Saturday**, the same participant shows **`"workday": null`** and **`"shift": null`** unless they also have a Saturday calendar row or an **`all-week`** row.

#### List filter behavior

| Filter | `weekdays/morning` only | `all-week/morning` only |
| ------ | ----------------------- | ------------------------ |
| **`?workday=friday`** | Included (Fri is Mon–Fri) | Included |
| **`?workday=saturday`** | **Excluded** (Sat is not a weekday) | Included |
| **`?workday=weekdays`** | **`400`** — not a valid filter | **`400`** |

A calendar-day row for a specific day **overrides** the aggregate for that day only (e.g. **`weekdays/morning`** + **`friday/afternoon`** → Friday afternoon, Mon–Thu morning). See [database_design.md — Aggregate workdays](./database_design.md#aggregate-workdays-weekdays-all-week) for precedence edge cases and per-day slot lookup tables.

<a id="attendance-and-checked_in"></a>

### Attendance and `checked_in`

Daily gate check-in is stored in the **`attendances`** table (see [database_design.md — `attendances`](./database_design.md#attendances)). Employee JSON adds a derived boolean **`checked_in`** — same pattern as **`full_time`** / **`workday`** / **`shift`**, not a column on **`employees`**.

| Endpoint | Field |
| -------- | ----- |
| **`GET /api/employees`** | each element of **`employees[]`** |
| **`GET /api/employees/{employee_number}`** | top-level object |
| **`GET /api/auth/me`** | top-level object |

**Definition:** **`checked_in`: `true`** when an **`attendances`** row exists for **`camp_date` = calendar today** in camp timezone ([`camp_today()`](../app/camp_time.py)). **`false`** when no row exists. **`checkout_at` is ignored** — a participant who checked out early still counts as checked in if today’s row exists.

**Not affected by part-time list filters:** the **`checked_in`** field on each row always reflects **calendar today**, like get-one **`workday`** / **`shift`** context — not the list **`?workday=`** filter.

**List filter:** **`GET /api/employees`** accepts optional **`?checked_in=`** (`true`/`1`/`yes` or `false`/`0`/`no`; omit = no filter). **`true`** returns only participants with an **`attendances`** row for **camp today**; **`false`** returns only those **without** such a row. Same calendar-day rule and **`checkout_at`** semantics as the response field. Combine with **`?active=`**, **`?workday=`**, **`?shift=`**, and **`?auth_group=`** (see [List employees](#list-employees---apiemployees)). For timestamp audit logs (who scanned in and when), use **`GET /api/attendance/check-ins`** instead.

**Who must check in for job center?** Village switches in **`village.ini`** **`[attendance]`** (also under **`attendance`** in **`GET /api/village-data`**) control whether **`POST`** and **`DELETE`** on **`/api/job-assignments`** require today’s check-in row. Check-out is **never** required. See [Job assignments](#job-assignments) and [Attendance API](#attendance-api).

| Participant | JWT `auth_group` | Check-in at job center when… |
| ----------- | ---------------- | ------------------------------ |
| Kids | **`employee`** | **`require_attendance_for_kids`** is **`true`** (default) |
| Staff / admin | **`staff`**, **`admin`** | **`require_attendance_for_staff`** is **`true`** (default **`false`**) |

Staff record check-in via **`POST /api/attendance/check-in/{employee_number}`** (passport scan at the gate). Optional early departure: **`POST /api/attendance/check-out/{employee_number}`**.

---

### List employees - /api/employees

**Explanation**
Lists employees (camp participants), optionally filtered by **`active`**, **`workday`**, **`shift`**, **`checked_in`**, and **`auth_group`**. Each element includes contextual **`full_time`**, **`workday`**, **`shift`**, and **`checked_in`** (see [Part-time context on employee responses](#part-time-context-on-employee-responses) and [Attendance and `checked_in`](#attendance-and-checked_in)).

Use this endpoint for **gate rosters** — full profile, company, part-time context, and present flag together. For **check-in timestamps** only, use [List check-ins](#list-check-ins---apiattendancecheck-ins) or [List check-outs](#list-check-outs---apiattendancecheck-outs).

**Parameters** (query)


| Name         | Required | Description                                                                                                      |
| ------------ | -------- | ---------------------------------------------------------------------------------------------------------------- |
| `active`     | No       | Same semantics as companies: `true`/`1`/`yes`, `false`/`0`/`no`, or omit for all                               |
| `workday`    | No       | Default **`all`**. **`all`**, **`today`**, or a calendar weekday slug (`monday` … `sunday`). Filters use slot precedence (direct calendar row, then **`weekdays`**, then **`all-week`**). Aggregate slugs **`weekdays`** / **`all-week`** are invalid here. |
| `shift`      | No       | When **`workday`** is not **`all`**: optional **`all-day`**, **`morning`**, or **`afternoon`**. Ignored for **`workday=all`**. |
| `checked_in` | No       | Filter by today’s **`attendances`** row (camp calendar day — same rule as the **`checked_in`** field on each row; **`checkout_at`** ignored). `true`/`1`/`yes` = has a row; `false`/`0`/`no` = no row; omit = all. Not tied to **`?workday=`**. |
| `auth_group` | No       | Filter by JWT tier from **`authentications.auth_group`**: **`employee`** (kids; default when no auth row), **`staff`**, or **`admin`**. Invalid value → **`400`** **`INVALID_AUTH_GROUP`**. |


**Endpoint sample**

```http
GET /api/employees?active=true&workday=today HTTP/1.1
Host: localhost:5000
```

```bash
curl -s "http://localhost:5000/api/employees"
curl -s "http://localhost:5000/api/employees?active=true"
curl -s "http://localhost:5000/api/employees?workday=tuesday"
curl -s "http://localhost:5000/api/employees?workday=tuesday&shift=afternoon"
curl -s "http://localhost:5000/api/employees?active=true&checked_in=false"
curl -s "http://localhost:5000/api/employees?active=true&checked_in=false&auth_group=employee"
curl -s "http://localhost:5000/api/employees?active=true&checked_in=true&auth_group=staff"
```

**JSON request**
None.

**JSON response** (example — assumes calendar **Monday** in camp timezone; Monika has a Monday morning slot; Anna is full-time)

```json
{
  "employees": [
    {
      "id": 1,
      "first_name": "Monika",
      "last_name": "Mustermann",
      "employee_number": "M00155",
      "age": 35,
      "can_leave_alone": false,
      "role": "Betreuer",
      "company": "Bank",
      "active": true,
      "notes": null,
      "created_at": "2026-01-15T10:00:00+00:00",
      "updated_at": "2026-01-15T10:00:00+00:00",
      "full_time": false,
      "workday": "today",
      "shift": "morning",
      "checked_in": true
    },
    {
      "id": 2,
      "first_name": "Anna",
      "last_name": "Schmidt",
      "employee_number": "A0265",
      "age": 28,
      "can_leave_alone": true,
      "role": "Helferin",
      "company": "",
      "active": true,
      "notes": null,
      "created_at": "2026-01-15T10:00:00+00:00",
      "updated_at": "2026-01-15T10:00:00+00:00",
      "full_time": true,
      "workday": "today",
      "shift": "all-day",
      "checked_in": false
    }
  ],
  "count": 2
}
```

**HTTP status codes**


| Code | Meaning |
| ---- | ------- |
| 200  | OK |
| 400  | `{"error": "INVALID_PART_TIME_WORKDAY"}`, `{"error": "INVALID_PART_TIME_SHIFT"}`, or `{"error": "INVALID_AUTH_GROUP"}` |


---

### Get employee - /api/employees/<employee_number>

**Explanation**
Returns one camp participant by `employee_number` (one employee record). Checksum validated when `VALIDATE_CHECK_SUM` is enabled. **`workday`** and **`shift`** use **calendar today** in camp timezone (see [Part-time context on employee responses](#part-time-context-on-employee-responses)). **`checked_in`** reflects today’s attendance row (see [Attendance and `checked_in`](#attendance-and-checked_in)).

**Parameters** (path)


| Name              | Required | Description   |
| ----------------- | -------- | ------------- |
| `employee_number` | Yes      | e.g. `M00155` |


**Endpoint sample**

```http
GET /api/employees/M00155 HTTP/1.1
Host: localhost:5000
```

```bash
curl -s "http://localhost:5000/api/employees/M00155"
```

**JSON request**
None.

**JSON response** (example)

```json
{
  "id": 1,
  "first_name": "Max",
  "last_name": "Mustermann",
  "employee_number": "M00155",
  "age": 35,
  "can_leave_alone": false,
  "role": "Betreuer",
  "company": "Bank",
  "active": true,
  "notes": null,
  "created_at": "2026-01-15T10:00:00+00:00",
  "updated_at": "2026-01-15T10:00:00+00:00",
  "full_time": false,
  "workday": "today",
  "shift": "morning",
  "checked_in": true
}
```

**HTTP status codes**


| Code | Meaning                              |
| ---- | ------------------------------------ |
| 200  | OK                                   |
| 400  | Error: `{"error": "EMPLOYEE_NUMBER_WRONG"}` |
| 404  | Error: `{"error": "EMPLOYEE_NOT_FOUND"}`    |


---

### Create employee - /api/employees

**Explanation**
Creates a camp participant (employee record). Validates checksum on `employee_number` when enabled. The server stores an **`Authentication`** row: **`auth_group`** from JSON, **`password_must_change`** `true`, and an initial password hash from **`last_name`** (same scheme as staff **reset-password**—sign-in compares passwords case-insensitively). **Authorization:** admin required — send `Authorization: Bearer <token>` for an admin session ([Endpoint index](#endpoint-index), [Authentication](#authentication)).

**Parameters**
None.

**Endpoint sample**

```http
POST /api/employees HTTP/1.1
Host: localhost:5000
Content-Type: application/json
Authorization: Bearer <jwt-access-token>
```

```bash
curl -s -X POST http://localhost:5000/api/employees \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"first_name":"Max","last_name":"Mustermann","employee_number":"M00155","age":16,"role":"Betreuer","auth_group":"staff","can_leave_alone":false}'
```

**JSON request**


| Field             | Required | Description                   |
| ----------------- | -------- | ----------------------------- |
| `first_name`      | Yes      |                               |
| `last_name`       | Yes      |                               |
| `employee_number` | Yes      | Unique; checksum when enabled |
| `age`             | Yes      | Integer age in whole years. |
| `can_leave_alone` | No       | Default `true`. JSON boolean, or `0`/`1`, or `true`/`false`/`yes`/`no` strings. |
| `role`            | Yes      | Descriptive camp role (not app permission) |
| `auth_group`      | Yes      | App permission: `employee`, `staff`, or `admin` |
| `active`          | No       | Default `true`. Same boolean coercion as `can_leave_alone`. |
| `notes`           | No       | Notes (optional)              |


Example:

```json
{
  "first_name": "Max",
  "last_name": "Mustermann",
  "employee_number": "M00155",
  "age": 16,
  "can_leave_alone": false,
  "role": "Betreuer",
  "auth_group": "staff",
  "active": true,
  "notes": null
}
```

**JSON response** (example — `company` is empty string when none; **`auth_group`** echoes the app permission stored for the new account; list/get employee endpoints omit `auth_group`)

```json
{
  "id": 1,
  "first_name": "Max",
  "last_name": "Mustermann",
  "employee_number": "M00155",
  "age": 16,
  "can_leave_alone": false,
  "role": "Betreuer",
  "company": "",
  "active": true,
  "notes": null,
  "created_at": "2026-01-15T10:00:00+00:00",
  "updated_at": "2026-01-15T10:00:00+00:00",
  "auth_group": "staff"
}
```

**HTTP status codes**


| Code | Meaning                                      |
| ---- | -------------------------------------------- |
| 201  | Created                                      |
| 400  | Error: validation may return `{"error": "REQUEST_BODY_MUST_BE_A_JSON_OBJECT"}`, `{"error": "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"}`, `{"error": "INVALID_AGE_IN_JSON"}`, `{"error": "INVALID_JSON_BOOLEAN_IN_JSON"}`, `{"error": "EMPLOYEE_NUMBER_WRONG_IN_JSON"}`, or `{"error": "INVALID_AUTH_GROUP_IN_JSON"}` |
| 403  | Error: `{"error": "FORBIDDEN_WRONG_AUTH_GROUP"}` (not admin) |
| 409  | Error: `{"error": "CONSTRAINT_VIOLATION", "message": "Create failed, because entry is already in database"}` |


---

### Update employee - /api/employees/<employee_number>

**Explanation**
Updates fields present in the body for the camp participant identified by the path `employee_number`. **Authorization:** admin required — send `Authorization: Bearer <token>` for an admin session ([Endpoint index](#endpoint-index), [Authentication](#authentication)).

**Parameters** (path)


| Name              | Required | Description                                  |
| ----------------- | -------- | -------------------------------------------- |
| `employee_number` | Yes      | Current employee number (checksum validated) |


**Endpoint sample**

```http
PUT /api/employees/M00155 HTTP/1.1
Host: localhost:5000
Content-Type: application/json
Authorization: Bearer <jwt-access-token>
```

```bash
curl -s -X PUT "http://localhost:5000/api/employees/M00155" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"role":"Leiter"}'
```

**JSON request** (include only keys you want to change; body must be a JSON object)

| Field             | Required | Description                   |
| ----------------- | -------- | ----------------------------- |
| `first_name`      | No       | Omit or set to update         |
| `last_name`       | No       | Omit or set to update         |
| `employee_number` | No       | New value if renumbering; checksum when enabled |
| `age`             | No       | When present: integer age in whole years. Do not send a JSON boolean for `age`. |
| `can_leave_alone` | No       | Same boolean coercion as on create. |
| `role`            | No       | Omit or set to update         |
| `active`          | No       | Omit or set to update         |
| `notes`           | No       | Omit or set to update         |

```json
{
  "first_name": "Max",
  "last_name": "Mustermann",
  "employee_number": "M00155",
  "age": 17,
  "can_leave_alone": true,
  "role": "Leiter",
  "active": true,
  "notes": "Note"
}
```

**JSON response**
Same shape as `GET` one employee (updated row).

**HTTP status codes**


| Code | Meaning                                                   |
| ---- | --------------------------------------------------------- |
| 200  | OK                                                        |
| 400  | Error: `{"error": "REQUEST_BODY_MUST_BE_A_JSON_OBJECT"}`, `{"error": "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"}`, `{"error": "INVALID_AGE_IN_JSON"}`, `{"error": "INVALID_JSON_BOOLEAN_IN_JSON"}`, or `{"error": "EMPLOYEE_NUMBER_WRONG_IN_JSON"}` / `{"error": "EMPLOYEE_NUMBER_WRONG"}` |
| 403  | Error: `{"error": "FORBIDDEN_WRONG_AUTH_GROUP"}` (not admin) |
| 404  | Error: `{"error": "EMPLOYEE_NOT_FOUND"}`                         |
| 409  | Error: `{"error": "CONSTRAINT_VIOLATION", "message": "Create failed, because entry is already in database"}` |


---

### Delete employee - /api/employees/<employee_number>

**Explanation**
By default performs a **soft delete** (`active=false`). With `?hard=true`, removes the row permanently. **Authorization:** admin required — send `Authorization: Bearer <token>` for an admin session ([Endpoint index](#endpoint-index), [Authentication](#authentication)).

**Parameters** (path)


| Name              | Required | Description     |
| ----------------- | -------- | --------------- |
| `employee_number` | Yes      | Target camp participant (`employee_number` in path) |


**Parameters** (query)


| Name   | Required | Description                          |
| ------ | -------- | ------------------------------------ |
| `hard` | No       | `true` / `1` / `yes` for hard delete |


**Endpoint sample**

```http
DELETE /api/employees/M00155?hard=true HTTP/1.1
Host: localhost:5000
Authorization: Bearer <jwt-access-token>
```

```bash
curl -s -X DELETE "http://localhost:5000/api/employees/M00155" \
  -H "Authorization: Bearer $TOKEN"
curl -s -X DELETE "http://localhost:5000/api/employees/M00155?hard=true" \
  -H "Authorization: Bearer $TOKEN"
```

**JSON request**
None.

**JSON response** (soft delete — full employee object)

```json
{
  "id": 1,
  "first_name": "Max",
  "last_name": "Mustermann",
  "employee_number": "M00155",
  "age": 35,
  "can_leave_alone": false,
  "role": "Betreuer",
  "company": "",
  "active": false,
  "notes": null,
  "created_at": "2026-01-15T10:00:00+00:00",
  "updated_at": "2026-01-15T10:00:00+00:00"
}
```

**JSON response** (hard delete)

```json
{
  "message": "employee deleted permanently"
}
```

**HTTP status codes**


| Code | Meaning |
| ---- | ------- |
| 200  | Soft or hard delete succeeded |
| 400  | Error: `{"error": "EMPLOYEE_NUMBER_WRONG"}` |
| 403  | Error: `{"error": "FORBIDDEN_WRONG_AUTH_GROUP"}` (not admin) |
| 404  | Error: `{"error": "EMPLOYEE_NOT_FOUND"}` |
| 409  | Error: `{"error": "CONSTRAINT_VIOLATION", "message": "Delete failed, because related entries in JobAssignment table"}` |


---

<a id="part-time-api"></a>

## Part-time API

Admin CRUD on stored **`part_times`** rows at **`/api/part-time/{employee_number}`**. Normal camp processing (employee lists, kiosk, **`GET /api/auth/me`**) continues to use **`/api/employees`** for derived **`full_time`**, **`workday`**, and **`shift`** — see [Part-time context on employee responses](#part-time-context-on-employee-responses) and [Aggregate part-time patterns](#aggregate-part-time-patterns).

| Need | Call |
| ---- | ---- |
| Who works today? / roster / shift display | **`GET /api/employees`** (derived fields) |
| What rows are stored for editing? | **`GET /api/part-time/{employee_number}`** |
| Admin edit schedule | **`POST`** / **`PUT`** / **`DELETE /api/part-time/{employee_number}`** |

**Full-time everywhere** = **delete all** part-time rows (`DELETE /api/part-time/{employee_number}` with no query), not `{ "workday": "all-week", "shift": "all-day" }`.

Every route validates path **`employee_number`** before database access (same rules as the Employee API): invalid format/checksum → **`400`** **`EMPLOYEE_NUMBER_WRONG`**; valid number but no employee row → **`404`** **`EMPLOYEE_NOT_FOUND`**.

**Write validation** (POST, PUT, and DELETE-one **`?workday=`**):

1. **`verify_part_time_stored_workday`** → **`400`** **`INVALID_PART_TIME_WORKDAY`**
2. **`verify_part_time_shift`** → **`400`** **`INVALID_PART_TIME_SHIFT`**
3. **`validate_part_time_combination`** → **`400`** **`INVALID_PART_TIME_COMBINATION`**

Allowed stored **`workday`** values (including aggregates) are listed under **`la-server.part_time_workdays`** on **`GET /api/village-data`**.

### List stored part-time rows - /api/part-time/<employee_number>

**Explanation**
Returns **stored** slugs for one employee — not contextual **`today`**. Rows are ordered by **`PART_TIME_STORED_WORKDAYS`**. Reject any **`?workday=`** query on GET → **`400`** **`INVALID_PART_TIME_WORKDAY`**.

**Parameters** (path)

| Name              | Required | Description   |
| ----------------- | -------- | ------------- |
| `employee_number` | Yes      | e.g. `M00252` |

**Endpoint sample**

```http
GET /api/part-time/M00252 HTTP/1.1
Host: localhost:5000
```

```bash
curl -s "http://localhost:5000/api/part-time/M00252"
```

**JSON request**
None.

**JSON response** (example)

```json
{
  "employee_number": "M00252",
  "part_times": [
    {
      "id": 1,
      "workday": "weekdays",
      "shift": "morning",
      "notes": null,
      "created_at": "2026-01-15T10:00:00+00:00",
      "updated_at": "2026-01-15T10:00:00+00:00"
    }
  ],
  "count": 1
}
```

**HTTP status codes**

| Code | Meaning |
| ---- | ------- |
| 200  | OK |
| 400  | `{"error": "EMPLOYEE_NUMBER_WRONG"}` or `{"error": "INVALID_PART_TIME_WORKDAY"}` (spurious `?workday=`) |
| 404  | `{"error": "EMPLOYEE_NOT_FOUND"}` |

---

### Create part-time row - /api/part-time/<employee_number>

**Explanation**
Creates one stored row. **`workday`** is required; **`shift`** defaults to **`all-day`**; **`notes`** is optional. Duplicate **`workday`** for the same employee → **`409`** **`CONSTRAINT_VIOLATION`** (enforced by the DB unique constraint `uq_part_times_employee_workday`). **Authorization:** admin required.

**Parameters** (path)

| Name              | Required | Description   |
| ----------------- | -------- | ------------- |
| `employee_number` | Yes      | Target employee |

**Endpoint sample**

```http
POST /api/part-time/M00252 HTTP/1.1
Host: localhost:5000
Content-Type: application/json
Authorization: Bearer <jwt-access-token>
```

```bash
curl -s -X POST "http://localhost:5000/api/part-time/M00252" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"workday":"weekdays","shift":"morning"}'
```

**JSON request**

| Field     | Required | Description |
| --------- | -------- | ----------- |
| `workday` | Yes      | Stored slug (`monday` … `sunday`, `weekdays`, `all-week`) |
| `shift`   | No       | Default **`all-day`** |
| `notes`   | No       | Optional free text |

**JSON response** (created row — **`201`**)

```json
{
  "id": 3,
  "workday": "weekdays",
  "shift": "morning",
  "notes": null,
  "created_at": "2026-01-15T10:00:00+00:00",
  "updated_at": "2026-01-15T10:00:00+00:00"
}
```

**HTTP status codes**

| Code | Meaning |
| ---- | ------- |
| 201  | Created |
| 400  | Validation errors (`INVALID_PART_TIME_WORKDAY`, `INVALID_PART_TIME_SHIFT`, `INVALID_PART_TIME_COMBINATION`, …) |
| 403  | `{"error": "FORBIDDEN_WRONG_AUTH_GROUP"}` (not admin) |
| 404  | `{"error": "EMPLOYEE_NOT_FOUND"}` |
| 409  | `{"error": "CONSTRAINT_VIOLATION", "message": "Create failed, because entry is already in database"}` |

---

### Update part-time row - /api/part-time/<employee_number>

**Explanation**
Partial update by stored **`workday`** lookup key (**`workday`** is not renamable). Include **`shift`** and/or **`notes`** to change them. Unknown row → **`404`** **`PART_TIME_NOT_FOUND`**. **Authorization:** admin required.

**Parameters** (path)

| Name              | Required | Description   |
| ----------------- | -------- | ------------- |
| `employee_number` | Yes      | Target employee |

**Endpoint sample**

```http
PUT /api/part-time/M00252 HTTP/1.1
Host: localhost:5000
Content-Type: application/json
Authorization: Bearer <jwt-access-token>
```

```bash
curl -s -X PUT "http://localhost:5000/api/part-time/M00252" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"workday":"tuesday","shift":"morning","notes":"Until noon"}'
```

**JSON request**

| Field     | Required | Description |
| --------- | -------- | ----------- |
| `workday` | Yes      | Lookup key (stored slug) |
| `shift`   | No       | New shift when present |
| `notes`   | No       | New notes; send `null` to clear |

**JSON response**
Same shape as create (**`200`**).

**HTTP status codes**

| Code | Meaning |
| ---- | ------- |
| 200  | OK |
| 400  | Validation errors |
| 403  | Not admin |
| 404  | `{"error": "EMPLOYEE_NOT_FOUND"}` or `{"error": "PART_TIME_NOT_FOUND"}` |

---

### Delete all part-time rows - /api/part-time/<employee_number>

**Explanation**
Removes every stored row for the employee (idempotent when already empty). Restores full-time: **`GET /api/employees/{employee_number}`** then shows **`full_time`: true**, **`workday`: `"today"`**, **`shift`: `"all-day"`** (when calendar today applies). **Authorization:** admin required. When **`?workday=`** is present, see [Delete one part-time row](#delete-one-part-time-row---apipart-timeemployee_numberworkday).

**Parameters** (path)

| Name              | Required | Description   |
| ----------------- | -------- | ------------- |
| `employee_number` | Yes      | Target employee |

**Endpoint sample**

```http
DELETE /api/part-time/M00252 HTTP/1.1
Host: localhost:5000
Authorization: Bearer <jwt-access-token>
```

```bash
curl -s -X DELETE "http://localhost:5000/api/part-time/M00252" \
  -H "Authorization: Bearer $TOKEN"
```

**JSON request**
None.

**JSON response**

```json
{
  "message": "part-time rows deleted",
  "count": 2
}
```

**HTTP status codes**

| Code | Meaning |
| ---- | ------- |
| 200  | OK |
| 400  | `{"error": "EMPLOYEE_NUMBER_WRONG"}` |
| 403  | Not admin |
| 404  | `{"error": "EMPLOYEE_NOT_FOUND"}` |

---

<a id="delete-one-part-time-row---apipart-timeemployee_numberworkday"></a>

### Delete one part-time row - /api/part-time/<employee_number>?workday=

**Explanation**
Deletes the row for one stored **`workday`** slug. Unknown row → **`404`** **`PART_TIME_NOT_FOUND`**. **Authorization:** admin required.

**Parameters** (path)

| Name              | Required | Description   |
| ----------------- | -------- | ------------- |
| `employee_number` | Yes      | Target employee |

**Parameters** (query)

| Name      | Required | Description |
| --------- | -------- | ----------- |
| `workday` | Yes      | Stored slug to delete |

**Endpoint sample**

```http
DELETE /api/part-time/M00252?workday=weekdays HTTP/1.1
Host: localhost:5000
Authorization: Bearer <jwt-access-token>
```

```bash
curl -s -X DELETE "http://localhost:5000/api/part-time/M00252?workday=weekdays" \
  -H "Authorization: Bearer $TOKEN"
```

**JSON request**
None.

**JSON response**

```json
{
  "message": "part-time row deleted"
}
```

**HTTP status codes**

| Code | Meaning |
| ---- | ------- |
| 200  | OK |
| 400  | `{"error": "INVALID_PART_TIME_WORKDAY"}` |
| 403  | Not admin |
| 404  | `{"error": "EMPLOYEE_NOT_FOUND"}` or `{"error": "PART_TIME_NOT_FOUND"}` |

---

<a id="attendance-api"></a>

## Attendance API

Daily **check-in** (gate scan) and optional **check-out** (early pickup) for camp participants. Timestamps are **server-only** — POST endpoints accept **no request body** (including `{}`); any body bytes → **`400`** **`REQUEST_BODY_NOT_ALLOWED`**.

| Need | Call |
| ---- | ---- |
| Staff scan at gate | **`POST /api/attendance/check-in/{employee_number}`** (staff or admin JWT) |
| Record early departure | **`POST /api/attendance/check-out/{employee_number}`** (optional; staff or admin JWT) |
| Who checked in (with times)? | **`GET /api/attendance/check-ins`** (default **`?workday=today`**) |
| Who checked out early (with times)? | **`GET /api/attendance/check-outs`** (subset with **`checkout_at`** set) |
| Who has **not** checked in yet? | **`GET /api/employees?active=true&checked_in=false`** |
| Not checked in — kids / staff / admin | **`GET /api/employees?…&auth_group=employee`** (etc.; combine with **`checked_in=false`**) |
| Full roster with present flag | **`GET /api/employees`** — **`checked_in`** on each row (optional **`?checked_in=`** filter) |
| One person’s history | **`GET /api/attendance/{employee_number}`** |

**Camp calendar:** **`camp_date`** and default **`workday=today`** use **`general.timezone`** from **`village.ini`** ([`camp_today()`](../app/camp_time.py)). List **`?workday=`** accepts **`today`** or a calendar weekday slug (**`monday`** … **`sunday`**) — that weekday in the ISO week containing camp today. Aggregate slugs **`all`**, **`weekdays`**, and **`all-week`** are **invalid** → **`400`** **`INVALID_ATTENDANCE_WORKDAY`**.

**Configuration:** **`[attendance]`** in **`village.ini`** (echoed under **`attendance`** in **`GET /api/village-data`**) controls job-assignment gates — not who may use the check-in POST endpoints (any **active** participant may be checked in or out by staff):

| Key | Default if missing | Effect |
| --- | ------------------ | ------ |
| **`require_attendance_for_kids`** | **`true`** | Kids (`auth_group` **`employee`**) need today’s check-in row before **`POST`** / **`DELETE`** **`/api/job-assignments`** |
| **`require_attendance_for_staff`** | **`false`** | When **`true`**, staff/admin need today’s check-in row for the same gate |

**GET read access:** **`GET /api/attendance/check-ins`**, **`GET /api/attendance/check-outs`**, and **`GET /api/attendance/{employee_number}`** are **public** — no JWT required (same policy as **`GET /api/employees`**). Only **`POST`** check-in and check-out require staff or admin.

Every route validates path **`employee_number`** where applicable (same rules as the Employee API): invalid format/checksum → **`400`** **`EMPLOYEE_NUMBER_WRONG`**; valid number but no employee row → **`404`** **`EMPLOYEE_NOT_FOUND`**.

### Check-in - /api/attendance/check-in/<employee_number>

**Explanation**
Staff or admin records check-in for **camp today** only. Inserts one **`attendances`** row with **`checkin_at = now()`** (UTC, timezone-aware). Duplicate check-in for the same participant on the same **`camp_date`** → **`409`** **`CONSTRAINT_VIOLATION`**. Inactive participant → **`400`** **`EMPLOYEE_NOT_ACTIVE`** (show the client that the passport belongs to an inactive participant).

**Authorization:** staff or higher — send `Authorization: Bearer <token>` ([Endpoint index](#endpoint-index), [Authentication](#authentication)).

**Parameters** (path)

| Name              | Required | Description   |
| ----------------- | -------- | ------------- |
| `employee_number` | Yes      | e.g. `M00252` |

**Endpoint sample**

```http
POST /api/attendance/check-in/M00252 HTTP/1.1
Host: localhost:5000
Authorization: Bearer <jwt-access-token>
```

```bash
curl -s -X POST "http://localhost:5000/api/attendance/check-in/M00252" \
  -H "Authorization: Bearer $TOKEN"
```

**JSON request**
None. Do **not** send a body (not even `{}`).

**JSON response** (success — **`201`**)

```json
{
  "employee_number": "M00252",
  "camp_date": "2026-05-18",
  "checkin_at": "2026-05-18T08:00:00+00:00",
  "checkout_at": null
}
```

**HTTP status codes**

| Code | Meaning |
| ---- | ------- |
| 201  | Created |
| 400  | `{"error": "REQUEST_BODY_NOT_ALLOWED"}` (any request body), `{"error": "EMPLOYEE_NOT_ACTIVE"}`, or `{"error": "EMPLOYEE_NUMBER_WRONG"}` |
| 401  | `AUTHORIZATION_REQUIRED` |
| 403  | `{"error": "FORBIDDEN_WRONG_AUTH_GROUP"}` (not staff or admin) |
| 404  | `{"error": "EMPLOYEE_NOT_FOUND"}` |
| 409  | `{"error": "CONSTRAINT_VIOLATION", "message": "Create failed, because entry is already in database"}` (duplicate check-in) |

---

### Check-out - /api/attendance/check-out/<employee_number>

**Explanation**
Staff or admin records **optional** check-out on **camp today** only. Sets **`checkout_at = now()`** on today’s row. Most participants never check out. No row for today → **`404`** **`ATTENDANCE_NOT_CHECKED_IN`**. Duplicate check-out → **`409`** **`CONSTRAINT_VIOLATION`**.

**Authorization:** staff or higher.

**Parameters** (path)

| Name              | Required | Description   |
| ----------------- | -------- | ------------- |
| `employee_number` | Yes      | e.g. `M00252` |

**Endpoint sample**

```http
POST /api/attendance/check-out/M00252 HTTP/1.1
Host: localhost:5000
Authorization: Bearer <jwt-access-token>
```

```bash
curl -s -X POST "http://localhost:5000/api/attendance/check-out/M00252" \
  -H "Authorization: Bearer $TOKEN"
```

**JSON request**
None. Do **not** send a body.

**JSON response** (success — **`200`**)

```json
{
  "employee_number": "M00252",
  "camp_date": "2026-05-18",
  "checkin_at": "2026-05-18T08:00:00+00:00",
  "checkout_at": "2026-05-18T14:30:00+00:00"
}
```

**HTTP status codes**

| Code | Meaning |
| ---- | ------- |
| 200  | OK |
| 400  | `{"error": "REQUEST_BODY_NOT_ALLOWED"}` or `{"error": "EMPLOYEE_NUMBER_WRONG"}` |
| 401  | `AUTHORIZATION_REQUIRED` |
| 403  | Not staff or admin |
| 404  | `{"error": "EMPLOYEE_NOT_FOUND"}` or `{"error": "ATTENDANCE_NOT_CHECKED_IN"}` |
| 409  | Duplicate check-out (`CONSTRAINT_VIOLATION`) |

---

### List check-ins - /api/attendance/check-ins

**Explanation**
Returns all attendance rows for the resolved **`camp_date`** (everyone who checked in), sorted by **`employee_number`** ascending. Each row includes **`checkin_at`** and **`checkout_at`** (often **`null`**). **Authorization:** public — no sign-in needed.

Participants **without** a check-in row do not appear here. For a **full roster** filtered by present / not-present (with company, part-time context, etc.), use **`GET /api/employees`** with **`?checked_in=`** — see [List employees](#list-employees---apiemployees) and [Attendance and `checked_in`](#attendance-and-checked_in).

**Parameters** (query)

| Name      | Required | Description |
| --------- | -------- | ----------- |
| `workday` | No       | Default **`today`**. **`today`** or calendar slug **`monday`** … **`sunday`**. Invalid → **`400`** **`INVALID_ATTENDANCE_WORKDAY`**. |

**Endpoint sample**

```http
GET /api/attendance/check-ins?workday=today HTTP/1.1
Host: localhost:5000
```

```bash
curl -s "http://localhost:5000/api/attendance/check-ins"
curl -s "http://localhost:5000/api/attendance/check-ins?workday=monday"
```

**JSON request**
None.

**JSON response** (example)

```json
{
  "workday": "today",
  "camp_date": "2026-05-18",
  "check_ins": [
    {
      "employee_number": "A00265",
      "first_name": "Anna",
      "last_name": "Schmidt",
      "checkin_at": "2026-05-18T08:05:00+00:00",
      "checkout_at": null
    },
    {
      "employee_number": "M00252",
      "first_name": "Monika",
      "last_name": "Mustermann",
      "checkin_at": "2026-05-18T08:00:00+00:00",
      "checkout_at": null
    },
    {
      "employee_number": "P00370",
      "first_name": "Peter",
      "last_name": "Krause",
      "checkin_at": "2026-05-18T08:15:00+00:00",
      "checkout_at": null
    }
  ],
  "count": 3
}
```

**HTTP status codes**

| Code | Meaning |
| ---- | ------- |
| 200  | OK |
| 400  | `{"error": "INVALID_ATTENDANCE_WORKDAY"}` |

---

### List check-outs - /api/attendance/check-outs

**Explanation**
Same **`workday`** rules as **`GET /api/attendance/check-ins`**, but returns only rows where **`checkout_at IS NOT NULL`** (optional departures). Sorted by **`employee_number`** ascending. **Authorization:** public — no sign-in needed.

**Parameters** (query)

| Name      | Required | Description |
| --------- | -------- | ----------- |
| `workday` | No       | Default **`today`**. Same valid values as check-ins list. |

**Endpoint sample**

```http
GET /api/attendance/check-outs?workday=today HTTP/1.1
Host: localhost:5000
```

```bash
curl -s "http://localhost:5000/api/attendance/check-outs"
```

**JSON request**
None.

**JSON response** (example)

```json
{
  "workday": "today",
  "camp_date": "2026-05-18",
  "check_outs": [
    {
      "employee_number": "A00265",
      "first_name": "Anna",
      "last_name": "Schmidt",
      "checkin_at": "2026-05-18T08:05:00+00:00",
      "checkout_at": "2026-05-18T15:00:00+00:00"
    },
    {
      "employee_number": "M00252",
      "first_name": "Monika",
      "last_name": "Mustermann",
      "checkin_at": "2026-05-18T08:00:00+00:00",
      "checkout_at": "2026-05-18T14:30:00+00:00"
    }
  ],
  "count": 2
}
```

**HTTP status codes**

| Code | Meaning |
| ---- | ------- |
| 200  | OK |
| 400  | `{"error": "INVALID_ATTENDANCE_WORKDAY"}` |

---

### Attendance history - /api/attendance/<employee_number>

**Explanation**
Returns stored attendance rows for one participant. Without **`?workday=`**, full history ordered by **`camp_date`** descending. With **`?workday=`**, zero or one row for that camp day; response echoes **`workday`** and **`camp_date`**. **Authorization:** public — no sign-in needed.

**Parameters** (path)

| Name              | Required | Description   |
| ----------------- | -------- | ------------- |
| `employee_number` | Yes      | e.g. `M00252` |

**Parameters** (query)

| Name      | Required | Description |
| --------- | -------- | ----------- |
| `workday` | No       | When set: **`today`** or **`monday`** … **`sunday`**. Omitted → full history. |

**Endpoint sample**

```http
GET /api/attendance/M00252 HTTP/1.1
Host: localhost:5000
```

```bash
curl -s "http://localhost:5000/api/attendance/M00252"
curl -s "http://localhost:5000/api/attendance/M00252?workday=today"
```

**JSON request**
None.

**JSON response** (full history — no top-level **`workday`** / **`camp_date`**)

```json
{
  "employee_number": "M00252",
  "attendances": [
    {
      "camp_date": "2026-05-18",
      "checkin_at": "2026-05-18T08:00:00+00:00",
      "checkout_at": null
    },
    {
      "camp_date": "2026-05-17",
      "checkin_at": "2026-05-17T08:05:00+00:00",
      "checkout_at": "2026-05-17T15:00:00+00:00"
    }
  ],
  "count": 2
}
```

**JSON response** (filtered — **`?workday=today`**)

```json
{
  "employee_number": "M00252",
  "attendances": [
    {
      "camp_date": "2026-05-18",
      "checkin_at": "2026-05-18T08:00:00+00:00",
      "checkout_at": null
    }
  ],
  "count": 1,
  "workday": "today",
  "camp_date": "2026-05-18"
}
```

**HTTP status codes**

| Code | Meaning |
| ---- | ------- |
| 200  | OK ( **`count`** may be **`0`** when filtered day has no row) |
| 400  | `{"error": "EMPLOYEE_NUMBER_WRONG"}` or `{"error": "INVALID_ATTENDANCE_WORKDAY"}` |
| 404  | `{"error": "EMPLOYEE_NOT_FOUND"}` |

---

## Job assignments

When village **`[attendance]`** switches require it (see [Attendance API](#attendance-api)), **`POST /api/job-assignments`** and **`DELETE /api/job-assignments/{job_assignment_number}`** require a **check-in row for camp today** on the **assignment’s participant** — not the JWT caller. The gate checks **row presence only**; **`checkout_at` is ignored** (early check-out does not block quit or take job). **`POST /api/job-assignments/reset`** and **`GET`** list are **not** gated. Missing check-in → **`400`** **`ATTENDANCE_CHECK_IN_REQUIRED`**.

### List job assignments - /api/job-assignments

**Explanation**
Lists all job assignment rows (ids reference `companies.id` and `employees.id`; each assignment is one camp participant at one company).

**Parameters**
None.

**Endpoint sample**

```http
GET /api/job-assignments HTTP/1.1
Host: localhost:5000
```

```bash
curl -s http://localhost:5000/api/job-assignments
```

**JSON request**
None.

**JSON response** (example)

```json
{
  "job_assignments": [
    {
      "id": 1,
      "job_assignment_number": "*0000195",
      "company_id": 1,
      "employee_id": 2,
      "notes": null,
      "created_at": "2026-01-15T10:00:00+00:00",
      "updated_at": "2026-01-15T10:00:00+00:00"
    },
    {
      "id": 2,
      "job_assignment_number": "*0000292",
      "company_id": 1,
      "employee_id": 3,
      "notes": null,
      "created_at": "2026-01-15T10:00:00+00:00",
      "updated_at": "2026-01-15T10:00:00+00:00"
    }
  ],
  "count": 2
}
```

Each assignment includes `job_assignment_number`: a `*` prefix, the five-digit zero-padded assignment `id`, and two ISO 7064 mod 97–10 check digits computed on those five digits only. Real responses use values generated by the API for each row.

**HTTP status codes**


| Code | Meaning |
| ---- | ------- |
| 200  | OK      |


---

### Create job assignment - /api/job-assignments

**Explanation**
Assigns an active camp participant to an active company, if capacity allows and they have no job yet (`employee_number` in JSON). When attendance is required for that participant, today’s check-in row must exist first (see [Job assignments](#job-assignments)). **Authorization:** employee or higher — send `Authorization: Bearer <token>` ([Endpoint index](#endpoint-index), [Authentication](#authentication)).

**Parameters**
None.

**Endpoint sample**

```http
POST /api/job-assignments HTTP/1.1
Host: localhost:5000
Content-Type: application/json
Authorization: Bearer <jwt-access-token>
```

```bash
curl -s -X POST http://localhost:5000/api/job-assignments \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"company_name":"Bank","employee_number":"M00155"}'
```

**JSON request**

```json
{
  "company_name": "Bank",
  "employee_number": "M00155"
}
```

**JSON response** (example)

```json
{
  "id": 1,
  "job_assignment_number": "*0000195",
  "company_id": 1,
  "employee_id": 2,
  "notes": null,
  "created_at": "2026-01-15T10:00:00+00:00",
  "updated_at": "2026-01-15T10:00:00+00:00"
}
```

Same `job_assignment_number` assignment number format as in the list response (`*` + padded id + check digits on the id digits only).

**HTTP status codes**


| Code | Meaning |
| ---- | ------- |
| 201  | Created |
| 400  | Error: possible `error` values include `{"error": "REQUEST_BODY_MUST_BE_A_JSON_OBJECT"}`, `{"error": "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"}`, `{"error": "EMPLOYEE_NUMBER_WRONG_IN_JSON"}`, `{"error": "COMPANY_NOT_ACTIVE"}`, `{"error": "EMPLOYEE_NOT_ACTIVE"}`, `{"error": "ATTENDANCE_CHECK_IN_REQUIRED"}`, `{"error": "JOB_ALREADY_ASSIGNED"}`, `{"error": "NO_JOB_LEFT"}` |
| 403  | Error: `{"error": "FORBIDDEN_WRONG_AUTH_GROUP"}` (not signed in as employee, staff, or admin) |
| 404  | Error: `{"error": "COMPANY_NOT_FOUND"}` or `{"error": "EMPLOYEE_NOT_FOUND"}` |

---

### Remove job assignment - /api/job-assignments/<job_assignment_number>

**Explanation**
Deletes the job assignment identified by `job_assignment_number`. Before the live row is removed, the server writes an **append-only** snapshot to **`job_assignment_history`** with `end_reason` **`deleted`** (employee and company fields, effective pay/tax, timing — see [Job assignment history](#job-assignment-history)). When attendance is required for the assignment’s participant, today’s check-in row must exist (same gate as create — see [Job assignments](#job-assignments)). The path string must match the assignment number format (`*` + five zero-padded id digits + ISO 7064 Mod 97,10 check digits on those five digits); checksum validation is **always** applied on this route (unlike some participant-number flows, it is not affected by `VALIDATE_CHECK_SUM`). **Authorization:** employee or higher — send `Authorization: Bearer <token>` ([Endpoint index](#endpoint-index), [Authentication](#authentication)).

**Parameters** (path)


| Name                    | Required | Description                                      |
| ----------------------- | -------- | ------------------------------------------------ |
| `job_assignment_number` | Yes      | Assignment identifier as returned by list/create |


**Endpoint sample**

```http
DELETE /api/job-assignments/<job_assignment_number> HTTP/1.1
Host: localhost:5000
Authorization: Bearer <jwt-access-token>
```

```bash
curl -s -X DELETE "http://localhost:5000/api/job-assignments/<job_assignment_number>" \
  -H "Authorization: Bearer $TOKEN"
```

**JSON request**
None.

**JSON response**

```json
{
  "message": "job deleted"
}
```

**HTTP status codes**


| Code | Meaning |
| ---- | ------- |
| 200  | `{"message": "job deleted"}` |
| 400  | Error: `{"error": "JOB_ASSIGNMENT_NUMBER_WRONG"}` (malformed assignment number format or failed checksum) or `{"error": "ATTENDANCE_CHECK_IN_REQUIRED"}` |
| 403  | Error: `{"error": "FORBIDDEN_WRONG_AUTH_GROUP"}` (not signed in as employee, staff, or admin) |
| 404  | Error: `{"error": "JOB_ASSIGNMENT_NOT_FOUND"}` (valid format but no matching assignment row) |


---

### Reset job assignments - /api/job-assignments/reset

**Explanation**
Deletes job assignments. Before each live row is removed, the server archives a snapshot to **`job_assignment_history`**: **`reset_all`** when the body is empty or omitted (all assignments), **`reset_company`** when filtering by `company_name` (see [Job assignment history](#job-assignment-history)). With an empty or omitted body, deletes **all** assignments. With `{"company_name": "..."}`, deletes only assignments for that company (company must exist). On success the response is always **200** with `{"message": "reset successful", "count": N}` where **`N`** is the number of rows deleted; **`N` may be `0`** when there were no matching assignments (for example an empty table on reset-all, or the named company currently has no assignments). **Authorization:** admin required — send `Authorization: Bearer <token>` for an admin session ([Endpoint index](#endpoint-index), [Authentication](#authentication)).

**Parameters**
None (optional JSON body).

**Endpoint sample**

```http
POST /api/job-assignments/reset HTTP/1.1
Host: localhost:5000
Content-Type: application/json
Authorization: Bearer <jwt-access-token>
```

```bash
curl -s -X POST http://localhost:5000/api/job-assignments/reset \
  -H "Authorization: Bearer $TOKEN"
curl -s -X POST http://localhost:5000/api/job-assignments/reset \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"company_name":"Bank"}'
```

**JSON request** (optional)

```json
{
  "company_name": "Bank"
}
```

**JSON response**

```json
{
  "message": "reset successful",
  "count": 3
}
```

The same shape applies when nothing was deleted: `"count": 0` and **200** (there is no separate “nothing to reset” error for this endpoint).

**HTTP status codes**


| Code | Meaning |
| ---- | ------- |
| 200  | Success: `{"message": "reset successful", "count": N}` — **`N` may be `0`** when no rows matched (still a successful reset). |
| 400  | Error: `{"error": "REQUEST_BODY_MUST_BE_A_JSON_OBJECT"}` or `{"error": "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"}` when the JSON body is invalid or `company_name` is empty (non-empty body must include a non-blank `company_name`) |
| 403  | Error: `{"error": "FORBIDDEN_WRONG_AUTH_GROUP"}` (not admin) |
| 404  | Error: `{"error": "COMPANY_NOT_FOUND"}` when filtering by an unknown `company_name` |

---

## Job assignment history

Immutable **audit trail** of ended job assignments. Rows are created **only** when a live assignment is removed — not on create:

| Trigger | `end_reason` |
| ------- | ------------ |
| **`DELETE /api/job-assignments/{job_assignment_number}`** | **`deleted`** |
| **`POST /api/job-assignments/reset`** (empty body — all assignments) | **`reset_all`** |
| **`POST /api/job-assignments/reset`** with `{"company_name": "..."}` | **`reset_company`** |

Each history row stores a **denormalized snapshot** at end time: participant name/age, company name, **effective** `hourly_pay` (`companies.hourly_pay` plus village **`[hourly_pay]`** `increase` from `village.ini`), **`tax`** from the same INI section, wall-clock **`started_at`** / **`ended_at`** (UTC ISO 8601), camp-calendar **`started_camp_date`** / **`ended_camp_date`** (`YYYY-MM-DD`), and **`minutes_worked`** (`floor` of elapsed minutes). History survives after the live **`job_assignments`** row is gone — use these endpoints for Excel/reporting instead of inferring past jobs from the live list.

**Immutability:** the HTTP API is **read-only** — only **`GET`** routes exist; **`POST`**, **`PUT`**, **`PATCH`**, and **`DELETE`** on these paths do not succeed. Rows are inserted by the job-assignment service during delete/reset (same transaction as the live delete). See also [database design — job_assignment_history](database_design.md#job_assignment_history).

| Need | Call |
| ---- | ---- |
| All archived jobs (optional filters) | **`GET /api/job-assignment-history`** (staff or admin JWT) |
| Filter by participant | **`GET /api/job-assignment-history?employee_number=P00370`** |
| Filter by company | **`GET /api/job-assignment-history?company_name=Bauhof`** |
| Jobs that ended on a camp day | **`GET /api/job-assignment-history?workday=today`** (filters **`ended_camp_date`**) |
| One child’s full history | **`GET /api/job-assignment-history/{employee_number}`** |
| Excel download (filtered list) | **`GET /api/job-assignment-history/export`** |
| Excel download (one child) | **`GET /api/job-assignment-history/{employee_number}/export`** |

**Authorization:** all four routes require **staff or higher** — send `Authorization: Bearer <token>`. No token → **`401`**; camp-participant (`employee`) token → **`403`** **`FORBIDDEN_WRONG_AUTH_GROUP`**.

**`?workday=`** on list and per-person JSON/CSV routes uses the same camp-calendar rules as [Attendance API](#attendance-api): **`today`** or **`monday`** … **`sunday`** (weekday in the ISO week containing camp today). On list routes, **`workday`** filters rows whose **`ended_camp_date`** matches that day; the JSON response echoes **`workday`** and **`ended_camp_date`** when the query param was set. Aggregate slugs **`all`**, **`weekdays`**, and **`all-week`** are **invalid** → **`400`** **`INVALID_ATTENDANCE_WORKDAY`**.

Path **`employee_number`** is validated (format/checksum when enabled) → **`400`** **`EMPLOYEE_NUMBER_WRONG`**; a valid number with no history rows still returns **200** with **`count`: `0`**.

### List job assignment history - /api/job-assignment-history

**Explanation**
Returns all archived employment snapshots, newest **`ended_at`** first. Optional query filters narrow the result set; omitted filters return the full table.

**Parameters** (query)

| Name               | Required | Description |
| ------------------ | -------- | ----------- |
| `employee_number`  | No       | e.g. `P00370` — only that participant’s rows |
| `company_name`     | No       | e.g. `Bauhof` — exact company name match |
| `workday`          | No       | **`today`** or **`monday`** … **`sunday`** — filters **`ended_camp_date`** |

**Endpoint sample**

```http
GET /api/job-assignment-history HTTP/1.1
Host: localhost:5000
Authorization: Bearer <jwt-access-token>
```

```bash
curl -s "http://localhost:5000/api/job-assignment-history" \
  -H "Authorization: Bearer $TOKEN"
curl -s "http://localhost:5000/api/job-assignment-history?employee_number=P00370" \
  -H "Authorization: Bearer $TOKEN"
curl -s "http://localhost:5000/api/job-assignment-history?company_name=Bauhof&workday=today" \
  -H "Authorization: Bearer $TOKEN"
```

**JSON request**
None.

**JSON response** (example)

```json
{
  "history": [
    {
      "employee_number": "P00370",
      "first_name": "Peter",
      "last_name": "Krause",
      "age": 40,
      "company_name": "Bauhof",
      "hourly_pay": 9,
      "tax": 10,
      "started_at": "2026-05-18T08:00:00+00:00",
      "started_camp_date": "2026-05-18",
      "ended_at": "2026-05-18T15:30:00+00:00",
      "ended_camp_date": "2026-05-18",
      "minutes_worked": 450,
      "end_reason": "deleted",
      "created_at": "2026-05-18T15:30:00+00:00"
    }
  ],
  "count": 1,
  "workday": "today",
  "ended_camp_date": "2026-05-18"
}
```

When **`?workday=`** is omitted, top-level **`workday`** and **`ended_camp_date`** are omitted. **`hourly_pay`** and **`tax`** are the **effective** values at archive time (not re-read from `village.ini` later). **`end_reason`** is one of **`deleted`**, **`reset_company`**, or **`reset_all`**.

**HTTP status codes**

| Code | Meaning |
| ---- | ------- |
| 200  | OK (**`count`** may be **`0`**) |
| 400  | `{"error": "EMPLOYEE_NUMBER_WRONG"}` or `{"error": "INVALID_ATTENDANCE_WORKDAY"}` |
| 401  | Not signed in |
| 403  | `{"error": "FORBIDDEN_WRONG_AUTH_GROUP"}` (not staff or admin) |

---

### Export job assignment history (CSV) - /api/job-assignment-history/export

**Explanation**
Downloads the same filtered result set as the JSON list as a CSV file. UTF-8 with **BOM** (`\ufeff` prefix) so Excel on Windows opens umlauts correctly. **Authorization:** staff or higher.

**Parameters** (query)
Same as [List job assignment history](#list-job-assignment-history---apijob-assignment-history): **`employee_number`**, **`company_name`**, **`workday`**.

**Endpoint sample**

```http
GET /api/job-assignment-history/export HTTP/1.1
Host: localhost:5000
Authorization: Bearer <jwt-access-token>
```

```bash
curl -s -o job-assignment-history-all.csv \
  "http://localhost:5000/api/job-assignment-history/export" \
  -H "Authorization: Bearer $TOKEN"
curl -s -o job-assignment-history-today.csv \
  "http://localhost:5000/api/job-assignment-history/export?workday=today" \
  -H "Authorization: Bearer $TOKEN"
```

**Response**
- **`Content-Type`:** `text/csv; charset=utf-8`
- **`Content-Disposition`:** `attachment; filename="job-assignment-history-{ended_camp_date_or_all}.csv"` — e.g. `job-assignment-history-2026-05-18.csv` when filtered by **`workday`**, or `job-assignment-history-all.csv` without a day filter
- **Header row** (stable column order): `employee_number`, `first_name`, `last_name`, `age`, `company_name`, `hourly_pay`, `tax`, `started_at`, `started_camp_date`, `ended_at`, `ended_camp_date`, `minutes_worked`, `end_reason`, `created_at`
- **Dates** (`started_camp_date`, `ended_camp_date`): `YYYY-MM-DD`
- **Datetimes** (`started_at`, `ended_at`, `created_at`): ISO 8601 strings (same as JSON)
- **Integers** (`minutes_worked`, `hourly_pay`, `tax`, `age`): plain numbers (no locale formatting)

**HTTP status codes**

| Code | Meaning |
| ---- | ------- |
| 200  | CSV body |
| 400  | Same validation errors as JSON list |
| 401  | Not signed in |
| 403  | Not staff or admin |

---

### Job assignment history by participant - /api/job-assignment-history/<employee_number>

**Explanation**
Full employment history for one camp participant, ordered by **`ended_at`** descending. Optional **`?workday=`** limits rows to assignments that **ended** on that camp day (same resolution as attendance). **Authorization:** staff or higher.

**Parameters** (path)

| Name              | Required | Description   |
| ----------------- | -------- | ------------- |
| `employee_number` | Yes      | e.g. `P00370` |

**Parameters** (query)

| Name      | Required | Description |
| --------- | -------- | ----------- |
| `workday` | No       | When set: **`today`** or **`monday`** … **`sunday`**. Omitted → full history. |

**Endpoint sample**

```http
GET /api/job-assignment-history/P00370 HTTP/1.1
Host: localhost:5000
Authorization: Bearer <jwt-access-token>
```

```bash
curl -s "http://localhost:5000/api/job-assignment-history/P00370" \
  -H "Authorization: Bearer $TOKEN"
curl -s "http://localhost:5000/api/job-assignment-history/P00370?workday=today" \
  -H "Authorization: Bearer $TOKEN"
```

**JSON request**
None.

**JSON response** (example)

```json
{
  "employee_number": "P00370",
  "history": [
    {
      "employee_number": "P00370",
      "first_name": "Peter",
      "last_name": "Krause",
      "age": 40,
      "company_name": "Bauhof",
      "hourly_pay": 9,
      "tax": 10,
      "started_at": "2026-05-18T08:00:00+00:00",
      "started_camp_date": "2026-05-18",
      "ended_at": "2026-05-18T15:30:00+00:00",
      "ended_camp_date": "2026-05-18",
      "minutes_worked": 450,
      "end_reason": "deleted",
      "created_at": "2026-05-18T15:30:00+00:00"
    }
  ],
  "count": 1
}
```

**HTTP status codes**

| Code | Meaning |
| ---- | ------- |
| 200  | OK (**`count`** may be **`0`**) |
| 400  | `{"error": "EMPLOYEE_NUMBER_WRONG"}` or `{"error": "INVALID_ATTENDANCE_WORKDAY"}` |
| 401  | Not signed in |
| 403  | Not staff or admin |

---

### Export job assignment history by participant (CSV) - /api/job-assignment-history/<employee_number>/export

**Explanation**
Downloads one participant’s employment history as CSV (same columns and Excel-friendly encoding as the list export). Optional **`?workday=`** applies the same **`ended_camp_date`** filter as the JSON route. **Authorization:** staff or higher.

**Parameters** (path)

| Name              | Required | Description   |
| ----------------- | -------- | ------------- |
| `employee_number` | Yes      | e.g. `P00370` |

**Parameters** (query)

| Name      | Required | Description |
| --------- | -------- | ----------- |
| `workday` | No       | Same as per-person JSON route |

**Endpoint sample**

```http
GET /api/job-assignment-history/P00370/export HTTP/1.1
Host: localhost:5000
Authorization: Bearer <jwt-access-token>
```

```bash
curl -s -o job-assignment-history-P00370.csv \
  "http://localhost:5000/api/job-assignment-history/P00370/export" \
  -H "Authorization: Bearer $TOKEN"
curl -s -o job-assignment-history-P00370-today.csv \
  "http://localhost:5000/api/job-assignment-history/P00370/export?workday=today" \
  -H "Authorization: Bearer $TOKEN"
```

**Response**
Same CSV format as [Export job assignment history (CSV)](#export-job-assignment-history-csv---apijob-assignment-historyexport). **`Content-Disposition`** filename: `job-assignment-history-{employee_number}.csv`.

**HTTP status codes**

| Code | Meaning |
| ---- | ------- |
| 200  | CSV body |
| 400  | `{"error": "EMPLOYEE_NUMBER_WRONG"}` or `{"error": "INVALID_ATTENDANCE_WORKDAY"}` |
| 401  | Not signed in |
| 403  | Not staff or admin |

---

## Village data (Spielstadt configuration)

Camp-specific **name**, **currency** labels, optional **`[village-theme]`** UI palette (hex strings for clients), other optional INI sections, and **image paths** live on the server under **`village_data/`** at the repository root (not under `data/`). The server resolves this directory from the project root, not from the process working directory. Deployments edit **`village_data/village.ini`** and files under **`village_data/images/`** (or rely on samples created by **`init-env`** from `data/`—see the [README](../README.md)). Implementations: [`app/routes/village_data.py`](../app/routes/village_data.py) (HTTP); INI load and parse in [`app/village_config.py`](../app/village_config.py).

**INI → JSON:** The file is parsed with Python’s `configparser`. Each **`[section]`** becomes a top-level key in the JSON object; each option becomes a string value inside that object. Optional double quotes around values in the INI are stripped in the API output. Option names are normalized to **lower case** by the parser. Inline remarks on the same line as a value must use **`;`** (not **`#`**); that way hex colors like **`#2563eb`** stay intact **as the value**. A **`#`** that starts **an entire comment line** (full-line **`#`** comment) remains valid.

**`[village-theme]`:** Optional section for **client apps only**. Keys are typically CSS-style hex colors (`accent`, `on-accent`, status pairs such as `ok` / `ok-bg`). LA-Server does **not** apply these colors to HTTP responses; it only passes them through under the JSON key **`village-theme`** (matching the INI section name). Omit the section if a deployment does not need themed UIs. A full sample lives in the repo’s **`data/village.ini`**.

**Runtime-only `la-server`:** The response always includes a top-level **`la-server`** object built by the server (auth groups, part-time and company-jobs-max enum lists, whether employee-number checksum validation is enabled, JWT TTL hints in **minutes** for access and refresh, etc.). When checksum validation is off, **`employee_number_checksum_algorithm`** is JSON **`null`**. It is **not** read from `village.ini` and must **not** be configured via a `[la-server]` section in the INI; if that section appears in the file, the server **overwrites** it in the JSON so the payload matches real server behavior. **`la-server.part_time_workdays`** lists **stored** slugs (calendar days plus **`weekdays`** and **`all-week`** for data entry); employee list filters and response **`workday`** labels use calendar slugs only — see [Aggregate part-time patterns](#aggregate-part-time-patterns). **`la-server.company_jobs_max_workdays`** and **`la-server.company_jobs_max_shifts`** reuse the same stored slug lists for **`company_jobs_max`** schedule CRUD; company GET responses use contextual labels only — see [Company jobs max context on company responses](#company-jobs-max-context-on-company-responses).

**Camp calendar:** **`general.timezone`** in the INI (also echoed under **`general`** in this JSON) is the IANA time zone the server uses for **`workday=today`** on employee lists, contextual **`workday`** / **`shift`** on employee responses, attendance **`camp_date`** resolution, and derived **`checked_in`**. See [Part-time context on employee responses](#part-time-context-on-employee-responses) and [Attendance API](#attendance-api).

**Attendance switches:** Optional **`[attendance]`** section (echoed as top-level **`attendance`** above) sets **`require_attendance_for_kids`** and **`require_attendance_for_staff`** — booleans as strings in INI (`"true"` / `"false"`). Defaults when keys are missing: kids **`true`**, staff **`false`**. These control the job-assignment check-in gate only; see [Attendance API](#attendance-api).

**Caching:** The **INI-derived** keys are cached in memory until **`village_data/village.ini`** changes (file modification time). The **`ETag`** on **`GET /api/village-data`** is an MD5 hex digest of a **canonical JSON serialization** of the **entire** object returned to the client (all INI sections **plus** the **`la-server`** block). That way, changes from environment or app config (for example checksum validation) update **`ETag`** even when `village.ini` is unchanged. Send **`If-None-Match`** (quoted, comma-separated, or weak `W/"..."` forms are accepted) to receive **`304 Not Modified`** with an **empty body** when the represented body is unchanged.

**Logo and favicon files:** `GET /api/village-data/logo` and `GET /api/village-data/favicon` also return **`ETag`** and honor **`If-None-Match`** the same way. Their **`ETag`** is an MD5 hex digest of the resolved file’s **nanosecond mtime and size** (not the file contents). On **`200`**, responses include **`Cache-Control: public, max-age=3600, must-revalidate`**. On **`304`**, the body is **empty** (no image bytes).

---

### Spielstadt config - /api/village-data

**Explanation**
Returns the Spielstadt configuration as JSON for clients (titles, currency strings, optional **`village-theme`** colors, image path keys under **`village-images`**, and any other sections present in `village.ini`), plus the server-generated **`la-server`** metadata block described above.

**Parameters**
None. Optional request header **`If-None-Match`**: previous **`ETag`** to skip body when unchanged.

**Endpoint sample**

```http
GET /api/village-data HTTP/1.1
Host: localhost:5000
```

```bash
curl -s -D - http://localhost:5000/api/village-data
```

**JSON request**
None.

**JSON response** (shape depends on your `village.ini`; example)

```json
{
  "general": {
    "name": "Kinderspielstadt Los Ämmerles",
    "location": "Ammerbuch",
    "language": "de",
    "timezone": "Europe/Berlin",
    "year": "2026"
  },
  "currency": {
    "name": "Ammertaler",
    "name_short": "AT"
  },
  "hourly_pay": {
    "increase": "0",
    "tax": "3"
  },
  "attendance": {
    "require_attendance_for_kids": "true",
    "require_attendance_for_staff": "false"
  },
  "village-images": {
    "logo": "images/logo.png",
    "favicon": "images/favicon.png"
  },
  "village-theme": {
    "accent": "#2563eb",
    "on-accent": "#ffffff",
    "bg": "#f4f6fa",
    "surface": "#ffffff",
    "border": "#d1dae6",
    "text": "#162032",
    "muted": "#5c6b80",
    "ok":  "#15803d",
    "ok-bg": "#dcfce7",
    "warn": "#b45309",
    "warn-bg": "#fef9c3" ,
    "bad": "#b91c1c",
    "bad-bg": "#fee2e2",
  },
  "la-server": {
    "auth_groups": ["employee", "staff", "admin"],
    "part_time_shifts": ["all-day", "morning", "afternoon"],
    "part_time_workdays": [
      "monday", "tuesday", "wednesday", "thursday", "friday",
      "saturday", "sunday", "weekdays", "all-week"
    ],
    "company_jobs_max_shifts": ["all-day", "morning", "afternoon"],
    "company_jobs_max_workdays": [
      "monday", "tuesday", "wednesday", "thursday", "friday",
      "saturday", "sunday", "weekdays", "all-week"
    ],
    "validate_employee_number_checksum": true,
    "employee_number_checksum_algorithm": "ISO_7064_MOD_97_10",
    "jwt_access_ttl_minutes": 15,
    "jwt_refresh_ttl_minutes": 180
  }
}
```

**HTTP status codes**

| Code | Meaning |
| ---- | ------- |
| 200  | JSON body; response includes **`ETag`** |
| 304  | Not modified (send **`If-None-Match`** matching **`ETag`**); **no JSON body** |
| 404  | Error: `{"error": "VILLAGE_DATA_NOT_FOUND"}` |
| 500  | Error: `{"error": "VILLAGE_DATA_INVALID"}` (malformed INI) |

---

### Village logo - /api/village-data/logo

**Explanation**
Streams the **logo** file. The path comes from the **`logo`** key under the top-level **`village-images`** object in the parsed config (INI section **`[village-images]`** in `village.ini`). The path is **relative to `village_data/`** (e.g. `images/logo.png` → file `village_data/images/logo.png`).

**Parameters**
None. Optional request header **`If-None-Match`**: the **`ETag`** from a previous **`200`** response for this endpoint (same rules as `GET /api/village-data`: quoted tokens, comma-separated lists, and weak **`W/"..."`** are accepted).

**Endpoint sample**

```http
GET /api/village-data/logo HTTP/1.1
Host: localhost:5000
```

```bash
curl -s -o logo.png http://localhost:5000/api/village-data/logo
```

**JSON request**
None.

**Response body**
On **`200`**: **binary** image bytes. `Content-Type` is set from the file extension (e.g. `image/png`, `image/jpeg`). Response headers include **`ETag`** and **`Cache-Control`** (see **Caching** above).

On **`304`**: **empty** body; **`ETag`** repeats the current validator.

**HTTP status codes**

| Code | Meaning |
| ---- | ------- |
| 200  | Image bytes; **`ETag`** and **`Cache-Control`** included |
| 304  | Not modified (**`If-None-Match`** matches **`ETag`**); **no image body** |
| 400  | Error: `{"error": "INVALID_FILE_PATH"}` |
| 404  | Error: `{"error": "VILLAGE_DATA_NOT_FOUND"}`, `{"error": "VILLAGE_LOGO_NOT_CONFIGURED"}`, or `{"error": "FILE_NOT_FOUND"}` |

---

### Village favicon - /api/village-data/favicon

**Explanation**
Same as the logo endpoint, but uses the **`favicon`** key under **`village-images`** in the parsed config.

**Parameters**
None. Optional request header **`If-None-Match`**: the **`ETag`** from a previous **`200`** response for this endpoint (same rules as `GET /api/village-data`).

**Endpoint sample**

```http
GET /api/village-data/favicon HTTP/1.1
Host: localhost:5000
```

```bash
curl -s -o favicon.png http://localhost:5000/api/village-data/favicon
```

**JSON request**
None.

**Response body**
Same as **`GET /api/village-data/logo`**: **`200`** returns **binary** image bytes with **`ETag`** and **`Cache-Control`**; **`304`** returns an **empty** body.

**HTTP status codes**

| Code | Meaning |
| ---- | ------- |
| 200  | Image bytes; **`ETag`** and **`Cache-Control`** included |
| 304  | Not modified (**`If-None-Match`** matches **`ETag`**); **no image body** |
| 400  | Error: `{"error": "INVALID_FILE_PATH"}` |
| 404  | Error: `{"error": "VILLAGE_DATA_NOT_FOUND"}`, `{"error": "VILLAGE_FAVICON_NOT_CONFIGURED"}`, or `{"error": "FILE_NOT_FOUND"}` |

---

# Backend development (server contributors)

**Local development is Poetry-based:** install and run everything through **`poetry install --with dev`** and **`poetry run …`**. **`pyproject.toml`** and **`poetry.lock`** are the only definitions you edit for dependencies. **`data/requirements.txt`** is **not** hand-maintained as primary: it is produced with **`poetry export`** (see the top of [`pyproject.toml`](../pyproject.toml) and the [README](../README.md)) for **production** `pip` installs. You do not use `pip install -r` or **`setup.ps1` / `setup.sh` in `provision` mode** for a dev machine (those are for **production** without Poetry on the host).

## Request flow (schemas, services, repositories)

For typical JSON endpoints the stack is:

- **Route modules** under **`app/`** — Flask Blueprints: HTTP only; validate JSON into **`app/schemas/`** dataclasses or helpers, run work inside **`g.db.begin()`**, return **`jsonify`** responses.
- **`app/services/`** — Orchestration and rules (companies, employees, attendance, job assignments, auth flows); raise **`APIError`** with stable **`error`** tokens and HTTP status codes.
- **`app/repositories/`** — SQLAlchemy **`select`** / **`execute`** / **`flush`** / **`delete`** grouped per model or use-case (no Flask imports).

Blueprint handlers stay thin (for example [`app/auth/routes.py`](../app/auth/routes.py) delegates to **`AuthService`** in [`app/services/auth.py`](../app/services/auth.py)). Password hashing and JWT helpers remain in **`app/auth/`** (`utils`, decorators).

## Prerequisites

- **Python 3.14+** (see `requires-python` in [pyproject.toml](../pyproject.toml))
- **MariaDB** reachable from your machine (tests create temporary databases; the app needs a configured schema). You can install MariaDB locally or use a remote instance.
- **Git** (repository clone) and **Poetry** on your `PATH`. You may install Poetry via `pipx`, the official installer, or another method you prefer. **`poetry export`** (used to refresh `data/requirements.txt` and in pre-commit) needs the **export plugin**; **`setup.ps1 -Mode development`** or **`setup.sh --mode development`** runs **`poetry self add poetry-plugin-export`** for you, or install it manually: `poetry self add poetry-plugin-export`.

## One-shot development setup

From the repository root, **create and prepare `.env` and `village_data/` first** with **`init-env`** (same as production step 2 in the [README](../README.md)): that copies **`.env.example`** when needed and, if **`village_data/`** is missing, seeds it from **`data/`**.

**Windows (PowerShell):**

```powershell
.\scripts\setup.ps1 -Mode init-env
```

**Linux / macOS / Git Bash** (`chmod +x ./scripts/setup.sh` once):

```bash
./scripts/setup.sh --mode init-env
```

Edit **`.env`** with at least **`SECRET_KEY`** and your **MariaDB** settings (see [`.env.example`](../.env.example) and the **Environment file** section below).

Then install the development toolchain:

**Windows:**

```powershell
.\scripts\setup.ps1 -Mode development
```

**Linux / macOS / Git Bash:**

```bash
./scripts/setup.sh --mode development
```

The **development** script:

1. Ensures **`.env`** exists (copies from **`.env.example`** only if it is still missing—use **`init-env`** above so you control creation explicitly).
2. Runs **`poetry install --with dev`** so runtime and **development** dependencies are installed (same as [`.github/workflows/pre-commit.yml`](../.github/workflows/pre-commit.yml)).
3. Runs **`poetry run pre-commit install`** so **pre-commit** runs on **commit** (see [`.pre-commit-config.yaml`](../.pre-commit-config.yaml)).
4. Validates the **test environment**: `pytest --collect-only`, then a short **MariaDB** connection using `Config.admin_db_uri()` and your `.env` credentials.

If MariaDB is not available yet (e.g. offline), use `--skip-test-env-check` / `-SkipTestEnvCheck`:

```powershell
.\scripts\setup.ps1 -Mode development -SkipTestEnvCheck
```

```bash
./scripts/setup.sh --mode development --skip-test-env-check
```

For full help: **PowerShell** `Get-Help .\scripts\setup.ps1 -Full`; **bash** `./scripts/setup.sh --help`

## Environment file (`.env`)

Create **`.env`** with **`.\scripts\setup.ps1 -Mode init-env`** or **`./scripts/setup.sh --mode init-env`**, then edit it before running the server or tests against a real database: at minimum **`SECRET_KEY`** and **MariaDB** settings (`MARIADB_HOST`, `MARIADB_PORT`, `MARIADB_USER`, `MARIADB_PASSWORD`, `MARIADB_DATABASE`). Comments in [`.env.example`](../.env.example) describe each variable. If you run **development** without a `.env` file, the setup script will copy **`.env.example`** to **`.env`**, but the intended workflow is **`init-env` first** so the step is obvious. Production database creation and the **non-Poetry** venv path (`provision`) are in the [README](../README.md)—**do not** mix **`provision`** with Poetry on the same dev tree; use **Poetry** for development.

## Spielstadt assets (`village_data/`)

Client-visible **branding and config** are not stored in MariaDB; they come from **`village_data/village.ini`** and static files under **`village_data/`** (see **Village data** in the [README](../README.md)). After **`init-env`**, adjust **`village.ini`** and images for your environment; the running server reloads from disk when **`village.ini`**’s modification time changes (in-process cache). Set **`general.timezone`** to the camp’s IANA time zone — employee **`workday=today`** and contextual **`workday`** / **`shift`** fields depend on it ([`get_camp_timezone()`](../app/village_config.py), [Part-time context on employee responses](#part-time-context-on-employee-responses) in this guide).

## Load and stress testing

Functional tests in this repository (`poetry run pytest`) check **correctness**, not throughput or concurrency under camp-day load.

Load and stress scenarios live in a **separate repository**, **[`la-loadtest`](../../la-loadtest)** (sibling folder to `la-server`). It uses [Locust](https://locust.io/) to simulate kiosk and staff API traffic against a **staging** LA-Server instance (never production camp data).

Typical workflow:

1. Start staging LA-Server (`DEBUG=false`, default `THREADS=4`).
2. In `la-loadtest`: copy `.env.example` to `.env`, `poetry install`, run Locust (see [`la-loadtest/README.md`](../../la-loadtest/README.md)).
3. Optionally poll `GET /api/health/runtime` (admin JWT) during a run — [Runtime diagnostics](#runtime-diagnostics---apihealthruntime) — to watch SQLAlchemy pool and concurrency peaks.

## Day-to-day commands

| Task | Command |
| ---- | ------- |
| Run tests | `poetry run pytest` |
| Run all pre-commit hooks on the tree (same idea as CI) | `poetry run pre-commit run --all-files` |
| Start the server (after configuring `.env`) | `.\start.ps1` / `./start.sh` or `poetry run python main.py` |

CI runs **`poetry install --with dev`** then **`poetry run pre-commit run --all-files`** on push and pull requests; keeping your local hook install and dependencies aligned avoids surprises.

## Editor / IDE

The repo includes [`poetry.toml`](../poetry.toml) with **`in-project = true`**, so Poetry’s environment is **`.venv`** in the project root (not only under `%LOCALAPPDATA%` when in-project was off). In VS Code, choose **Python: Select Interpreter** and pick **`.venv\Scripts\python.exe`** (Windows) or **`.venv/bin/python`** (Linux/macOS) so the same environment is used as in the terminal.

## If you already ran `provision` on this clone (optional recovery)

`provision` creates **`.venv`** with **pip** and `data/requirements.txt`. That is **not** a Poetry environment. If you use **`poetry run …`** after that, Poetry can report a **broken** **`.venv`** or missing imports. For **development, use Poetry only**: run **`.\scripts\setup.ps1 -Mode development -ForceRecreatePoetryVenv`** or **`./scripts/setup.sh --mode development --force-recreate-poetry-venv`**, or delete **`.venv`** and run **`poetry install --with dev`**, then always **`poetry run pytest`**, **`poetry run python`**, and point your IDE at the venv’s Python (e.g. **`.venv/Scripts/python.exe`** on Windows, **`.venv/bin/python`** on Linux/macOS). Prefer a **separate folder or clone** for production-style `provision` tests if you need both workflows.
