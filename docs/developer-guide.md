# Developer Guide

## Overview

The **LA-Server** (Kinderspielstadt Los Ämmerles) is a Flask application backed by **MariaDB**. It exposes a JSON REST API for companies, **camp participants** (children and staff; “employees” in paths and JSON), job assignments during the summer camp, and **Spielstadt branding / configuration** (read from `village_data/` on the server: `village.ini` plus static images). Clients (e.g. job center apps) call these endpoints over HTTP.

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
  "role": "participant",
  "company": "Example Co",
  "active": true,
  "notes": null,
  "created_at": "2025-06-01T10:00:00",
  "updated_at": "2025-06-01T10:00:00",
  "auth_group": "employee"
}
```

## Errors and status codes

- Most validation and not-found cases use response body `{"error": "<CODE>"}` and an HTTP status (often `400`, `404`).
- Database constraint issues may return `**409`** with `{"error": "CONSTRAINT_VIOLATION", "message": "Create failed, because entry is already in database"}` (duplicate / unique violation) or `{"error": "CONSTRAINT_VIOLATION", "message": "Delete failed, because related entries in JobAssignment table"}` (delete blocked by related rows), as implemented in [`app/errors.py`](../app/errors.py).
- Uncaught DB errors: `**500**` with `DATABASE_ERROR`. Unhandled exceptions: `**500**` with `INTERNAL_SERVER_ERROR`, per [`app/errors.py`](../app/errors.py). For both, a **`message`** field is included in the JSON **only when** server **`DEBUG`** is enabled (otherwise the body is just `{"error": "<CODE>"}`).

**Common error codes** include: `REQUEST_BODY_MUST_BE_A_JSON_OBJECT`, `REQUIRED_JSON_INPUT_MISSING_OR_EMPTY`, `COMPANY_NOT_FOUND`, `EMPLOYEE_NOT_FOUND`, `COMPANY_NOT_ACTIVE`, `EMPLOYEE_NOT_ACTIVE`, `JOB_ALREADY_ASSIGNED`, `NO_JOB_LEFT`, `NO_JOB_ASSIGNED`, `EMPLOYEE_NUMBER_WRONG`, `BAD_CREDENTIALS`, `FORBIDDEN_WRONG_AUTH_GROUP`, `OLD_PASSWORD_IS_INCORRECT`, `AUTHORIZATION_REQUIRED`, `EXPIRED_TOKEN`, `INVALID_TOKEN`, `DATABASE_ERROR`, `INTERNAL_SERVER_ERROR`, and variants with `_IN_JSON` where applicable.

JWT responses from Flask-JWT-Extended include a `message` next to `error` where applicable; see [`app/__init__.py`](../app/__init__.py). **HTTP mapping:** missing `Authorization` / Bearer → **`401`** `AUTHORIZATION_REQUIRED`; expired JWT → **`401`** `EXPIRED_TOKEN`; malformed or invalid Bearer / wrong token type for the loader → **`422`** `INVALID_TOKEN`.

For **village / Spielstadt config** endpoints: `VILLAGE_DATA_NOT_FOUND` (missing `village_data/village.ini`), `VILLAGE_LOGO_NOT_CONFIGURED` / `VILLAGE_FAVICON_NOT_CONFIGURED` (INI lacks the key under `[images]`), `FILE_NOT_FOUND` (path in INI points to a file that does not exist on disk), `INVALID_FILE_PATH` (unsafe or absolute path in INI), `VILLAGE_DATA_INVALID` (INI parse failure on the server).

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

**List endpoints (no pagination):** `GET /api/companies`, `GET /api/employees`, and `GET /api/job-assignments` return the **full** result set in one response (no `limit`/`offset`). Plan accordingly for large datasets or future API versions.

| Method | Path                                     | Summary                                     | Authorization                    |
| ------ | ---------------------------------------- | ------------------------------------------- | -------------------------------- |
| GET    | `/api/health`                            | Liveness                                    | public                           |
| GET    | `/api/health/db`                         | Database connectivity                       | public                           |
| GET    | `/api/health/runtime`                    | Pool, peaks, redacted DB (no customer data) | admin required                   |
| POST   | `/api/auth/login`                        | Sign in                                     | public                           |
| GET    | `/api/auth/me`                           | Current employee profile                    | employee or higher               |
| POST   | `/api/auth/set-auth-group`               | Change another user’s permission level      | admin required                   |
| POST   | `/api/auth/password/set-password`        | Change password                             | employee or higher               |
| POST   | `/api/auth/password/reset-password`      | Reset password to initial value             | staff or higher                  |
| POST   | `/api/auth/refresh`                      | Refresh session token                       | employee or higher               |
| POST   | `/api/auth/logout`                       | Logout                                      | employee or higher               |
| GET    | `/api/companies`                         | List companies                              | public                           |
| GET    | `/api/companies/<company_name>`          | List one company                            | public                           |
| POST   | `/api/companies`                         | Create company                              | admin required                   |
| PUT    | `/api/companies/<company_name>`          | Update company                              | admin required                   |
| DELETE | `/api/companies/<company_name>`          | Delete company                              | admin required                   |
| GET    | `/api/employees`                         | List employees                              | public                           |
| GET    | `/api/employees/<employee_number>`       | List one employee                           | public                           |
| POST   | `/api/employees`                         | Create employee                             | admin required                   |
| PUT    | `/api/employees/<employee_number>`       | Update employee                             | admin required                   |
| DELETE | `/api/employees/<employee_number>`       | Soft or hard delete employee                | admin required                   |
| GET    | `/api/job-assignments`                   | List job assignments                        | public                           |
| POST   | `/api/job-assignments`                   | Create job assignment                       | employee or higher               |
| DELETE | `/api/job-assignments/<employee_number>` | Remove assignment for employee              | employee or higher               |
| POST   | `/api/job-assignments/reset`             | Reset assignments (optional filter)         | admin required                   |
| GET    | `/api/village-data`                      | Spielstadt config JSON (`village.ini`)      | public                           |
| GET    | `/api/village-data/logo`                 | Logo image (path from INI)                  | public                           |
| GET    | `/api/village-data/favicon`              | Favicon image (path from INI)               | public                           |
| GET    | `/api/openapi.json`                       | OpenAPI 3.0 schema (machine-readable)      | public                           |
| GET    | `/api/docs`                               | Swagger UI (interactive explorer)         | public                           |


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
Public sign-in. The server checks the JSON **`employee_number`** and **`password`** against the participant’s row in [`Authentication`](../app/models.py). On success it returns two JWT strings — **`token`** (short-lived **access**) and **`refresh_token`** (long-lived **refresh**) — plus **`auth_group`** (`employee`, `staff`, or `admin`) and **`password_must_change`**. Server implementation: [`app/auth/routes.py`](../app/auth/routes.py) (`authenticate`). Use **`token`** as `Authorization: Bearer …` on protected routes; keep **`refresh_token`** only for **`POST /api/auth/refresh`** ([Authentication](#authentication)).

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
Returns the signed-in **participant** (employee) as JSON: profile fields from the database plus **`auth_group`** from the **JWT** (not the camp descriptive **`role`** on the record). Requires a valid access token whose claim **`auth_group`** is one of `employee`, `staff`, or `admin`. Server implementation: [`app/auth/routes.py`](../app/auth/routes.py) (`me`).

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
| `role`              | string  | Camp role (e.g. participant); distinct from JWT `auth_group`. |
| `company`           | string  | Company name (empty string if none resolved from job assignment join). |
| `active`            | boolean | |
| `notes`             | string or null | |
| `created_at`        | string or null | ISO 8601 timestamp. |
| `updated_at`        | string or null | ISO 8601 timestamp. |
| `auth_group`        | string  | `employee`, `staff`, or `admin` from the JWT. |

Example:

```json
{
  "id": 1,
  "first_name": "Ada",
  "last_name": "Example",
  "employee_number": "M00155",
  "role": "participant",
  "company": "Example Co",
  "active": true,
  "notes": null,
  "created_at": "2025-06-01T10:00:00",
  "updated_at": "2025-06-01T10:00:00",
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
      "jobs": { "available": 6, "max": 8 },
      "pay_per_hour": 10,
      "active": true,
      "notes": null,
      "created_at": "2026-01-15T10:00:00+00:00",
      "updated_at": "2026-01-15T10:00:00+00:00"
    },
    {
      "id": 2,
      "company_name": "Bauhof",
      "jobs": { "available": 4, "max": 4 },
      "pay_per_hour": 10,
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
  "jobs": { "available": 6, "max": 8 },
  "pay_per_hour": 10,
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
  -d '{"company_name":"Bank","jobs_max":8,"pay_per_hour":10,"active":true}'
```

**JSON request**

| Field          | Required | Type           | Description                |
| -------------- | -------- | -------------- | -------------------------- |
| `company_name` | Yes      | string         | Unique name                |
| `jobs_max`     | Yes      | integer        | Max concurrent assignments |
| `pay_per_hour` | Yes      | integer        | payment per hour           |
| `active`       | No       | boolean        | Default `true`  (optional) |
| `notes`        | No       | string or null | Free text  (optional)      |


Example:

```json
{
  "company_name": "Bank",
  "jobs_max": 8,
  "pay_per_hour": 10,
  "active": true,
  "notes": null
}
```

**JSON response** (example)

```json
{
  "id": 1,
  "company_name": "Bank",
  "jobs": { "available": 8, "max": 8 },
  "pay_per_hour": 10,
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
  -d '{"pay_per_hour":12}'
```

**JSON request** (all optional keys; only sent fields are updated)

| Field          | Required | Type           | Description                            |
| -------------- | -------- | -------------- | -------------------------------------- |
| `company_name` | Yes      | string         | Unique name  (optional)                |
| `jobs_max`     | Yes      | integer        | Max concurrent assignments  (optional) |
| `pay_per_hour` | Yes      | integer        | payment per hour  (optional)           |
| `active`       | No       | boolean        | Default `true`  (optional)             |
| `notes`        | No       | string or null | Free text  (optional)                  |

```json
{
  "company_name": "Bank Filiale",
  "jobs_max": 10,
  "pay_per_hour": 12,
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

## Employees

In domain language, each row is a **camp participant** (child or staff). The API keeps the historical names *employee* / `employee_number`.

### List employees - /api/employees

**Explanation**
Lists employees (camp participants), optionally filtered by `active`.

**Parameters** (query)


| Name     | Required | Description                                                                      |
| -------- | -------- | -------------------------------------------------------------------------------- |
| `active` | No       | Same semantics as companies: `true`/`1`/`yes`, `false`/`0`/`no`, or omit for all |


**Endpoint sample**

```http
GET /api/employees?active=true HTTP/1.1
Host: localhost:5000
```

```bash
curl -s "http://localhost:5000/api/employees"
curl -s "http://localhost:5000/api/employees?active=true"
curl -s "http://localhost:5000/api/employees?active=false"
```

**JSON request**
None.

**JSON response** (example)

```json
{
  "employees": [
    {
      "id": 1,
      "first_name": "Max",
      "last_name": "Mustermann",
      "employee_number": "M00155",
      "role": "Betreuer",
      "company": "Bank",
      "active": true,
      "notes": null,
      "created_at": "2026-01-15T10:00:00+00:00",
      "updated_at": "2026-01-15T10:00:00+00:00"
    },
    {
      "id": 2,
      "first_name": "Anna",
      "last_name": "Schmidt",
      "employee_number": "A0265",
      "role": "Helferin",
      "company": "",
      "active": true,
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

### Get employee - /api/employees/<employee_number>

**Explanation**
Returns one camp participant by `employee_number` (one employee record). Checksum validated when `VALIDATE_CHECK_SUM` is enabled.

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
  "role": "Betreuer",
  "company": "Bank",
  "active": true,
  "notes": null,
  "created_at": "2026-01-15T10:00:00+00:00",
  "updated_at": "2026-01-15T10:00:00+00:00"
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
  -d '{"first_name":"Max","last_name":"Mustermann","employee_number":"M00155","role":"Betreuer","auth_group":"staff"}'
```

**JSON request**


| Field             | Required | Description                   |
| ----------------- | -------- | ----------------------------- |
| `first_name`      | Yes      |                               |
| `last_name`       | Yes      |                               |
| `employee_number` | Yes      | Unique; checksum when enabled |
| `role`            | Yes      | Descriptive camp role (not app permission) |
| `auth_group`      | Yes      | App permission: `employee`, `staff`, or `admin` |
| `active`          | No       | Default `true` (optional)     |
| `notes`           | No       | Notes (optional)              |


Example:

```json
{
  "first_name": "Max",
  "last_name": "Mustermann",
  "employee_number": "M00155",
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
| 400  | Error: validation may return `{"error": "REQUEST_BODY_MUST_BE_A_JSON_OBJECT"}`, `{"error": "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"}`, `{"error": "EMPLOYEE_NUMBER_WRONG_IN_JSON"}`, or `{"error": "INVALID_AUTH_GROUP_IN_JSON"}` |
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
| `role`            | No       | Omit or set to update         |
| `active`          | No       | Omit or set to update         |
| `notes`           | No       | Omit or set to update         |

```json
{
  "first_name": "Max",
  "last_name": "Mustermann",
  "employee_number": "M00155",
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
| 400  | Error: `{"error": "REQUEST_BODY_MUST_BE_A_JSON_OBJECT"}`, or `{"error": "EMPLOYEE_NUMBER_WRONG_IN_JSON"}` / `{"error": "EMPLOYEE_NUMBER_WRONG"}` |
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

## Job assignments

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
      "company_id": 1,
      "employee_id": 2,
      "notes": null,
      "created_at": "2026-01-15T10:00:00+00:00",
      "updated_at": "2026-01-15T10:00:00+00:00"
    },
    {
      "id": 2,
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

**HTTP status codes**


| Code | Meaning |
| ---- | ------- |
| 200  | OK      |


---

### Create job assignment - /api/job-assignments

**Explanation**
Assigns an active camp participant to an active company, if capacity allows and they have no job yet (`employee_number` in JSON). **Authorization:** employee or higher — send `Authorization: Bearer <token>` ([Endpoint index](#endpoint-index), [Authentication](#authentication)).

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
  "company_id": 1,
  "employee_id": 2,
  "notes": null,
  "created_at": "2026-01-15T10:00:00+00:00",
  "updated_at": "2026-01-15T10:00:00+00:00"
}
```

**HTTP status codes**


| Code | Meaning |
| ---- | ------- |
| 201  | Created |
| 400  | Error: possible `error` values include `{"error": "REQUEST_BODY_MUST_BE_A_JSON_OBJECT"}`, `{"error": "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"}`, `{"error": "EMPLOYEE_NUMBER_WRONG_IN_JSON"}`, `{"error": "COMPANY_NOT_ACTIVE"}`, `{"error": "EMPLOYEE_NOT_ACTIVE"}`, `{"error": "JOB_ALREADY_ASSIGNED"}`, `{"error": "NO_JOB_LEFT"}` |
| 403  | Error: `{"error": "FORBIDDEN_WRONG_AUTH_GROUP"}` (not signed in as employee, staff, or admin) |
| 404  | Error: `{"error": "COMPANY_NOT_FOUND"}` or `{"error": "EMPLOYEE_NOT_FOUND"}` |

---

### Remove job assignment - /api/job-assignments/<employee_number>

**Explanation**
Removes the job assignment for the given camp participant’s `employee_number` (at most one row per participant in normal operation). **Authorization:** employee or higher — send `Authorization: Bearer <token>` ([Endpoint index](#endpoint-index), [Authentication](#authentication)).

**Parameters** (path)


| Name              | Required | Description                         |
| ----------------- | -------- | ----------------------------------- |
| `employee_number` | Yes      | Camp participant whose assignment to remove |


**Endpoint sample**

```http
DELETE /api/job-assignments/M00155 HTTP/1.1
Host: localhost:5000
Authorization: Bearer <jwt-access-token>
```

```bash
curl -s -X DELETE "http://localhost:5000/api/job-assignments/M00155" \
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
| 400  | Error: `{"error": "EMPLOYEE_NUMBER_WRONG"}` or `{"error": "NO_JOB_ASSIGNED"}` |
| 403  | Error: `{"error": "FORBIDDEN_WRONG_AUTH_GROUP"}` (not signed in as employee, staff, or admin) |
| 404  | Error: `{"error": "EMPLOYEE_NOT_FOUND"}` |


---

### Reset job assignments - /api/job-assignments/reset

**Explanation**
Deletes job assignments. With an empty or omitted body, deletes **all** assignments. With `{"company_name": "..."}`, deletes only assignments for that company (company must exist). **Authorization:** admin required — send `Authorization: Bearer <token>` for an admin session ([Endpoint index](#endpoint-index), [Authentication](#authentication)).

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

**HTTP status codes**


| Code | Meaning |
| ---- | ------- |
| 200  | Reset completed (`count` may be 0) |
| 400  | Error: `{"error": "REQUEST_BODY_MUST_BE_A_JSON_OBJECT"}` or `{"error": "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"}` when the JSON body is invalid or `company_name` is empty (non-empty body must include a non-blank `company_name`) |
| 403  | Error: `{"error": "FORBIDDEN_WRONG_AUTH_GROUP"}` (not admin) |
| 404  | Error: `{"error": "COMPANY_NOT_FOUND"}` when filtering by an unknown `company_name` |

---

## Village data (Spielstadt configuration)

Camp-specific **name**, **currency** labels, optional extra INI sections, and **image paths** live on the server under **`village_data/`** at the repository root (not under `data/`). The server resolves this directory from the project root, not from the process working directory. Deployments edit **`village_data/village.ini`** and files under **`village_data/images/`** (or rely on samples created by **`init-env`** from `data/`—see the [README](../README.md)). Implementations: [`app/routes/village_data.py`](../app/routes/village_data.py).

**INI → JSON:** The file is parsed with Python’s `configparser`. Each **`[section]`** becomes a top-level key in the JSON object; each option becomes a string value inside that object. Optional double quotes around values in the INI are stripped in the API output. Option names are normalized to **lower case** by the parser.

**Runtime-only `la-server`:** The response always includes a top-level **`la-server`** object built by the server (auth groups, whether employee-number checksum validation is enabled, JWT TTL hints in **minutes** for access and refresh, etc.). When checksum validation is off, **`employee_number_checksum_algorithm`** is JSON **`null`**. It is **not** read from `village.ini` and must **not** be configured via a `[la-server]` section in the INI; if that section appears in the file, the server **overwrites** it in the JSON so the payload matches real server behavior.

**Caching:** The **INI-derived** keys are cached in memory until **`village_data/village.ini`** changes (file modification time). The **`ETag`** on **`GET /api/village-data`** is an MD5 hex digest of a **canonical JSON serialization** of the **entire** object returned to the client (all INI sections **plus** the **`la-server`** block). That way, changes from environment or app config (for example checksum validation) update **`ETag`** even when `village.ini` is unchanged. Send **`If-None-Match`** (quoted, comma-separated, or weak `W/"..."` forms are accepted) to receive **`304 Not Modified`** with an **empty body** when the represented body is unchanged.

**Logo and favicon files:** `GET /api/village-data/logo` and `GET /api/village-data/favicon` also return **`ETag`** and honor **`If-None-Match`** the same way. Their **`ETag`** is an MD5 hex digest of the resolved file’s **nanosecond mtime and size** (not the file contents). On **`200`**, responses include **`Cache-Control: public, max-age=3600, must-revalidate`**. On **`304`**, the body is **empty** (no image bytes).

---

### Spielstadt config - /api/village-data

**Explanation**
Returns the Spielstadt configuration as JSON for clients (titles, currency strings, image path keys, and any other sections present in `village.ini`), plus the server-generated **`la-server`** metadata block described above.

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
    "year": "2026"
  },
  "currency": {
    "name": "Ammertaler",
    "name_short": "AT"
  },
  "salary": {
    "increase": "0",
    "tax": "3"
  },
  "images": {
    "logo": "images/logo.png",
    "favicon": "images/favicon.png"
  },
  "la-server": {
    "auth_groups": ["employee", "staff", "admin"],
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
Streams the **logo** file. The path comes from **`images.logo`** in the parsed config (typically under section **`[images]`** in `village.ini`). The path is **relative to `village_data/`** (e.g. `images/logo.png` → file `village_data/images/logo.png`).

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
Same as the logo endpoint, but uses **`images.favicon`** from the config.

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

Client-visible **branding and config** are not stored in MariaDB; they come from **`village_data/village.ini`** and static files under **`village_data/`** (see **Village data** in the [README](../README.md)). After **`init-env`**, adjust **`village.ini`** and images for your environment; the running server reloads from disk when **`village.ini`**’s modification time changes (in-process cache).

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
