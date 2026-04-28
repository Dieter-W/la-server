# Developer Guide

## Overview

The **LA-Server** (Kinderspielstadt Los Ämmerles) is a Flask application backed by **MariaDB**. It exposes a JSON REST API for companies, **camp participants** (children and staff; “employees” in paths and JSON), job assignments during the summer camp, and **Spielstadt branding / configuration** (read from `village_data/` on the server: `village.ini` plus static images). Clients (e.g. job center apps) call these endpoints over HTTP.

For environment variables, production setup (`setup.ps1` / `setup.sh` with `init-env` or `provision`), **`village_data/`** layout, and CSV bulk import, see the main [README.md](../README.md). A short pointer to this development guide is under *Development* in the [README](../README.md).

---

# Client developer (API usage)

## Base URL

By default the server listens on **`http://localhost:5000`**. In deployment, use `http://<HOST>:<PORT>` where `HOST` and `PORT` come from `.env` (see [.env.example](../.env.example)). TLS termination is assumed to happen in a reverse proxy if you serve HTTPS.

## Authentication

As a **client developer**, you are responsible for the sign-in experience, for **keeping tokens safe**, and for **attaching the right credential on every API call** that requires it. The camp issues accounts (linked to a participant and a company in the server’s data model; see [`app/models.py`](../app/models.py)); your app collects the user name and password only during sign-in and password flows, not on ordinary data requests.

**What the JWT is (short):** after a successful sign-in, the server can return a **JSON Web Token (JWT)**—a signed string that encodes who the user is, which **company** the session belongs to, the **app permission role** (one of three fixed levels, not the same as the descriptive camp “role” on the participant record), and an **expiry** time. You store that string and send it back when you call the API; you do not parse or change the payload yourself.

**What you do on a normal API call**

1. **Use HTTPS** in real deployments so the token is not exposed on the network.
2. **Send the access JWT on each request** that requires authentication: add an HTTP header
   `Authorization: Bearer <your_access_token>`
   (replace `<your_access_token>` with the stored JWT string, no quotes). Omit this header only for calls that the server documents as public (for example some health checks).
3. **Do not** send the user’s password on regular CRUD calls—only where the server explicitly expects it (sign-in, password set/change, etc., when those flows are documented).
4. If the server responds with an **authentication error** (for example missing/invalid/expired token), **obtain a new access token** the way your integration supports (refresh flow if provided, otherwise send the user through sign-in again), update storage, and **retry the request** with the new `Authorization` header.

**Sign-in and token storage:** when sign-in succeeds, persist the access token (and a refresh token, if the server returns one) in **secure storage** for your platform (not plain logs, not easy-to-read app bundles). Keep using the access token until it expires or the server rejects it.

**Expiry:** access tokens are usually short-lived. Your app should treat expiration as normal: refresh or re-login, then continue calling the API with a fresh `Authorization: Bearer …` header.

**Sign-out:** clear all stored tokens from the device and return the user to the sign-in screen. Unless the server documents a separate revoke step, assume the main effect is on the client side.

**Password changes:** the camp may reset an account or ask the user to set a password the first time; changing an existing password should still require the old password when the account is already active. After a successful password flow, the server may issue new tokens—replace your stored JWTs accordingly.

**Deployment note:** some environments may still rely on a private network or proxy in addition to JWTs. Your integration should still follow the header rule above whenever the server expects a bearer token.

## Errors and status codes

- Most validation and not-found cases use response body `{"error": "<CODE>"}` and an HTTP status (often `400`, `404`).
- Database constraint issues may return `**409`** with `{"error": "CONSTRAINT_VIOLATION", "message": "Create failed, because entry is already in database"}` (duplicate / unique violation) or `{"error": "CONSTRAINT_VIOLATION", "message": "Delete failed, because related entries in JobAssignment table"}` (delete blocked by related rows), as implemented in [`app/errors.py`](../app/errors.py).
- Uncaught DB errors: `**500**` with `DATABASE_ERROR`.

Common `error` codes include: `REQUEST_BODY_MUST_BE_A_JSON_OBJECT`, `REQUIRED_JSON_INPUT_MISSING_OR_EMPTY`, `COMPANY_NOT_FOUND`, `EMPLOYEE_NOT_FOUND`, `COMPANY_NOT_ACTIVE`, `EMPLOYEE_NOT_ACTIVE`, `JOB_ALREADY_ASSIGNED`, `NO_JOB_LEFT`, `NO_JOB_ASSIGNED`, `EMPLOYEE_NUMBER_WRONG`, and variants with `_IN_JSON` where applicable.

For **village / Spielstadt config** endpoints: `VILLAGE_DATA_NOT_FOUND` (missing `village_data/village.ini`), `VILLAGE_LOGO_NOT_CONFIGURED` / `VILLAGE_FAVICON_NOT_CONFIGURED` (INI lacks the key under `[images]`), `FILE_NOT_FOUND` (path in INI points to a file that does not exist on disk), `INVALID_FILE_PATH` (unsafe or absolute path in INI), `VILLAGE_DATA_INVALID` (INI parse failure on the server).

## Employee numbers and checksums

When `VALIDATE_CHECK_SUM=true` in `.env` (default), employee numbers must satisfy the **ISO 7064 Mod 97,10** checksum on paths and JSON fields that carry `employee_number`. See [employee-numbers.md](./employee-numbers.md). Set `VALIDATE_CHECK_SUM=false` only for local testing if needed.

---

## Endpoint index


| Method | Path                                     | Summary                             |
| ------ | ---------------------------------------- | ----------------------------------- |
| GET    | `/api/health`                            | Liveness                            |
| GET    | `/api/health/db`                         | Database connectivity               |
| GET    | `/api/health/runtime`                    | Pool, peaks, redacted DB (no customer data) |
| GET    | `/api/companies`                         | List companies                      |
| GET    | `/api/companies/<company_name>`          | Get one company                     |
| POST   | `/api/companies`                         | Create company                      |
| PUT    | `/api/companies/<company_name>`          | Update company                      |
| DELETE | `/api/companies/<company_name>`          | Delete company                      |
| GET    | `/api/employees`                         | List employees                      |
| GET    | `/api/employees/<employee_number>`       | Get one employee                    |
| POST   | `/api/employees`                         | Create employee                     |
| PUT    | `/api/employees/<employee_number>`       | Update employee                     |
| DELETE | `/api/employees/<employee_number>`       | Soft or hard delete employee        |
| GET    | `/api/job-assignments`                   | List job assignments                |
| POST   | `/api/job-assignments`                   | Create job assignment               |
| DELETE | `/api/job-assignments/<employee_number>` | Remove assignment for employee      |
| POST   | `/api/job-assignments/reset`             | Reset assignments (optional filter) |
| GET    | `/api/village-data`                      | Spielstadt config JSON (`village.ini`) |
| GET    | `/api/village-data/logo`                 | Logo image (path from INI)         |
| GET    | `/api/village-data/favicon`             | Favicon image (path from INI)      |


Each operation below uses the same blocks: **Explanation**, **Parameters**, **Endpoint sample**, **JSON request** (if any), **JSON response** (if any), **HTTP status codes**.

---

## Health

The `GET /api/health` and `GET /api/health/db` APIs are for client developers to validate the communication with the server works correct.  The third API (`GET /api/health/runtime`) provides runtime information, which are usually not needed by a client developer.

### `GET /api/health`

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

### `GET /api/health/db`

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

### `GET /api/health/runtime`

**Explanation**
Returns **operational** JSON for debugging and monitoring: process/runtime facts (Python version, platform, PID, app uptime), non-secret config flags (`DEBUG`, `TESTING`, `LOG_LEVEL`), a **password-redacted** database URL summary (host, port, database name, driver), SQLAlchemy **connection pool** statistics, and **`concurrency`**: process-local **historic peaks** for pool checkouts (parallel DB connections) and for Flask requests that have entered the per-request DB session lifecycle (`active` / `max_historic` each). Counts reset when the process restarts. It does **not** expose customer or business data.

**Privacy / deployment**
The response still reveals infrastructure details (for example DB host and database name). Use on trusted networks or behind a reverse proxy if you do not want that metadata publicly reachable.

**Parameters**
None.

**Endpoint sample**

```http
GET /api/health/runtime HTTP/1.1
Host: localhost:5000
```

```bash
curl -s http://localhost:5000/api/health/runtime
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


---

## Authentication

---

## Companies

### `GET /api/companies`

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

### `GET /api/companies/<company_name>`

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

### `POST /api/companies`

**Explanation**
Creates a new company row.

**Parameters**
None (body is JSON).

**Endpoint sample**

```http
POST /api/companies HTTP/1.1
Host: localhost:5000
Content-Type: application/json
```

```bash
curl -s -X POST http://localhost:5000/api/companies \
  -H "Content-Type: application/json" \
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
| 409  | Error: `{"error": "CONSTRAINT_VIOLATION", "message": "Create failed, because entry is already in database"}` |


---

### `PUT /api/companies/<company_name>`

**Explanation**
Updates any fields present in the JSON body. Lookup is by URL `company_name` before updates (including if you rename via `company_name` in the body).

**Parameters** (path)


| Name           | Required | Description                       |
| -------------- | -------- | --------------------------------- |
| `company_name` | Yes      | Current name used to find the row |


**Endpoint sample**

```http
PUT /api/companies/Bank HTTP/1.1
Host: localhost:5000
Content-Type: application/json
```

```bash
curl -s -X PUT "http://localhost:5000/api/companies/Bank" \
  -H "Content-Type: application/json" \
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
| 404  | Error: `{"error": "COMPANY_NOT_FOUND"}`                  |
| 409  | Error: `{"error": "CONSTRAINT_VIOLATION", "message": "Create failed, because entry is already in database"}` |


---

### `DELETE /api/companies/<company_name>`

**Explanation**
Permanently deletes the company. Fails if foreign keys still reference it (e.g. job assignments).

**Parameters** (path)


| Name           | Required | Description       |
| -------------- | -------- | ----------------- |
| `company_name` | Yes      | Company to delete |


**Endpoint sample**

```http
DELETE /api/companies/Bank HTTP/1.1
Host: localhost:5000
```

```bash
curl -s -X DELETE "http://localhost:5000/api/companies/Bank"
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
| 404  | Error: `{"error": "COMPANY_NOT_FOUND"}`                    |
| 409  | Error: `{"error": "CONSTRAINT_VIOLATION", "message": "Delete failed, because related entries in JobAssignment table"}` |


---

## Employees

In domain language, each row is a **camp participant** (child or staff). The API keeps the historical names *employee* / `employee_number`.

### `GET /api/employees`

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

### `GET /api/employees/<employee_number>`

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

### `POST /api/employees`

**Explanation**
Creates a camp participant (employee record). Validates checksum on `employee_number` when enabled.

**Parameters**
None.

**Endpoint sample**

```http
POST /api/employees HTTP/1.1
Host: localhost:5000
Content-Type: application/json
```

```bash
curl -s -X POST http://localhost:5000/api/employees \
  -H "Content-Type: application/json" \
  -d '{"first_name":"Max","last_name":"Mustermann","employee_number":"M00155","role":"Betreuer"}'
```

**JSON request**


| Field             | Required | Description                   |
| ----------------- | -------- | ----------------------------- |
| `first_name`      | Yes      |                               |
| `last_name`       | Yes      |                               |
| `employee_number` | Yes      | Unique; checksum when enabled |
| `role`            | Yes      |                               |
| `active`          | No       | Default `true` (optional)     |
| `notes`           | No       | Notes (optional)              |


Example:

```json
{
  "first_name": "Max",
  "last_name": "Mustermann",
  "employee_number": "M00155",
  "role": "Betreuer",
  "active": true,
  "notes": null
}
```

**JSON response** (example — `company` is empty string when none)

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
  "updated_at": "2026-01-15T10:00:00+00:00"
}
```

**HTTP status codes**


| Code | Meaning                                      |
| ---- | -------------------------------------------- |
| 201  | Created                                      |
| 400  | Error: validation may return `{"error": "REQUEST_BODY_MUST_BE_A_JSON_OBJECT"}`, `{"error": "REQUIRED_JSON_INPUT_MISSING_OR_EMPTY"}`, or `{"error": "EMPLOYEE_NUMBER_WRONG_IN_JSON"}` |
| 409  | Error: `{"error": "CONSTRAINT_VIOLATION", "message": "Create failed, because entry is already in database"}` |


---

### `PUT /api/employees/<employee_number>`

**Explanation**
Updates fields present in the body for the camp participant identified by the path `employee_number`.

**Parameters** (path)


| Name              | Required | Description                                  |
| ----------------- | -------- | -------------------------------------------- |
| `employee_number` | Yes      | Current employee number (checksum validated) |


**Endpoint sample**

```http
PUT /api/employees/M00155 HTTP/1.1
Host: localhost:5000
Content-Type: application/json
```

```bash
curl -s -X PUT "http://localhost:5000/api/employees/M00155" \
  -H "Content-Type: application/json" \
  -d '{"role":"Leiter"}'
```

**JSON request** (optional keys)

| Field             | Required | Description                   |
| ----------------- | -------- | ----------------------------- |
| `first_name`      | Yes      | (optional)                    |
| `last_name`       | Yes      | (optional)                    |
| `employee_number` | Yes      | (optional) Unique; checksum when enabled |
| `role`            | Yes      | (optional)                    |
| `active`          | No       | Default `true` (optional)     |
| `notes`           | No       | Notes (optional)              |

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
| 400  | Error: `{"error": "EMPLOYEE_NUMBER_WRONG_IN_JSON"}` or `{"error": "EMPLOYEE_NUMBER_WRONG"}` |
| 404  | Error: `{"error": "EMPLOYEE_NOT_FOUND"}`                         |
| 409  | Error: `{"error": "CONSTRAINT_VIOLATION", "message": "Create failed, because entry is already in database"}` |


---

### `DELETE /api/employees/<employee_number>`

**Explanation**
By default performs a **soft delete** (`active=false`). With `?hard=true`, removes the row permanently.

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
```

```bash
curl -s -X DELETE "http://localhost:5000/api/employees/M00155"
curl -s -X DELETE "http://localhost:5000/api/employees/M00155?hard=true"
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
| 404  | Error: `{"error": "EMPLOYEE_NOT_FOUND"}` |
| 409  | Error: `{"error": "CONSTRAINT_VIOLATION", "message": "Delete failed, because related entries in JobAssignment table"}` |


---

## Job assignments

### `GET /api/job-assignments`

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

### `POST /api/job-assignments`

**Explanation**
Assigns an active camp participant to an active company, if capacity allows and they have no job yet (`employee_number` in JSON).

**Parameters**
None.

**Endpoint sample**

```http
POST /api/job-assignments HTTP/1.1
Host: localhost:5000
Content-Type: application/json
```

```bash
curl -s -X POST http://localhost:5000/api/job-assignments \
  -H "Content-Type: application/json" \
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
| 404  | Error: `{"error": "COMPANY_NOT_FOUND"}` or `{"error": "EMPLOYEE_NOT_FOUND"}` |

---

### `DELETE /api/job-assignments/<employee_number>`

**Explanation**
Removes the job assignment for the given camp participant’s `employee_number` (at most one row per participant in normal operation).

**Parameters** (path)


| Name              | Required | Description                         |
| ----------------- | -------- | ----------------------------------- |
| `employee_number` | Yes      | Camp participant whose assignment to remove |


**Endpoint sample**

```http
DELETE /api/job-assignments/M00155 HTTP/1.1
Host: localhost:5000
```

```bash
curl -s -X DELETE "http://localhost:5000/api/job-assignments/M00155"
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
| 404  | Error: `{"error": "EMPLOYEE_NOT_FOUND"}` |


---

### `POST /api/job-assignments/reset`

**Explanation**
Deletes job assignments. With an empty or omitted body, deletes **all** assignments. With `{"company_name": "..."}`, deletes only assignments for that company (company must exist).

**Parameters**
None (optional JSON body).

**Endpoint sample**

```http
POST /api/job-assignments/reset HTTP/1.1
Host: localhost:5000
Content-Type: application/json
```

```bash
curl -s -X POST http://localhost:5000/api/job-assignments/reset
curl -s -X POST http://localhost:5000/api/job-assignments/reset \
  -H "Content-Type: application/json" \
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
| 404  | Error: `{"error": "COMPANY_NOT_FOUND"}` when filtering by an unknown `company_name` |

---

## Village data (Spielstadt configuration)

Camp-specific **name**, **currency** labels, optional extra INI sections, and **image paths** live on the server under **`village_data/`** at the repository root (not under `data/`). The server resolves this directory from the project root, not from the process working directory. Deployments edit **`village_data/village.ini`** and files under **`village_data/images/`** (or rely on samples created by **`init-env`** from `data/`—see the [README](../README.md)). Implementations: [`app/routes/village_data.py`](../app/routes/village_data.py).

**INI → JSON:** The file is parsed with Python’s `configparser`. Each **`[section]`** becomes a top-level key in the JSON object; each option becomes a string value inside that object. Optional double quotes around values in the INI are stripped in the API output. Option names are normalized to **lower case** by the parser.

**Caching:** The parsed JSON is cached in memory until **`village_data/village.ini`** changes (file modification time). The **`ETag`** response header on `GET /api/village-data` is an MD5 hex digest of the **raw** INI bytes; send **`If-None-Match`** (quoted, comma-separated, or weak `W/"..."` forms are accepted) to receive **`304 Not Modified`** with an **empty body** when nothing changed.

**Logo and favicon files:** `GET /api/village-data/logo` and `GET /api/village-data/favicon` also return **`ETag`** and honor **`If-None-Match`** the same way. Their **`ETag`** is an MD5 hex digest of the resolved file’s **nanosecond mtime and size** (not the file contents). On **`200`**, responses include **`Cache-Control: public, max-age=3600, must-revalidate`**. On **`304`**, the body is **empty** (no image bytes).

---

### `GET /api/village-data`

**Explanation**
Returns the Spielstadt configuration as JSON for clients (titles, currency strings, image path keys, and any other sections present in `village.ini`).

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
    "increase": ="0",
    "tax" = "3"
  },
  "images": {
    "logo": "images/logo.png",
    "favicon": "images/favicon.png"
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

### `GET /api/village-data/logo`

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

### `GET /api/village-data/favicon`

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
