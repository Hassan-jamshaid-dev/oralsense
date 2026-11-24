# OralSense production security checklist

**Remediation date:** 11 October 2026 (CSRF, registration default, host/proxy; earlier follow-up and first-pass tables are preserved below)  
**Use:** Pre-deploy review for the current email + password + session-cookie system.  
**Status values:** `VERIFIED` · `FAILED` · `NOT VERIFIED` · `NOT APPLICABLE` · `PARTIALLY VERIFIED` (used only when the control exists but is incomplete).

`VERIFIED` in this document means automated tests and/or inspected application config. It does **not** mean the owner’s production host was probed.

This is not a penetration test and does not claim legal or regulatory compliance.

Do not paste passwords, `DATABASE_URL`, session cookies, tokens, or API keys into a filled copy of this list. Record file + secret type only.

**Current verdict:** **CONDITIONALLY READY** for a closed, HTTPS-terminated demo of the current auth/workspace/dashboard routes after the owner items in §9. **FAILED** as “ready to store real participant identifiers on the public internet.”

---

## Follow-up statuses (independent re-check)

### 1. Secrets and repository hygiene

| Item | Status | Evidence / note |
|---|---|---|
| `backend/.env` gitignored | VERIFIED | Root `.gitignore` matches `.env`. `git check-ignore` pointed at `.gitignore:2:.env`. |
| `backend/.env` not tracked | VERIFIED | `git ls-files` returned no `.env` paths. File exists locally. Type: local environment file. Value not recorded. |
| Only `.env.example` committed, placeholders only | VERIFIED | `CHANGE_ME` in `DATABASE_URL`; comments only. |
| No `VITE_` / `PUBLIC_` secrets | VERIFIED | Frontend grep found none. No `localStorage` / `sessionStorage` tokens. |
| `OPENAI_API_KEY` not in frontend or this batch | NOT APPLICABLE | OpenAI QC is not integrated yet. |
| Secrets never logged | VERIFIED (code review) | Handlers log exception type / generic messages. Production log pipeline still NOT VERIFIED. |
| `SECRET_KEY` / JWT / OAuth secrets | NOT APPLICABLE | This architecture does not use them. |

### 2. Transport and cookies

| Item | Status | Evidence / note |
|---|---|---|
| HTTPS terminated in front of the app | NOT VERIFIED | This environment is local HTTP. |
| HTTP→HTTPS redirect | NOT VERIFIED | Not implemented in FastAPI. Do this at the reverse proxy. |
| Session cookie `HttpOnly` | VERIFIED | Set and logout-clear tested. |
| Session cookie `SameSite=Lax` | VERIFIED | Set and logout-clear tested. Combined with CSRF header. |
| Session cookie `Secure` in production | VERIFIED | Forced when `ENVIRONMENT=production`, even if `COOKIE_SECURE=false`. Register and logout `Set-Cookie` include `Secure`. |
| `Secure` on local HTTP development | NOT APPLICABLE | Left false so the Vite/HTTP workflow works. |
| HSTS | VERIFIED (code + pytest) | Set only when `ENVIRONMENT=production`. Absent on the live development process (expected). |
| Cookie path `/` | VERIFIED | Set and cleared with `path=/`. |
| `__Host-` cookie prefix | FAILED | Still `oralsense_session`. Backlog; not a closed-demo ship-blocker. |
| Cookie value stored hashed | VERIFIED | SHA-256 hex in `user_sessions.token_hash`; raw cookie not in the hash. |
| Logout deletes DB row and cookie | VERIFIED | Pytest + replay `401`. User B logout does not revoke user A. |

### 3. Authentication

| Item | Status | Evidence / note |
|---|---|---|
| Passwords hashed (scrypt) | VERIFIED | `scrypt$n$r$p$salt$hash`. |
| Constant-time compare | VERIFIED | `hmac.compare_digest`. |
| Unknown-email dummy hash | VERIFIED | Same error body as wrong password (exact JSON equality test). |
| Session rotation on login | VERIFIED | Presented own-session revoked; unknown presented cookie not adopted. |
| Session expiry enforced | VERIFIED | Expired row deleted; `401 session_expired`. |
| Tampered token rejected | VERIFIED | `401 not_authenticated`. |
| Unauthenticated API rejected | VERIFIED | Protected routes return `401`. Live `/api/auth/me` → `401 not_authenticated`. |
| Registration kill switch | VERIFIED | `ALLOW_REGISTRATION=false` → `403 registration_disabled`. |
| Registration default-off in production | VERIFIED | Unset `ALLOW_REGISTRATION` is off when `ENVIRONMENT=production`, on in development. Explicit `true` / `false` override. Pytest: unit + register endpoint. |
| Password reset | FAILED | Does not exist. Owner blocker for public accounts. |
| Email verification | FAILED | Does not exist. |
| MFA | FAILED | Does not exist. |
| Password change | FAILED | Does not exist. Required before long-lived research identities. |
| Account lockout beyond sliding window | FAILED | 15-minute in-memory window only. Pre-registration failures can `429` a later first login (L7). |

### 4. Authorization

| Item | Status | Evidence / note |
|---|---|---|
| Server-side session required | VERIFIED | `CurrentUser` dependency. |
| Tenant scoped to current membership | VERIFIED | `/workspaces/current` and `/dashboard/summary` use `user_id` only. |
| Two users cannot access each other's workspaces | VERIFIED | `/me`, dashboard, workspace POST/PATCH, logout. |
| Client cannot set `access_role` / `workspace_id` | VERIFIED | `extra="forbid"` → `422`. |
| Owner-only workspace name/description | VERIFIED | SQL-inserted member gets `403 forbidden`. |
| Frontend role UI is not the control | VERIFIED | Edit form hides fields; API still enforces. |
| IDOR on participant/assessment IDs | NOT APPLICABLE | Routes do not exist (`404` live and pytest). Re-check when they do. Do not record as passed. |

### 5. CSRF, CORS, headers

| Item | Status | Evidence / note |
|---|---|---|
| CSRF defense on state-changing requests | VERIFIED | Trusted `Origin` (`CORS_ORIGINS` or same-host) on POST/PATCH/PUT/DELETE. Login/register: Origin required. After session: per-session token in `X-OralSense-CSRF` (from `/auth/me` or login/register). Missing / untrusted / `null` / malformed Origin rejected. Origin-less mutation allowed only with a matching session token. Static `1` is not accepted. Referer is not a substitute. Pytest covers every current mutation. |
| Frontend sends the CSRF header | VERIFIED | `frontend/src/lib/api.ts` sends the token from login/register/`/me` on mutations. Typecheck + production build passed. Origin is browser-set. |
| CORS explicit origins + credentials | VERIFIED | Settings list; live `Origin: http://localhost:5173` reflected with credentials. |
| Wildcard CORS rejected | VERIFIED | Startup `RuntimeError`. |
| Disallowed origin | VERIFIED | `https://evil.example` has no `Access-Control-Allow-Origin`. Preflight not allowed. Server now **rejects** untrusted Origin on mutations (`403 csrf_rejected`) even if a CSRF header is present. |
| `Access-Control-Allow-Headers` includes CSRF | VERIFIED | Allowed preflight lists `X-OralSense-CSRF`. |
| Security headers on API | VERIFIED | Present on health, `/me`, 401/404/405, and CSRF `403` (middleware wraps the 403 `send` path). HSTS only when `ENVIRONMENT=production`. |
| SPA document CSP | FAILED | `frontend/index.html` has none. Do not apply the API CSP to the SPA. |
| Clickjacking (API) | VERIFIED | `X-Frame-Options: DENY` + CSP `frame-ancestors 'none'` on responses that go through the header wrapper. |
| OpenAPI disabled in production | VERIFIED | pytest `create_app()` with `ENVIRONMENT=production` → `404`. Live development process still serves `/docs` (`200`). |

### 6. Rate limits and availability

| Item | Status | Evidence / note |
|---|---|---|
| Failed-login limit per email | VERIFIED | 10 / 15 minutes → `429`. |
| Failed-login limit per IP | VERIFIED (code) | 20 / 15 minutes. TestClient shares one address. |
| Register attempt limit per IP | VERIFIED (code) | 10 / 15 minutes. |
| Limiter shared across processes | FAILED | In-memory only. |
| `X-Forwarded-For` not trusted | VERIFIED | Ignored unless `TRUST_FORWARDING=true` and the peer is in `TRUSTED_PROXY_IPS`. Default off. Pytest: default ignore; trusted peer rewrite; untrusted peer ignore. |
| Database failure does not fail open | VERIFIED | `503 database_unavailable`, not a signed-in user. |

### 7. Errors and logging

| Item | Status | Evidence / note |
|---|---|---|
| User-facing 500 has no traceback / internals | VERIFIED | `internal_error` generic message; leak marker absent. |
| User-facing 503 does not name `DATABASE_URL` | VERIFIED | Generic “not configured” / “unavailable”. |
| Validation errors are field-safe | VERIFIED | 422 `validation_error`. |
| Stack traces not sent to the client | VERIFIED | TestClient `raise_server_exceptions=False` path. Live 401/403 bodies had no traceback. |
| Production log redaction of cookies / tokens | NOT VERIFIED | Needs a log-pipeline review at deploy time. |

### 8. Dependencies and build

| Item | Status | Evidence / note |
|---|---|---|
| `pip-audit -r backend/requirements.txt` | VERIFIED | No known vulnerabilities found (local run, exit 0). |
| `pip-audit` installed set in `backend/.venv` | VERIFIED | Scanned. No known vulnerabilities found (exit 0). |
| `npm audit --json` in `frontend/` | VERIFIED | 0 vulnerabilities; report metadata listed 113 dependencies. |
| Third-party source upload scanners | NOT APPLICABLE | Not used. |
| Frontend typecheck | VERIFIED | `npm run typecheck` passed (remediation pass). |
| Frontend production build | VERIFIED | `npm run build` passed (remediation pass). |
| Backend pytest (existing + remediations) | VERIFIED | **126 passed** against `oralsense_test`. |

### 9. Deployment configuration (owner)

| Item | Status | Evidence / note |
|---|---|---|
| `ENVIRONMENT=production` | NOT VERIFIED | Must be set on the host. This environment is local HTTP / development. |
| `CORS_ORIGINS` = real frontend origin only | NOT VERIFIED | Defaults / local Vite ports. App rejects `*`. Owner must pin the demo origin. |
| `ALLOW_REGISTRATION` matches the demo plan | NOT VERIFIED | App default is now off in production. Owner must still set the env on the host (or leave it unset). |
| `SESSION_TTL_HOURS` reviewed | NOT VERIFIED | Default 12. No idle timeout. |
| `COOKIE_SECURE=true` | NOT VERIFIED | Forced anyway when environment is production. |
| PostgreSQL not reachable from the internet | NOT VERIFIED | Infra. App code does not provide network isolation. |
| Managed backups / encryption at rest | NOT VERIFIED | Infra. App code does not provide these. |
| TLS termination / HTTP→HTTPS redirect | NOT VERIFIED | Infra / reverse proxy. App code does not terminate TLS. |
| Trusted proxy / host allow-list | VERIFIED (code + pytest) / NOT VERIFIED (host values) | `ALLOWED_HOSTS` and optional `TRUST_FORWARDING` + `TRUSTED_PROXY_IPS` are implemented. Production values on a real host were not set or probed. |
| Multi-worker rate limiting | FAILED | In-memory only. Not implemented. |
| WAF / bot protection | NOT VERIFIED | Out of app scope. |

### 10. What “done” is not

| Item | Status |
|---|---|
| Clinically validated software | NOT APPLICABLE — prototype |
| Medical device / diagnostic claim | NOT APPLICABLE — must not be claimed |
| Pentest | NOT VERIFIED |
| SOC 2 / HIPAA / ISO 27001 | NOT VERIFIED / NOT APPLICABLE |
| Ready to store real participant identifiers on the public internet | FAILED — see verdict |

---

## Current verdict (after remediations)

**CONDITIONALLY READY** for the **defined scope** (current email + password + session cookie, current routes only) when the owner completes the closed-demo settings below. **FAILED / not ready** for public internet accounts or real participant identifiers.

This is not production readiness, a pentest, or a compliance claim.

### Exact closed-demo settings (owner)

App code does **not** provide TLS, HTTP→HTTPS redirect, PostgreSQL network isolation, backups, or encryption at rest.

```text
ENVIRONMENT=production
CORS_ORIGINS=https://<the-page-origin-the-browser-sends>
ALLOWED_HOSTS=<api-hostname>
ALLOW_REGISTRATION=false
# or leave ALLOW_REGISTRATION unset (same effect in production)
COOKIE_SECURE=true
SESSION_TTL_HOURS=12
TRUST_FORWARDING=false
```

If a reverse proxy you control terminates TLS on the same machine:

```text
TRUST_FORWARDING=true
TRUSTED_PROXY_IPS=127.0.0.1
```

Also run `alembic upgrade head` so `user_sessions.csrf_token` exists. Seed accounts, then keep registration off. Accept in-memory rate limits, no MFA, no password change/reset, and no email verification.

Re-run this list when participant, study, or assessment routes are added. Those will re-open IDOR as the primary authorization risk.

---

## First-pass checklist (historical, 11 October 2026)

The tables below are the original pass. Do not treat them as this follow-up’s statuses.

**Date:** 11 October 2026  
**Status values (original):** `verified` · `failed` · `n/a` · `not verified`.

This is not a penetration test and does not claim legal or regulatory compliance.

Do not paste passwords, `DATABASE_URL`, session cookies, tokens, or API keys into a filled copy of this list. Record file + secret type only.

---

## 1. Secrets and repository hygiene

| Item | Status | Evidence / note |
|---|---|---|
| `backend/.env` gitignored | verified | Root `.gitignore` matches `.env` in any directory. |
| `backend/.env` not tracked | verified | `git ls-files` returned no `.env` paths. |
| Only `.env.example` committed, placeholders only | verified | `CHANGE_ME` in `DATABASE_URL`; no live credentials. |
| No `VITE_` / `PUBLIC_` secrets | verified | Frontend has no secret env vars. |
| `OPENAI_API_KEY` not in frontend or this batch | n/a | OpenAI QC is not integrated yet. |
| Secrets never logged | verified (code review) | Error handlers log exception type / generic messages, not env values. Confirm log aggregation before production. |
| `SECRET_KEY` / JWT / OAuth secrets | n/a | This architecture does not use them. |

## 2. Transport and cookies

| Item | Status | Evidence / note |
|---|---|---|
| HTTPS terminated in front of the app | not verified | This environment is local HTTP. Owner/infra must terminate TLS. |
| HTTP→HTTPS redirect | not verified | Not implemented in FastAPI. Do this at the reverse proxy. |
| Session cookie `HttpOnly` | verified | Set and tested. |
| Session cookie `SameSite=Lax` | verified | Set and tested. Combined with CSRF header. |
| Session cookie `Secure` in production | verified (code + test) | Forced when `ENVIRONMENT=production`, even if `COOKIE_SECURE=false`. |
| `Secure` on local HTTP development | n/a | Left false so the Vite/HTTP workflow works. |
| HSTS | verified (code + test) | Set only when `ENVIRONMENT=production`. |
| Cookie path `/` | verified | Set and cleared with `path=/`. |
| `__Host-` cookie prefix | failed | Still `oralsense_session`. Acceptable backlog; not a ship-blocker for a closed demo. |
| Cookie value stored hashed | verified | SHA-256 hex in `user_sessions.token_hash`. |
| Logout deletes DB row and cookie | verified | Tests + live `204` then `401 not_authenticated`. |

## 3. Authentication

| Item | Status | Evidence / note |
|---|---|---|
| Passwords hashed (scrypt) | verified | `scrypt$n$r$p$salt$hash`. Argon2id not used; see audit L1. |
| Constant-time compare | verified | `hmac.compare_digest`. |
| Unknown-email dummy hash | verified | Same error as wrong password. |
| Session rotation on login | verified | Presented own-session revoked; new token issued. |
| Session expiry enforced | verified | Expired row deleted; `401 session_expired`. |
| Tampered token rejected | verified | `401 not_authenticated`. |
| Unauthenticated API rejected | verified | Protected routes return `401`. |
| Registration kill switch | verified | `ALLOW_REGISTRATION=false` → `403 registration_disabled`. |
| Registration default-off in production | failed | Default remains `true`. Production logs a warning. Owner must set `false` on a public host. |
| Password reset | failed | Does not exist. Owner blocker for public accounts. |
| Email verification | failed | Does not exist. |
| MFA | failed | Does not exist. |
| Password change | failed | Does not exist. |
| Account lockout beyond sliding window | failed | 15-minute in-memory window only. |

## 4. Authorization

| Item | Status | Evidence / note |
|---|---|---|
| Server-side session required | verified | `CurrentUser` dependency. |
| Tenant scoped to current membership | verified | `/workspaces/current` and `/dashboard/summary`. |
| Two users cannot access each other's workspaces | verified | Security test. |
| Client cannot set `access_role` / `workspace_id` | verified | `extra="forbid"` → `422`. |
| Owner-only workspace name/description | verified | Members get `403 forbidden`. |
| Frontend role UI is not the control | verified | Edit form hides fields; API still enforces. |
| IDOR on future participant/assessment IDs | n/a | Those routes do not exist yet. Re-check when they do. |

## 5. CSRF, CORS, headers

| Item | Status | Evidence / note |
|---|---|---|
| CSRF defense on state-changing requests | verified | Required `X-OralSense-CSRF: 1`. Live `403 csrf_rejected` without it. |
| Frontend sends the CSRF header | verified | `frontend/src/lib/api.ts`. Live register/workspace/logout with the header succeeded. |
| CORS explicit origins + credentials | verified | Settings list; not `*`. |
| Wildcard CORS rejected | verified | Startup `RuntimeError`. |
| `Access-Control-Allow-Headers` includes CSRF | verified | `CORS_ALLOW_HEADERS`. |
| Security headers on API | verified | nosniff, DENY, no-store, API CSP, etc. |
| SPA document CSP | failed | `frontend/index.html` has none. Do not apply the API CSP to the SPA. |
| Clickjacking (API) | verified | `X-Frame-Options: DENY` + CSP `frame-ancestors 'none'`. |
| OpenAPI disabled in production | verified | Tested via `create_app()` with `ENVIRONMENT=production`. |

## 6. Rate limits and availability

| Item | Status | Evidence / note |
|---|---|---|
| Failed-login limit per email | verified | 10 / 15 minutes → `429`. |
| Failed-login limit per IP | verified (code) | 20 / 15 minutes. TestClient shares one address. |
| Register attempt limit per IP | verified (code) | 10 / 15 minutes. |
| Limiter shared across processes | failed | In-memory only. Documented remaining risk. |
| `X-Forwarded-For` not trusted | verified | Client address is `request.client.host` only. |
| Database failure does not fail open | verified | `503 database_unavailable`, not a signed-in user. |

## 7. Errors and logging

| Item | Status | Evidence / note |
|---|---|---|
| User-facing 500 has no traceback / internals | verified | `internal_error` generic message. |
| User-facing 503 does not name `DATABASE_URL` | verified | Generic “not configured” / “unavailable”. |
| Validation errors are field-safe | verified | 422 `validation_error`. |
| Stack traces not sent to the client | verified | TestClient `raise_server_exceptions=False` path. |
| Production log redaction of cookies / tokens | not verified | Needs a log-pipeline review at deploy time. |

## 8. Dependencies and build

| Item | Status | Evidence / note |
|---|---|---|
| `pip-audit -r backend/requirements.txt` | verified | No known vulnerabilities found (local run). |
| `npm audit` in `frontend/` | verified | 0 vulnerabilities. |
| Third-party source upload scanners | n/a | Not used. |
| Frontend typecheck | verified | `npm run typecheck` passed. |
| Frontend production build | verified | `npm run build` passed. |
| Backend pytest (existing + security) | verified | 65 passed against `oralsense_test`. |

## 9. Deployment configuration (owner)

| Item | Status | Evidence / note |
|---|---|---|
| `ENVIRONMENT=production` | not verified | Must be set on the host. |
| `CORS_ORIGINS` = real frontend origin only | not verified | Defaults are localhost Vite ports. |
| `ALLOW_REGISTRATION=false` unless intended | not verified | Default `true`. |
| `SESSION_TTL_HOURS` reviewed | not verified | Default 12. |
| `COOKIE_SECURE=true` | not verified | Forced anyway when environment is production. |
| PostgreSQL not reachable from the internet | not verified | Infra. |
| Managed backups / encryption at rest | not verified | Infra. |
| Trusted proxy / host allow-list | failed | Not implemented. |
| Multi-worker rate limiting | failed | Not implemented. |
| WAF / bot protection | not verified | Out of app scope. |

## 10. What “done” is not

| Item | Status |
|---|---|
| Clinically validated software | n/a — prototype |
| Medical device / diagnostic claim | n/a — must not be claimed |
| Pentest | not verified |
| SOC 2 / HIPAA / ISO 27001 | not verified / n/a |
| Ready to store real participant identifiers on the public internet | failed — see verdict |

---

## First-pass verdict (historical)

**Not ready for production.**

Conditionally acceptable for a **closed demo** when:

- TLS is terminated in front of the app
- `ENVIRONMENT=production`
- `CORS_ORIGINS` is a single real origin
- `ALLOW_REGISTRATION` matches the demo plan (usually `false` after seeding accounts)
- Operators accept in-memory rate limits, no MFA, no password reset, and no email verification

Re-run this list when participant, study, or assessment routes are added. Those will re-open IDOR as the primary authorization risk.
