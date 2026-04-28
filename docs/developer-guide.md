# Developer Guide

## Overview

The **LA-Server** (Kinderspielstadt Los Ämmerles) is a Flask application backed by **MariaDB**. It exposes a JSON REST API for companies, **camp participants** (children and staff; “employees” in paths and JSON), and job assignments during the summer camp. Clients (e.g. job center apps) call these endpoints over HTTP.

For installation, environment variables, production setup (`setup.ps1` / `setup.sh`), and CSV bulk import, see the main [README.md](../README.md).

---

# Client developer (API usage)

## Base URL

By default the server listens on **`http://localhost:5000`**. In deployment, use `http://<HOST>:<PORT>` where `HOST` and `PORT` come from `.env` (see [.env.example](../.env.example)). TLS termination is assumed to happen in a reverse proxy if you serve HTTPS.

## Authentication

**Coming soon.** The API does not yet implement authentication or API keys; treat deployments accordingly (e.g. private network or proxy auth).

## Errors and status codes

- Most validation and not-found cases use response body `{"error": "<CODE>"}` and an HTTP status (often `400`, `404`).
- Database constraint issues may return `**409`** with `{"error": "CONSTRAINT_VIOLATION", "message": "Create failed, because entry is already in database"}` (duplicate / unique violation) or `{"error": "CONSTRAINT_VIOLATION", "message": "Delete failed, because related entries in JobAssignment table"}` (delete blocked by related rows), as implemented in [`app/errors.py`](../app/errors.py).
- Uncaught DB errors: `**500**` with `DATABASE_ERROR`.

Common `error` codes include: `REQUEST_BODY_MUST_BE_A_JSON_OBJECT`, `REQUIRED_JSON_INPUT_MISSING_OR_EMPTY`, `COMPANY_NOT_FOUND`, `EMPLOYEE_NOT_FOUND`, `COMPANY_NOT_ACTIVE`, `EMPLOYEE_NOT_ACTIVE`, `JOB_ALREADY_ASSIGNED`, `NO_JOB_LEFT`, `NO_JOB_ASSIGNED`, `EMPLOYEE_NUMBER_WRONG`, and variants with `_IN_JSON` where applicable.

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

# Backend development (server contributors)

This part isn't done and will come soon.
