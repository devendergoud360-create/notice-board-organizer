# API Reference — Notice Board Organizer

**Base URL:** `http://127.0.0.1:8000` (loopback only — the server never binds to `0.0.0.0`)

**Version:** 1.0.0 · **Content type:** `application/json; charset=utf-8` (unless noted)

This document is the authoritative reference for every HTTP endpoint. All examples use `curl`. The Python stdlib HTTP server is used in production; these examples assume a local test instance.

---

## Table of Contents

1. [Conventions](#1-conventions)
2. [Authentication & Security Model](#2-authentication--security-model)
3. [Error Codes](#3-error-codes)
4. [Endpoint Reference](#4-endpoint-reference)
   - [GET /api/health](#get-apihealth)
   - [GET /api/notices](#get-apinotices)
   - [POST /api/notices](#post-apinotices)
   - [GET /api/notices/{id}](#get-apinoticesid)
   - [PUT /api/notices/{id}](#put-apinoticesid)
   - [DELETE /api/notices/{id}](#delete-apinoticesid)
   - [GET /api/summary](#get-apisummary)
   - [GET /api/warnings](#get-apiwarnings)
   - [POST /api/export](#post-apiexport)
   - [POST /api/import](#post-apiimport)
   - [GET /api/risk/{id}](#get-apiriskid)
   - [GET /api/events](#get-apievents)
5. [Security Behaviours by Endpoint](#5-security-behaviours-by-endpoint)
6. [Full Workflow Example](#6-full-workflow-example)

---

## 1. Conventions

- Dates are strings `YYYY-MM-DD`.
- `id` is a positive integer assigned as `max(existing ids) + 1`.
- All request bodies must be a JSON **object** (not array/string) unless stated.
- Query parameters are URL-encoded; repeatable filters are documented per endpoint.
- Every response includes the headers:

```http
Content-Type: application/json; charset=utf-8
Content-Security-Policy: default-src 'self'; script-src 'self'; object-src 'none'; base-uri 'self'
X-Content-Type-Options: nosniff
Referrer-Policy: no-referrer
```

- Timestamps in events are ISO-8601 UTC (`2026-11-22T10:15:30Z`).

---

## 2. Authentication & Security Model

The API is local-first and layered with several independent controls. A request is accepted only if all applicable checks pass.

### 2.1 Loopback Binding

The HTTP server binds to `127.0.0.1:<port>`. Connections from other hosts are refused at the TCP layer. This is the first and strongest boundary.

### 2.2 Origin / Referer Check

For **all** requests (including reads), if an `Origin` header is present it must be `http://127.0.0.1:<port>` or `http://localhost:<port>`. If absent, `Referer` is checked with the same allow-list. Requests with a foreign origin/referer are rejected with `403`.

```http
Origin: http://127.0.0.1:8000   ✓
Origin: https://evil.example    ✗ 403
```

### 2.3 Double-Submit CSRF

State-changing endpoints (`POST`, `PUT`, `DELETE`) require the CSRF double-submit pattern:

1. `GET /api/health` sets two cookies:
   - `nb_session` — `HttpOnly; SameSite=Strict; Path=/` (opaque random session id).
   - `nb_csrf` — readable by JavaScript (`SameSite=Strict; Path=/`; **not** HttpOnly).
2. The client reads `nb_csrf` and echoes its exact value in the `X-CSRF-Token` request header.
3. The server compares the cookie value to the header value using constant-time comparison. Mismatch or absence → `403`.

> The session cookie is never trusted alone; the CSRF token must be *submitted twice* (cookie + header).

### 2.4 Optional Bearer Token

If the environment variable `NOTICE_API_TOKEN` is set, every non-health request must include:

```http
Authorization: Bearer <token>
```

Comparison uses `hmac.compare_digest`. Missing/wrong token → `401`. If the variable is unset, bearer auth is skipped (demo-friendly), but **CSRF and origin checks still apply**.

### 2.5 Static-File Whitelist

The optional UI serves only files in an explicit whitelist (e.g. `index.html`, `app.js`, `styles.css`) from a fixed directory. Requests containing `..`, absolute paths, URL-encoded traversal (`%2e%2e`), or unknown names are rejected with `404`/`403`. No arbitrary filesystem read is possible.

### 2.6 Body-Size Limit

Request bodies larger than **1 MiB (1,048,576 bytes)** are rejected with `413` before parsing. The `Content-Length` header is checked, and the stream is capped defensively.

### 2.7 Strict CSP & HTML Escaping

Responses carry `Content-Security-Policy: default-src 'self'; script-src 'self'; object-src 'none'; base-uri 'self'`. Any user-controlled string rendered in HTML (UI or docs) is escaped with `html.escape` (`<` → `&lt;`, `>` → `&gt;`, `&` → `&amp;`, `"` → `&quot;`), preventing stored XSS.

---

## 3. Error Codes

| Status | Meaning | Typical Body |
| --- | --- | --- |
| `400` | Malformed request — bad JSON, wrong content type, missing body | `{"error": "bad_request", "message": "Invalid JSON payload."}` |
| `401` | Unauthorized — missing or invalid bearer token | `{"error": "unauthorized", "message": "Bearer token required."}` |
| `403` | Forbidden — CSRF failure, bad origin/referer, traversal attempt | `{"error": "forbidden", "message": "CSRF token mismatch."}` |
| `404` | Not found — unknown notice id or static path | `{"error": "not_found", "message": "No notice with id 999."}` |
| `413` | Payload too large — body exceeds 1 MiB | `{"error": "payload_too_large", "message": "Request body exceeds 1 MiB."}` |
| `422` | Unprocessable entity — validation failure | `{"error": "validation_error", "message": "...", "fields": {"expiry_date": "..."}}` |
| `500` | Internal server error | `{"error": "internal_error", "message": "Unexpected failure."}` |

All error responses use the same JSON envelope:
```json
{ "error": "<code>", "message": "<human-readable detail>", "fields": {} }
```
`fields` is optional and present mainly for `422`.

---

## 4. Endpoint Reference

### GET /api/health

Liveness probe and security handshake. Sets the session + CSRF cookies needed for subsequent mutations.

**Request:** no body. No bearer required. Origin check applies.

**curl:**
```bash
curl -i -c cookies.txt http://127.0.0.1:8000/api/health
```

**Response `200`:**
```json
{
  "status": "ok",
  "version": "1.0.0",
  "time": "2026-11-22T10:15:30Z",
  "csrf_cookie_name": "nb_csrf"
}
```
Set-Cookie headers:
```http
Set-Cookie: nb_session=<random>; HttpOnly; SameSite=Strict; Path=/
Set-Cookie: nb_csrf=<random>; SameSite=Strict; Path=/
```

**Security:** CSP + nosniff headers; cookies issued; origin/referer validated; no bearer needed.

---

### GET /api/notices

List notices with optional filtering and sorting.

**Query parameters:**

| Param | Type | Description |
| --- | --- | --- |
| `category` | string | Exact lowercased category filter |
| `q` | string | Case-insensitive keyword over title/description/author |
| `sort` | string | `id`, `title`, `category`, `posted`, `expiry` (default `expiry`) |
| `limit` | int | Optional page size |
| `offset` | int | Optional page offset |

**curl:**
```bash
curl -b cookies.txt \
  "http://127.0.0.1:8000/api/notices?category=events&q=lecture&sort=expiry"
```

**Response `200`:**
```json
{
  "count": 2,
  "notices": [
    {
      "id": 21,
      "title": "Guest Lecture: AI",
      "category": "events",
      "date_posted": "2026-10-05",
      "expiry_date": "2026-11-28",
      "status": "Upcoming",
      "author": "Faculty Club",
      "description": "AI guest lecture details."
    },
    {
      "id": 25,
      "title": "Alumni Networking Night",
      "category": "events",
      "date_posted": "2026-09-20",
      "expiry_date": "2026-12-01",
      "status": "Upcoming",
      "author": "Admin",
      "description": "Annual alumni meet."
    }
  ]
}
```

**Security:** origin/referer check; CSP; bearer token if configured; HTML escaping applies only if rendered in UI.

---

### POST /api/notices

Create a notice.

**Headers:** `Content-Type: application/json`, `X-CSRF-Token: <nb_csrf value>`, cookies, optional bearer.

**Request body:**
```json
{
  "title": "Midterm Examination Schedule",
  "category": "academics",
  "date_posted": "2026-10-01",
  "expiry_date": "2026-11-30",
  "author": "Registrar",
  "description": "Midterm exam timetable."
}
```

**curl:**
```bash
CSRF=$(grep nb_csrf cookies.txt | awk '{print $7}')
curl -b cookies.txt -X POST http://127.0.0.1:8000/api/notices \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: $CSRF" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"title":"Midterm Examination Schedule","category":"academics","date_posted":"2026-10-01","expiry_date":"2026-11-30","author":"Registrar","description":"Midterm exam timetable."}'
```

**Response `201`:**
```json
{
  "notice": {
    "id": 41,
    "title": "Midterm Examination Schedule",
    "category": "academics",
    "date_posted": "2026-10-01",
    "expiry_date": "2026-11-30",
    "status": "Upcoming",
    "author": "Registrar",
    "description": "Midterm exam timetable."
  },
  "event": {"event": "notice.created", "id": 41}
}
```

**Errors:** `400` bad JSON; `401` no bearer; `403` CSRF/origin; `413` large body; `422` validation (empty title, unknown category, bad date, expiry < posted); `500` internal.

**Security:** CSRF double-submit + origin + bearer + size limit; emits `notice.created` event to JSON log.

---

### GET /api/notices/{id}

Retrieve one notice.

**curl:**
```bash
curl -b cookies.txt http://127.0.0.1:8000/api/notices/41
```

**Response `200`:**
```json
{
  "id": 41,
  "title": "Midterm Examination Schedule",
  "category": "academics",
  "date_posted": "2026-10-01",
  "expiry_date": "2026-11-30",
  "status": "Upcoming",
  "author": "Registrar",
  "description": "Midterm exam timetable.",
  "days_remaining": 8
}
```

**Errors:** `404` unknown id; `401`/`403` auth.

---

### PUT /api/notices/{id}

Update a notice. Omitted keys keep current values. All supplied values are revalidated (including date ordering).

**Request body (partial):**
```json
{ "title": "Revised Midterm Schedule", "expiry_date": "2026-12-05" }
```

**curl:**
```bash
curl -b cookies.txt -X PUT http://127.0.0.1:8000/api/notices/41 \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: $CSRF" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"title":"Revised Midterm Schedule","expiry_date":"2026-12-05"}'
```

**Response `200`:**
```json
{
  "notice": {
    "id": 41,
    "title": "Revised Midterm Schedule",
    "category": "academics",
    "date_posted": "2026-10-01",
    "expiry_date": "2026-12-05",
    "status": "Upcoming",
    "author": "Registrar",
    "description": "Midterm exam timetable."
  },
  "event": {"event": "notice.updated", "id": 41}
}
```

**Errors:** `404`, `400`, `401`, `403`, `413`, `422`, `500`.

**Security:** full mutation protection; emits `notice.updated`.

---

### DELETE /api/notices/{id}

Delete a notice.

**curl:**
```bash
curl -b cookies.txt -X DELETE http://127.0.0.1:8000/api/notices/41 \
  -H "X-CSRF-Token: $CSRF" \
  -H "Authorization: Bearer $TOKEN"
```

**Response `200`:**
```json
{ "deleted": true, "id": 41, "event": {"event": "notice.deleted", "id": 41} }
```

**Errors:** `404` if no such id (with `{"deleted": false, ...}`); `401`/`403` auth.

---

### GET /api/summary

Executive summary over all notices.

**curl:**
```bash
curl -b cookies.txt http://127.0.0.1:8000/api/summary
```

**Response `200`:**
```json
{
  "total": 40,
  "active": 6,
  "upcoming": 21,
  "expired": 13,
  "overdue": 11,
  "expiring_soon": 7,
  "avg_days_remaining": 9.4,
  "category_counts": {"events": 9, "academics": 8, "general": 7}
}
```

---

### GET /api/warnings

Threshold warnings: overdue (`days < 0`) or expiring within 3 days.

**curl:**
```bash
curl -b cookies.txt http://127.0.0.1:8000/api/warnings
```

**Response `200`:**
```json
{
  "count": 2,
  "warnings": [
    {"id": 7, "title": "Library Maintenance", "message": "OVERDUE by 4 day(s)"},
    {"id": 19, "title": "Thesis Proposal Deadline", "message": "Expires in 2 day(s)"}
  ]
}
```

---

### POST /api/export

Export all notices to Markdown, plain text, or CSV. The output path must be inside the `data/` directory (whitelist).

**Request body:**
```json
{ "format": "md", "path": "data/notice_report.md" }
```
`format` is one of `md`, `txt`, `csv`. If `path` is omitted a default under `data/` is used. Paths with `..`, absolute paths, or outside `data/` → `403`.

**curl:**
```bash
curl -b cookies.txt -X POST http://127.0.0.1:8000/api/export \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: $CSRF" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"format":"md","path":"data/notice_report.md"}'
```

**Response `200`:**
```json
{ "exported": true, "format": "md", "path": "data/notice_report.md", "bytes": 4442 }
```

**Errors:** `403` path traversal / disallowed format; `400`, `401`, `413`, `500`.

---

### POST /api/import

Bulk-import notices from a CSV file inside `data/`. Each row is validated independently; invalid rows are skipped and reported.

**Request body:**
```json
{ "path": "data/sample_notices.csv", "mode": "append" }
```
`mode` is `append` (default) or `replace`.

**curl:**
```bash
curl -b cookies.txt -X POST http://127.0.0.1:8000/api/import \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: $CSRF" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"path":"data/sample_notices.csv","mode":"append"}'
```

**Response `200`:**
```json
{
  "added": 38,
  "skipped": 2,
  "errors": [
    {"row": 5, "reason": "Unknown category 'unknown'."},
    {"row": 17, "reason": "Expiry date cannot be earlier than the date posted."}
  ],
  "event": {"event": "notices.imported", "added": 38, "skipped": 2}
}
```

**Errors:** `400`, `401`, `403` (path), `413`, `500`.

---

### GET /api/risk/{id}

Compute the Notice Risk & Priority Score for one notice (see SRS §9 for the exact formula).

**curl:**
```bash
curl -b cookies.txt http://127.0.0.1:8000/api/risk/10
```

**Response `200`:**
```json
{
  "id": 10,
  "score": 0.744900,
  "components": {
    "urgency": 0.9,
    "staleness": 1.0,
    "category_weight": 0.137,
    "history_factor": 0.75
  },
  "explanation": "High urgency (expires in 3 days); stale posting; moderate deadline-category weight; 2 of 4 prior deadline notices were overdue."
}
```

- `score` is always in `[0,1]`, rounded half-up to 6 decimals.
- `components` exposes every term for explainability.
- **Errors:** `404` unknown id; `401`/`403` auth.

---

### GET /api/events

Return the most recent structured JSON events from `data/events.jsonl`.

**Query:** `limit` (default 50, max 500).

**curl:**
```bash
curl -b cookies.txt "http://127.0.0.1:8000/api/events?limit=10"
```

**Response `200`:**
```json
{
  "count": 3,
  "events": [
    {"event": "notice.created", "timestamp": "2026-11-22T10:15:30Z", "actor": "cli", "data": {"id": 41}},
    {"event": "notice.updated", "timestamp": "2026-11-22T10:16:02Z", "actor": "api", "data": {"id": 41}},
    {"event": "notice.deleted", "timestamp": "2026-11-22T10:16:45Z", "actor": "api", "data": {"id": 41}}
  ]
}
```

**Security:** bearer token recommended; origin check; if token configured it is enforced.

---

## 5. Security Behaviours by Endpoint

| Endpoint | Origin check | CSRF | Bearer | Size limit | Special |
| --- | --- | --- | --- | --- | --- |
| `GET /api/health` | ✓ | — | — | — | Issues cookies |
| `GET /api/notices` | ✓ | — | ✓ if set | — | CSP |
| `POST /api/notices` | ✓ | ✓ | ✓ if set | ✓ | Event emit |
| `GET /api/notices/{id}` | ✓ | — | ✓ if set | — | — |
| `PUT /api/notices/{id}` | ✓ | ✓ | ✓ if set | ✓ | Event emit |
| `DELETE /api/notices/{id}` | ✓ | ✓ | ✓ if set | — | Event emit |
| `GET /api/summary` | ✓ | — | ✓ if set | — | — |
| `GET /api/warnings` | ✓ | — | ✓ if set | — | — |
| `POST /api/export` | ✓ | ✓ | ✓ if set | ✓ | Path whitelist |
| `POST /api/import` | ✓ | ✓ | ✓ if set | ✓ | Path whitelist |
| `GET /api/risk/{id}` | ✓ | — | ✓ if set | — | Explainable score |
| `GET /api/events` | ✓ | — | ✓ recommended | — | Auditable log |

All endpoints: loopback bind, strict CSP, `nosniff`, `Referrer-Policy: no-referrer`, HTML escaping of rendered user strings.

---

## 6. Full Workflow Example

```bash
# 0. Start server (loopback)
 python main.py --serve 8000

# 1. Handshake: get cookies + CSRF
 curl -i -c cookies.txt http://127.0.0.1:8000/api/health
 CSRF=$(grep nb_csrf cookies.txt | awk '{print $7}')
 TOKEN="my-secret"

# 2. Create a notice
 curl -b cookies.txt -X POST http://127.0.0.1:8000/api/notices \
   -H "Content-Type: application/json" -H "X-CSRF-Token: $CSRF" \
   -H "Authorization: Bearer $TOKEN" \
   -d '{"title":"Safety Drill","category":"administration","date_posted":"2026-11-01","expiry_date":"2026-11-24"}'

# 3. Inspect summary, warnings and risk
 curl -b cookies.txt http://127.0.0.1:8000/api/summary
 curl -b cookies.txt http://127.0.0.1:8000/api/warnings
 curl -b cookies.txt http://127.0.0.1:8000/api/risk/41

# 4. Export and audit
 curl -b cookies.txt -X POST http://127.0.0.1:8000/api/export \
   -H "Content-Type: application/json" -H "X-CSRF-Token: $CSRF" \
   -H "Authorization: Bearer $TOKEN" -d '{"format":"md"}'
 curl -b cookies.txt "http://127.0.0.1:8000/api/events?limit=10"
```

---

*End of API Reference — Notice Board Organizer v1.0.0.*
