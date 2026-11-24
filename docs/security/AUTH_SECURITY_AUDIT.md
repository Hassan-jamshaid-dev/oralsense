# OralSense authentication and authorization security audit

**Latest verdict (remediation pass, 11 October 2026):** **CONDITIONALLY READY** for the defined scope only — a closed, HTTPS-terminated demo of the current email + password + session-cookie surface (`/api/health`, `/api/auth/*`, `/api/workspaces*`, `/api/dashboard/summary`) after the owner steps in [§11.5](#115-owner-steps-before-a-closed-demo). **Not ready** for the public internet, open signup, or real participant identifiers. This is not a pentest, compliance certification, or production-readiness claim.

The first-pass audit is preserved below as historical record. Treat its conclusions as hypotheses that this follow-up re-checked. The follow-up starts at [§10](#10-follow-up-audit-11-october-2026).

---

**First-pass date:** 11 October 2026  
**Scope:** Existing email + password accounts and server-side session cookies. This is not a penetration test, compliance certification, or claim that OralSense is ready to hold real participant data on the public internet.  
**Architecture kept:** Email + password, `hashlib.scrypt` password hashes, `secrets.token_urlsafe(32)` session tokens stored as SHA-256, HttpOnly cookie `oralsense_session`. OAuth / Auth0 / JWT were not introduced.  
**First-pass verdict:** **Not ready for production.** After the remediations in this pass the prototype is **conditionally acceptable for a closed, HTTPS-terminated demo** if the owner completes the blockers below.

No secret values (passwords, `DATABASE_URL`, session tokens, cookies, or API keys) are recorded in this document.

---

## 1. System map (verified in code)

```text
Browser (untrusted)
  → Vite /api proxy in development, or a reverse proxy in production
    → FastAPI (Route → Service → SQLAlchemy → PostgreSQL)
```

**Identity store:** `users` (email unique and stored lowercase, `password_hash`, optional `display_name`).  
**Tenant boundary:** `workspaces` + `workspace_memberships` (`access_role` in `{owner, member}`, optional `research_role`). One current workspace per user: the earliest membership.  
**Sessions:** `user_sessions.token_hash` is SHA-256 hex of the cookie value. The raw token is never stored.  
**Frontend:** React + Vite. `fetch(..., { credentials: "include" })`. `AuthProvider` boots from `GET /api/auth/me`. No secrets in `VITE_` variables.

### Sign-in → authenticated API → sign-out

1. `POST /api/auth/register` or `POST /api/auth/login` with JSON email/password from a trusted `Origin` (`CORS_ORIGINS` or same-host). After a session exists, mutations also send `X-OralSense-CSRF: <per-session token>` from `/auth/me` or the login/register body.
2. Backend verifies (or creates) the user. Login equalizes unknown-email cost with a dummy scrypt run and uses `hmac.compare_digest`.
3. A new session row is inserted. Login revokes the presented session if it belongs to that user (rotation). The response sets `oralsense_session` (`HttpOnly`, `SameSite=Lax`, `Secure` when `ENVIRONMENT=production` or `COOKIE_SECURE=true`, `Path=/`).
4. Subsequent `GET /api/auth/me`, workspace, and dashboard calls read the cookie, hash it, and load the user. Authorization uses the server-side membership, not client-supplied roles or workspace IDs.
5. `POST /api/auth/logout` deletes the matching `user_sessions` row and clears the cookie with the same attributes. Replaying the old cookie returns `401 not_authenticated`.

### Trust boundaries

| Boundary | What is trusted | What is not |
|---|---|---|
| Browser / SPA | Nothing privileged | Roles, workspace IDs, hidden UI, local state |
| HTTP headers | Session cookie after hashing; per-session CSRF token compared with `hmac.compare_digest`; `Origin` against `CORS_ORIGINS` or same-host | `X-Forwarded-For` unless `TRUST_FORWARDING` and a listed proxy; any `access_role` in JSON |
| FastAPI process | Env from `backend/.env`, in-memory rate-limit maps | Those maps do not survive restart and are not shared across processes |
| PostgreSQL | Rows and constraints | A DB leak of `password_hash` / `token_hash` is still a high-impact event |
| CORS origin list | Explicit origins with `allow_credentials=True` | `*` is rejected at startup |

---

## 2. Threat model (from this implementation)

| Threat | Relevant controls | Residual risk |
|---|---|---|
| Credential stuffing / password guessing | scrypt; dummy hash on unknown email; per-email and per-IP sliding windows | Limiter is in-process only |
| Session theft (XSS) | HttpOnly cookie; API CSP `default-src 'none'` | SPA itself has no document CSP |
| Session theft (network) | `Secure` forced in production | HTTPS must be terminated in front of the app (owner / infra) |
| CSRF | `SameSite=Lax` plus trusted Origin and a per-session `X-OralSense-CSRF` token | CORS must stay an explicit allow-list; login/register rely on Origin |
| Session fixation | New token on register/login; presented own-session revoked on login | Other devices keep their sessions |
| IDOR / BOLA | No resource IDs in routes; `/workspaces/current` and dashboard use `user_id` | Future participant/assessment routes must repeat this pattern |
| Privilege escalation | `extra="forbid"`; `access_role` always `"owner"` on create; owner check on workspace edits | Research role is a label, not a permission |
| Mass assignment | Pydantic `extra="forbid"` on all request models | Keep this on every new schema |
| Account takeover via recovery | None — no reset, no email verify, no MFA | High gap for a public deployment |
| Open signup abuse | `ALLOW_REGISTRATION`; per-IP register cap | Unset is off in production, on in development |
| Information leak | Stable error codes; 500/503 do not include internals | Register `409 email_taken` enumerates emails |
| Dependency compromise | Local `pip-audit` / `npm audit` this pass | Re-run before each release |

---

## 3. Endpoint inventory

| Method | Path | Public? | CSRF? | Authorization |
|---|---|---|---|---|
| `GET` | `/api/health` | Yes | No | None. Reports `database` as `ok` / `not_configured` / `unavailable`. |
| `POST` | `/api/auth/register` | Yes | Yes | Disabled when `ALLOW_REGISTRATION=false`. |
| `POST` | `/api/auth/login` | Yes | Yes | Rate limited. Same error for unknown email and bad password. |
| `POST` | `/api/auth/logout` | Yes (idempotent) | Yes | Deletes the presented session if any. |
| `GET` | `/api/auth/me` | No | No | Session user + current membership. |
| `POST` | `/api/workspaces` | No | Yes | Session. Rejects if a membership already exists. Sets `access_role=owner`. |
| `PATCH` | `/api/workspaces/current` | No | Yes | Session. Workspace name/description: owner only. Display name / research role: self. |
| `GET` | `/api/dashboard/summary` | No | No | Session + current workspace only. Query `workspace_id` is ignored. |
| `GET` | `/docs`, `/redoc`, `/openapi.json` | Dev only | No | Disabled when `ENVIRONMENT=production`. |

No other API routers exist in this batch. There is no password-reset, email-verify, MFA, invite, or workspace-by-id route.

---

## 4. Findings

Severity counts for this audit (implementation as reviewed, including remediations in the same pass):

| Severity | Total | Fixed this pass | Remaining open |
|---|---|---|---|
| Critical | 0 | 0 | 0 |
| High | 5 | 2 | 3 |
| Medium | 14 | 6 | 8 |
| Low | 6 | 0 | 6 |

### Critical

None verified. `backend/.env` is gitignored and not tracked. Passwords are not stored in plaintext. Auth does not fail open on database errors. Current routes do not accept a client-supplied workspace ID as the tenant key.

### High — fixed

| ID | Finding | Fix |
|---|---|---|
| H1 | Cookie-authenticated POST/PATCH/DELETE had no CSRF defense beyond `SameSite=Lax`. | Required header `X-OralSense-CSRF: 1`. Frontend `api.ts` sends it on every request. CORS allows that header. |
| H2 | `COOKIE_SECURE` defaulted to false and was independent of `ENVIRONMENT`. A production deploy on HTTP would set a non-Secure session cookie. | `session_cookie_secure` is always true when `ENVIRONMENT=production`. |

### High — remaining (identity features not built)

These are recorded as production gaps. They were **not** implemented in this pass (not required to close an exploitable hole in the current three-route surface, and the owner did not ask to invent those products).

| ID | Finding | Owner decision |
|---|---|---|
| H3 | No password reset or password-change flow. | How a researcher recovers a lost password, and whether a leaked password can be rotated without a new account. |
| H4 | No email verification. Anyone who can hit register can claim any address. | Acceptable only for a closed demo with registration disabled or invite-only later. |
| H5 | No MFA. | Required or not before real participant data is stored. |

### Medium — fixed

| ID | Finding | Fix |
|---|---|---|
| M1 | API responses lacked security headers. | `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, `COOP`, `Cache-Control: no-store`, API CSP, and HSTS in production. |
| M2 | FastAPI `/docs`, `/redoc`, `/openapi.json` would stay public in production. | Those URLs are disabled when `ENVIRONMENT=production`. |
| M3 | `CORS_ORIGINS=*` with credentialed cookies is a known footgun. | Startup raises if any origin is `*`. |
| M4 | Logout `delete_cookie` did not repeat `Secure` / `HttpOnly` / `SameSite`, so some browsers may keep the cookie. | Clear uses the same flags as set. |
| M5 | Login always minted a new token but left the presented session row valid. | Login revokes the incoming session when it belongs to the same user. Another user's session is not deleted. |
| M6 | 503 messages mentioned `DATABASE_URL` and `backend/.env`. | Public messages are now generic. Codes are unchanged so the UI can still guide a local operator. |

### Medium — remaining

| ID | Finding | Notes |
|---|---|---|
| M7 / M8 | Failed-login and register limiters are in-process dictionaries. | Reset on restart; not shared across workers. Per-IP counters were added; they are still not a production limiter. Do not trust `X-Forwarded-For` until a reverse proxy is defined. |
| M9 | `POST /api/auth/register` returns `409 email_taken`. | Login does not enumerate emails. Register does, by product choice. |
| M10 | No `TrustedHostMiddleware` / explicit host allow-list. | Host-header issues are an infra + app gap. |
| M11 | The app does not redirect HTTP→HTTPS. | HSTS is set only when `ENVIRONMENT=production`. TLS termination is an owner/infra task. |
| M12 | Concurrent sessions remain valid (login from a second browser does not revoke the first). | No session list UI. Owner should choose single-session vs multi-device. |
| M13 | Sessions expire on an absolute TTL (default 12 hours). No idle timeout. | Stolen cookies work until expiry or logout. |
| M14 | The SPA `index.html` has no Content-Security-Policy. | The API sets a strict CSP; that policy must not be copied onto the SPA. |
| M15 | No password-change, session-revoke-all, or security-event log. | Needed before treating accounts as long-lived research identities. |

### Low — remaining

| ID | Finding | Notes |
|---|---|---|
| L1 | Passwords use scrypt (`scrypt$n$r$p$salt_b64$hash_b64`), not Argon2id. | OWASP still lists scrypt as acceptable. Existing hashes were kept; any future algorithm must still verify this format. |
| L2 | Password policy is length 10–128 only. | Length is the main control; no complexity or breach check. |
| L3 | Cookie name is `oralsense_session`, not `__Host-`. | `__Host-` would require Secure + Path=/ and no Domain. Reasonable later hardening. |
| L4 | OpenAPI remains available in development. | Intentional. |
| L5 | `GET /api/health` is public and reports database status. | Useful for operators; low sensitivity. |
| L6 | `SameSite=Lax` rather than `Strict`. | Combined with the CSRF header this is acceptable for the SPA. |

### Verified non-findings (controls that already existed)

- `hmac.compare_digest` on password verify.
- Dummy scrypt when the email is unknown.
- Session token hashed with SHA-256 before insert.
- `extra="forbid"` on request bodies; client cannot set `access_role`, `workspace_id`, or `user_id`.
- Workspace edits for name/description require `access_role == owner` on the server.
- Logout deletes the database row; replay fails.
- Frontend `access_role === "owner"` only hides controls; the API is the authority.
- Database failure on a protected route returns 503, not an empty authenticated user.

---

## 5. Browser / CORS / CSRF / secrets

| Control | Status |
|---|---|
| CORS origins from settings, credentials on | Verified. Wildcard rejected. |
| CSRF on mutations | Verified after remediations. Trusted Origin + per-session synchronizer token. |
| Session cookie flags | HttpOnly, SameSite=Lax, Path=/, Secure in production. |
| `backend/.env` | Gitignored (`.gitignore` line `.env`). Not tracked. File type: local environment file. Value not recorded. |
| `backend/.env.example` | Tracked. Placeholders only (`CHANGE_ME`). |
| Frontend public env | No `VITE_` secrets found. |
| Rate limits | In-memory email + IP for login; IP for register. Remaining risk documented. |
| HTTPS | Not verified in this environment (local HTTP). Forced Secure cookie + HSTS when `ENVIRONMENT=production`. |

---

## 6. Dependencies (local tools only)

| Tool | Result |
|---|---|
| `backend/.venv` + `python -m pip_audit -r requirements.txt` | No known vulnerabilities found. |
| `frontend` `npm audit --json` | 0 vulnerabilities (info/low/moderate/high/critical). |

Source was not uploaded to a third-party scanner. No dependency upgrades were required. `pip-audit` is not a project dependency; it was run from the local virtualenv.

---

## 7. Tests added

`backend/tests/test_auth_security.py` (plus the existing `test_auth.py`, `test_workspaces.py`, `test_dashboard.py`):

- Unauthenticated access rejected
- Invalid credentials do not set a session
- Logout clears cookie attributes and deletes the row; replay fails
- Two users / two workspaces cannot read or write each other
- Client-supplied `access_role` / `workspace_id` rejected (`422`)
- Login rotates the presented session
- Register does not revoke another user's session
- Tampered and expired tokens rejected
- Unhandled errors and database failures do not fail open or leak internals
- Login rate limit returns `429`
- CSRF header required on mutations; GET/HEAD/OPTIONS exempt
- Security headers present; HSTS and OpenAPI disabled in production
- Wildcard CORS rejected at startup
- Session token stored hashed
- `ALLOW_REGISTRATION=false` enforced server-side

---

## 8. Owner blockers before any production-like deploy

1. Terminate TLS in front of the API and SPA. Do not serve this cookie session over HTTP.
2. Set `ENVIRONMENT=production`, pin `CORS_ORIGINS` to the real frontend origin only, and set `ALLOW_REGISTRATION=false` unless open signup is an explicit product choice.
3. Do not run multiple uvicorn workers until the rate limiter is moved off process memory (or accept that limits are per worker).
4. Decide password reset, email verification, MFA, and concurrent-session policy. None of those exist.
5. Add `TrustedHost` / proxy header policy when a reverse proxy is chosen.
6. Re-run this checklist on every new table that is keyed by participant, study, or assessment ID (IDOR risk appears as soon as those routes exist).
7. Do not describe this audit as a pentest, SOC 2, HIPAA, or “production hardened.”

---

## 9. Files changed in this pass

- `backend/app/http_security.py` (new)
- `backend/app/config.py`
- `backend/app/main.py`
- `backend/app/api/auth.py`
- `backend/app/services/auth_service.py`
- `backend/app/errors.py`
- `backend/tests/conftest.py`
- `backend/tests/test_auth_security.py` (new)
- `backend/.env.example`
- `frontend/src/lib/api.ts`
- `frontend/src/lib/errorMessages.ts`
- `docs/security/AUTH_SECURITY_AUDIT.md` (this file)
- `docs/security/PRODUCTION_SECURITY_CHECKLIST.md`

---

## 10. Follow-up audit (11 October 2026)

**Method:** Previous conclusions were treated as hypotheses. Code under `backend/app/*` and `frontend/src/lib/api.ts` was re-read. Login → authenticated mutation → logout was traced on the real path. Pytest was re-run against `oralsense_test`. `pip-audit` and `npm audit` were re-run. Live probes hit the already-running development API on `127.0.0.1:8000` without creating accounts or printing cookies.

**Scope unchanged:** email + password + `oralsense_session` cookie. No password reset, password change, email verification, or MFA was implemented. No auth architecture rewrite.

**Follow-up verdict:** **CONDITIONALLY READY** for the defined current-route scope after the owner blockers in §10.10. Not a pentest, not production-hardened, not ready for real participant data.

### 10.1 Sign-in → authenticated API → sign-out (re-traced)

1. Browser `fetch('/api/auth/login', { credentials: 'include', headers: { 'X-OralSense-CSRF': '1' }, body })` from `frontend/src/lib/api.ts`.
2. `BrowserSecurityMiddleware` rejects POST/PATCH/DELETE unless that header equals `1`. GET/HEAD/OPTIONS skip the check.
3. `auth.login` → `auth_service.login_user`: dummy scrypt on unknown email; `hmac.compare_digest` on known email; in-process email + IP limiters; `_revoke_own_session` only if the presented cookie hashes to a row for **that** user; new `secrets.token_urlsafe(32)` row; SHA-256 stored.
4. `oralsense_session` set with `HttpOnly`, `SameSite=Lax`, `Path=/`, `Secure` when `ENVIRONMENT=production` (forced) or `COOKIE_SECURE=true`.
5. Later `GET /api/auth/me`, `POST /api/workspaces`, `PATCH /api/workspaces/current`, `GET /api/dashboard/summary` resolve the user from the hashed cookie. Tenant data comes from `get_current_membership(user_id)` (earliest membership). Client `workspace_id` / `access_role` are rejected (`extra="forbid"`). Dashboard query `workspace_id` is never read.
6. `POST /api/auth/logout` deletes the hashed row and `delete_cookie`s with the same flags. Replay of the old value is `401 not_authenticated`.

### 10.2 Previous-fix verification

| ID | Prior claim | Follow-up status | Evidence |
|---|---|---|---|
| H1 CSRF `X-OralSense-CSRF: 1` | Required header fixes cookie CSRF | **PARTIALLY VERIFIED** | Missing header and wrong values (`''`, `0`, `true`, `1 `, etc.) return `403 csrf_rejected` on **every** current mutating route, including authenticated workspace POST/PATCH and logout. GET/HEAD/OPTIONS exempt. Origin/Referer **do not** replace the header and **are not** enforced server-side: `Origin: https://evil.example` plus header `1` still reaches the handler (`401 invalid_credentials` on unknown login). Static value is guessable by design. Defense is “browsers cannot set this header on a simple form post / unapproved origin,” plus `SameSite=Lax` and an explicit CORS allow-list. **Not** a per-session synchronizer token. Do not call the API CSRF-safe because one login 403s. |
| H2 Production `Secure` cookie | `ENVIRONMENT=production` forces Secure | **VERIFIED** | `session_cookie_secure` is `True` whenever `is_production`. Register `Set-Cookie` includes `Secure` even if `COOKIE_SECURE=false`. |
| Cookie HttpOnly / SameSite / Path | Set and tested | **VERIFIED** | Register and logout `Set-Cookie` include `HttpOnly`, `SameSite=Lax`, `Path=/`. |
| M4 Logout cookie flags | Clear repeats set flags | **VERIFIED** | Production logout `Set-Cookie` includes `Secure`, `HttpOnly`, `SameSite=Lax`, `Path=/`, `Max-Age=0`. Explicit presentation of the token deletes the DB row. TestClient over HTTP may omit a Secure cookie from its jar; that is a client-test limitation, not a missing `Secure` attribute. |
| M5 Session rotation | Login revokes presented own-session | **VERIFIED** | Re-login issues a new token; old token `401`. Unknown presented cookie is not adopted (session fixation check). Register does not revoke another user’s session. |
| Revoked token after logout | Replay rejected | **VERIFIED** | Logout deletes the row; replay `401 not_authenticated`. User B logout does not delete user A’s row. |
| DB failure fail-closed | `503`, not a signed-in user | **VERIFIED** | `get_db` `OperationalError` → `503 database_unavailable`, generic message, no traceback. |
| M3 Wildcard CORS | Startup reject | **VERIFIED** | `CORS_ORIGINS=*` → `create_app()` raises `RuntimeError`. Live + pytest: allowed origin reflected; `https://evil.example` gets no `Access-Control-Allow-Origin`. Disallowed preflight is `400` without ACAO. `allow_credentials=True` with no `*`. |
| M1 Security headers | Present on API | **PARTIALLY VERIFIED** | Health, `/me`, successful/failed login, 404, 405 include nosniff, DENY, API CSP, `no-store`, Referrer-Policy, Permissions-Policy, COOP. **CSRF `403` responses skip those headers** because the middleware returns the JSON 403 before wrapping `send`. Mutation is still blocked. HSTS only when `ENVIRONMENT=production` (pytest `create_app()`; not on the live development process). |
| M2 OpenAPI off in production | Disabled | **VERIFIED** (code + pytest) / **NOT APPLICABLE** live | Production `create_app()`: `/docs`, `/redoc`, `/openapi.json` are `404`. Live development process still serves them (`200`). |
| M6 5xx no internals | Generic messages | **VERIFIED** | Unhandled `RuntimeError` → `500 internal_error` without the leak marker. `503` messages do not name `DATABASE_URL`. Live error bodies had no traceback / `password_hash` / `postgresql+`. Frontend `errorMessages.ts` still mentions `backend/.env` for local operators; that is not an API leak. |
| `ALLOW_REGISTRATION=false` | Enforced | **VERIFIED** | `403 registration_disabled`; no user row. |

**CSRF adequacy for this scope:** the static custom header is an accepted SPA pattern **if** CORS stays an explicit allow-list and every mutation keeps requiring the header. It is **not** enough by itself, and it is **not** Origin-checked. Same-site subdomain form posts are the reason the header exists (`SameSite=Lax` would send the cookie). If `CORS_ORIGINS` ever includes an attacker origin, sending `X-OralSense-CSRF: 1` from JavaScript defeats this control.

### 10.3 Route inventory (re-checked)

| Method | Path | Public? | CSRF? | Authorization | Isolation tested this pass? |
|---|---|---|---|---|---|
| `GET` | `/api/health` | Yes | No | None. `database` is `ok` / `not_configured` / `unavailable`. | N/A (no tenant data) |
| `POST` | `/api/auth/register` | Yes | Yes | Disabled when `ALLOW_REGISTRATION=false`. | N/A (creates a new user) |
| `POST` | `/api/auth/login` | Yes | Yes | Rate limited. Same `invalid_credentials` body for unknown email and wrong password. | N/A |
| `POST` | `/api/auth/logout` | Yes (idempotent) | Yes | Deletes only the presented session. | **Yes** — B’s logout leaves A’s session valid |
| `GET` | `/api/auth/me` | No | No | Session user + current membership. | **Yes** |
| `POST` | `/api/workspaces` | No | Yes | Session. `access_role` forced to `owner`. Second workspace `409`. | **Yes** — B cannot create a second workspace or write A’s row |
| `PATCH` | `/api/workspaces/current` | No | Yes | Owner-only name/description; self display name / research role. | **Yes** — B rename leaves A’s name unchanged; injected `workspace_id` is `422` |
| `GET` | `/api/dashboard/summary` | No | No | Current membership only. `?workspace_id=` ignored. | **Yes** |
| `GET` | `/docs`, `/redoc`, `/openapi.json` | Dev only | No | Off when `ENVIRONMENT=production`. | N/A |
| `GET` | `/api/auth/logout` | N/A | N/A | No route. | **Yes** — `405`, session row unchanged |
| `GET`/`POST` | `/api/participants`, `/api/assessments`, `/api/studies`, `/api/protocols`, `/api/workspaces/{id}` | **Not implemented** | — | — | **NOT APPLICABLE** — `404`. Do not claim IDOR passed. |

No other FastAPI routers exist. `APIRouter` inventory is `health`, `auth`, `workspaces`, `dashboard` only.

### 10.4 Cross-workspace / adversarial coverage

| Case | Result |
|---|---|
| Missing session | `401 not_authenticated` on `/me`, dashboard, workspace POST/PATCH |
| Invalid / tampered / unknown token | `401 not_authenticated` |
| Expired session | `401 session_expired`; row deleted |
| Replay after logout | `401 not_authenticated` |
| Session fixation (attacker-chosen cookie on login) | New token issued; attacker value not adopted |
| Login rotation | Presented own-session revoked |
| Rate limit | 10 failed logins / 15 minutes → `429` (in-process; IP cap 20 not separately exercised — TestClient shares one address) |
| Register enumeration | `409 email_taken` still present |
| Login enumeration | Unknown email and wrong password return **identical** JSON |
| Two users, two workspaces | `/me`, dashboard, workspace POST, workspace PATCH, logout isolated |
| Owner vs member (SQL-inserted member) | Existing tests: member `403` on workspace name/description; may edit own profile |
| Planned participant/assessment/study routes | **Not implemented** (`404`) |

### 10.5 Findings in this follow-up

Previous severity totals are unchanged as a historical snapshot. This pass did **not** find a new exploitable Critical or High on the current route surface. No code fix was shipped: nothing met “verified Critical/High + safe without architecture change + locally testable + will not lock users out.”

#### New or refined

| ID | Severity | Status | Finding |
|---|---|---|---|
| H1 (refined) | High residual if CORS is loosened | Open residual | Static CSRF header is not bound to the session; server does not check Origin/Referer. Adequate for classic form CSRF only while CORS stays tight. |
| M16 | Medium | Open | CSRF `403` responses omit the security-header set (nosniff, DENY, CSP, `no-store`, …). The mutation is still rejected. Observed live and in middleware order. |
| L7 | Low | Open | Failed-login limiter is keyed by normalized email **before** the account exists. Ten failures against an address, then a successful register, then logout, can `429` a first login for up to 15 minutes. In-memory only. |
| L8 | Low | Open | Live `/docs` in development is wrapped in the API CSP (`default-src 'none'`), which will break Swagger UI scripts. Production disables the URL. |

Previous High gaps **H3–H5** (no password change/reset, no email verification, no MFA) remain open and were **not** implemented. Previous Medium **M7–M15** and Low **L1–L6** remain open as stated in the first pass.

#### Verified non-findings (re-confirmed)

- Passwords not stored in plaintext; scrypt + `hmac.compare_digest`; dummy hash on unknown email.
- Session token stored as SHA-256 hex only.
- Auth does not fail open on database errors.
- Current routes do not accept a client-supplied workspace ID as the tenant key.
- `backend/.env` exists locally, is gitignored (`.gitignore` line `.env`), and is **not** tracked. Type: local environment file. Value not recorded.
- No `VITE_` / `PUBLIC_` secrets. Frontend holds no session token in `localStorage` / `sessionStorage`.
- `extra="forbid"` on request bodies.

### 10.6 Account lifecycle (assessed, not implemented)

| Control | Exists? | Risk | Before release vs recommended |
|---|---|---|---|
| Password change (authenticated) | No | A leaked password cannot be rotated without a new account (and the old hash remains valid). | **Required** before treating accounts as long-lived research identities, even in a closed lab. **Recommended** before any multi-week demo. |
| Password reset (unauthenticated) | No | Lost password = operator intervention or a new email. Reset, if added later, is a high-risk flow (token in email, enumeration). | **Required** before public/open signup. **Not required** for a closed demo with operator-created accounts and `ALLOW_REGISTRATION=false`. |
| Email verification | No | Anyone who can hit register can claim any address (`409` then enumerates it). | **Required** before public signup. **Acceptable to skip** for a closed demo with registration disabled after seed accounts. |
| MFA | No | Password + stolen cookie (or guessed password) is the whole authenticator. | **Recommended** before real participant data. **Required** if this is exposed beyond a closed trusted network. Not required for a same-room hackathon demo. |

None of these were implemented in this pass.

### 10.7 Dependencies (independent re-run)

| Command | What was scanned | Result |
|---|---|---|
| `backend/.venv/Scripts/python.exe -m pip_audit -r requirements.txt` | Pins in `backend/requirements.txt` | No known vulnerabilities found. Exit 0. |
| `backend/.venv/Scripts/python.exe -m pip_audit` | **Installed set** in `backend/.venv` | No known vulnerabilities found. Exit 0. |
| `frontend` `npm audit --json` | Installed frontend tree (113 dependencies in the report metadata) | `vulnerabilities.total = 0` (info/low/moderate/high/critical all 0). npm printed an unrelated `devdir` npmrc warning. |

Source was not uploaded to a third-party scanner. `pip-audit` is not a project dependency.

### 10.8 Tests added this follow-up

Appended to `backend/tests/test_auth_security.py` (full suite **94 passed** against `oralsense_test`):

- CSRF required on every mutating route; wrong values rejected; Origin/Referer do not substitute
- Authenticated workspace POST/PATCH and logout still require the header (no state change on 403)
- Server processes a request with attacker `Origin` when the static header is present (documents missing Origin check)
- CORS allow vs deny + preflight
- Production logout cookie flags include `Secure`
- Login does not adopt an unknown presented cookie
- Logout does not revoke another user’s session
- Two users isolated on `/me`, dashboard, workspace POST, workspace PATCH
- Login unknown-email / wrong-password bodies are identical
- `GET /api/auth/logout` is `405` and does not delete the session
- Planned participant/assessment/study/protocol/`/workspaces/{id}` routes are `404`

### 10.9 Unverified external / infra controls

TLS termination, HTTP→HTTPS redirect, host allow-list / trusted proxy, PostgreSQL not reachable from the internet, backups, encryption at rest, production log redaction of cookies, WAF, multi-worker rate limiting, and the production values of `ENVIRONMENT`, `CORS_ORIGINS`, `ALLOW_REGISTRATION`, and `SESSION_TTL_HOURS` were **not** verified in this environment (local HTTP).

### 10.10 Remaining risks and owner blockers

1. Terminate TLS in front of the API and SPA. Do not serve this session cookie over HTTP.
2. Set `ENVIRONMENT=production`, pin `CORS_ORIGINS` to the single real frontend origin, and set `ALLOW_REGISTRATION=false` unless open signup is an explicit choice.
3. Do not run multiple uvicorn workers until the limiter is moved off process memory (or accept per-worker limits).
4. Decide password change/reset, email verification, MFA, and concurrent-session policy. None exist.
5. Add `TrustedHost` / proxy header policy when a reverse proxy is chosen.
6. Re-run IDOR review the moment participant, study, or assessment ID routes exist. Those routes are **not implemented** and were **not** authorized-tested.
7. Keep the CSRF header required on every new mutation. Do not treat the static value as a cryptographic token.
8. Do not describe this follow-up as a pentest, SOC 2, HIPAA, or “production hardened.”

### 10.11 Files changed in this follow-up

- `backend/tests/test_auth_security.py` (additional regressions)
- `docs/security/AUTH_SECURITY_AUDIT.md` (this follow-up)
- `docs/security/PRODUCTION_SECURITY_CHECKLIST.md` (follow-up statuses)

---

## 11. Remediation pass (11 October 2026)

**Scope:** Highest-priority verified gaps from the follow-up: CSRF (static header, no Origin check, headers omitted on CSRF 403), production registration default, and trusted-proxy / host-header policy. Password reset, MFA, email verification, and new infrastructure were not added.

**Method:** Implementation and tests were written against the current route surface, then `pytest` was run against `oralsense_test`. Frontend `npm run typecheck` and `npm run build` were run. TLS, PostgreSQL network isolation, backups, and encryption at rest were **not** exercised (this environment is local HTTP).

### 11.1 CSRF (H1 refined + M16)

Replaced the static `X-OralSense-CSRF: 1` check with:

1. **Trusted Origin** on POST/PATCH/PUT/DELETE. `Origin` must match `CORS_ORIGINS` or the request’s own scheme+host. `null`, empty, malformed, and untrusted Origins are rejected. `Referer` is not used as a substitute.
2. **Per-session synchronizer token** stored on `user_sessions.csrf_token` (plain, so `GET /api/auth/me` can return it). Login/register have no session yet: Origin is the primary defense. After a session exists, `X-OralSense-CSRF` must match that row. If Origin is omitted entirely, a matching token is the documented fallback — Origin-less mutations are never allowed without it.
3. **Security headers on CSRF 403.** The middleware now wraps the 403 `send` path with the same header set as other API responses.

Frontend `api.ts` no longer sends `1`. It stores `csrf_token` from login/register/`/me` in memory and sends it on mutations. Origin is sent by the browser. The Vite `/api` proxy remains compatible: the browser Origin is `http://localhost:5173`, which is on the default CORS list.

**Automated tests (VERIFIED):** missing Origin, untrusted Origin, `null` Origin, malformed Origin, static `1` insufficient, login/register with trusted Origin and no token, same-host Origin, missing/invalid token on every current authenticated mutation, legitimate Origin+token on workspace POST/PATCH/logout, Origin-less mutation only with a valid token, CSRF 403 includes nosniff/DENY/CSP/`no-store`.

### 11.2 Registration default (previous FAILED)

`ALLOW_REGISTRATION` unset now means **on in development, off in production**. Explicit `true` / `false` override. Production with registration still on logs the existing warning.

**Automated tests (VERIFIED):** production default off (unit + endpoint), explicit production opt-in, explicit development opt-out, development default on.

### 11.3 Deployment boundaries (previous M10 / FAILED)

- `TrustedHostMiddleware` with configurable `ALLOWED_HOSTS` (default `localhost,127.0.0.1,testserver`). `*` is rejected when `ENVIRONMENT=production`. `www_redirect` is off. Localhost is not broken.
- `X-Forwarded-Proto` / `X-Forwarded-For` are ignored unless `TRUST_FORWARDING=true` **and** the peer address is in `TRUSTED_PROXY_IPS`. Implemented with uvicorn `ProxyHeadersMiddleware`. `X-Forwarded-Host` is **not** applied (uvicorn 0.54 does not rewrite Host). `*` proxies are rejected in production. Empty `TRUSTED_PROXY_IPS` with forwarding on is rejected at startup.

The app **does not** terminate TLS, redirect HTTP→HTTPS, isolate PostgreSQL from the internet, take backups, or encrypt data at rest. Those are owner/infra tasks.

**Automated tests (VERIFIED):** unknown Host → 400; `localhost` Host → 200; production `ALLOWED_HOSTS=* ` → startup error; default ignores `X-Forwarded-*`; trusted peer + `TRUST_FORWARDING` accepts `https` same-host Origin; untrusted peer’s forwarded proto is ignored; production `TRUSTED_PROXY_IPS=*` → startup error.

**Deployment assumptions (NOT VERIFIED here):** real production hostname, real CORS origin, TLS terminator, proxy IP, PostgreSQL bind address, backups.

### 11.4 Verification run (this pass)

| Check | Result |
|---|---|
| Backend pytest against `oralsense_test` | **126 passed** |
| Frontend `npm run typecheck` | passed |
| Frontend `npm run build` | passed |

### 11.5 Owner steps before a closed demo

These are operator actions. App code does not perform them.

1. Run `alembic upgrade head` on the demo database so `user_sessions.csrf_token` exists. Existing sessions without a real token must sign in again.
2. Terminate TLS in front of the API and SPA. Do not serve this session cookie over HTTP.
3. Set `ENVIRONMENT=production`.
4. Set `CORS_ORIGINS` to the single real frontend origin (the page origin the browser will send).
5. Set `ALLOWED_HOSTS` to the API hostname the browser/proxy will put in `Host` (drop `testserver` on a real host).
6. Leave `ALLOW_REGISTRATION` unset (off in production) or set `false` after seeding accounts. Set `true` only if the demo must create accounts in the UI.
7. If a reverse proxy terminates TLS: `TRUST_FORWARDING=true` and `TRUSTED_PROXY_IPS=<proxy peer>`, usually `127.0.0.1` if the proxy is on the same machine. Otherwise leave `TRUST_FORWARDING=false`.
8. Accept remaining product gaps: in-memory rate limits, no MFA, no password change/reset, no email verification, no SPA document CSP, no `__Host-` cookie prefix.
9. Do not store real participant identifiers on a public host.

### 11.6 Remaining risks (unchanged product / infra gaps)

H3–H5 (no password change/reset, email verification, MFA). M7/M8 (in-process rate limits). M9 (register email enumeration). M11 (HTTP→HTTPS is proxy work). M12–M15 (concurrent sessions, no idle timeout, no SPA CSP, no password-change / revoke-all). L1–L8 as previously recorded. IDOR on participant/assessment/study routes remains **NOT APPLICABLE** (`404`).

### 11.7 Files changed in this remediations pass

- `backend/alembic/versions/0002_session_csrf_token.py`
- `backend/app/config.py`, `models.py`, `schemas.py`, `security.py`, `http_security.py`, `main.py`, `deps.py`
- `backend/app/api/auth.py`, `backend/app/api/workspaces.py`
- `backend/app/services/auth_service.py`
- `backend/tests/conftest.py`, `test_auth.py`, `test_auth_security.py`, `test_deployment_boundaries.py`
- `backend/.env.example`
- `frontend/src/lib/api.ts`, `frontend/src/lib/types.ts`
- `README.md` (env table only)
- `docs/security/AUTH_SECURITY_AUDIT.md` (this section)
- `docs/security/PRODUCTION_SECURITY_CHECKLIST.md`
