# Plan: Admin invites

**Date:** 2026-09-11  
**Status:** Done  
**Architecture SoT:** `docs/architecture.md` §2.1 (tenancy admin), §5 (AuthN/AuthZ), §12 (change protocol)

## What / why

| | |
|--|--|
| **What** | Productize the existing `admin_invites` SQLite table into a full invite flow: admin creates invite → invitee opens link → sets password → becomes an active user. |
| **Why** | Table + delete-on-user-cleanup already exist, but there is no create/list/accept API or UI. Operators today must create users with a known password via `CreateUserDialog` / CLI. |

## Current schema (v6)

```sql
admin_invites (
  id, email, token UNIQUE, created_by, expires_at, created_at
)
```

Gaps for a real product flow:

- No **role** on invite (admin/user/viewer)
- No **used_at** / single-use marker
- Token likely stored as plaintext (should store **hash**, return plaintext once — same pattern as API keys)

## Proposed design

### Schema migration (new `_migrations` entry)

Add columns (SQLite-friendly ALTER / recreate pattern used elsewhere):

| Column | Purpose |
|--------|---------|
| `role` TEXT NOT NULL DEFAULT `'user'` | Role granted on accept |
| `token_hash` TEXT UNIQUE | SHA-256 of invite token (migrate from `token` if present) |
| `used_at` TEXT NULL | Set when accepted; non-null ⇒ spent |
| Drop plaintext `token` after hash backfill if needed | Avoid dual storage |

Keep `email`, `created_by`, `expires_at`, `created_at`.

### API (admin JWT only for management; accept is public)

| Method | Path | Auth | Behavior |
|--------|------|------|----------|
| `POST` | `/api/admin/invites` | AdminUser | Body: `email`, `role`, optional `expires_in_hours` (default 72). Create row; return `{ id, email, role, expires_at, invite_url, plain_token }` once. |
| `GET` | `/api/admin/invites` | AdminUser | List pending/used/expired invites (filter query optional). Never return raw token. |
| `DELETE` | `/api/admin/invites/{id}` | AdminUser | Revoke unused invite. |
| `GET` | `/api/auth/invites/{token}` | Public | Validate token; return `{ email, role, expires_at }` or 404/410. |
| `POST` | `/api/auth/invites/{token}/accept` | Public | Body: `password`, optional `name`. Create user, mark `used_at`, return login tokens (or redirect client to login). |

**Rules:**

- Email normalized lower-case; conflict if user already exists (409).
- Expired or used invite → 410 Gone.
- Role must be `admin` \| `user` \| `viewer`.
- Accept path must **not** use API-key auth; public token in URL is the credential.
- Admin invite CRUD rejects API keys (already true via `AdminUser`).

### SPA

| Surface | Behavior |
|---------|----------|
| Admin **Users** page | “Invite user” dialog: email + role; show invite link once; list pending invites with revoke. |
| Public `/invite/:token` | Unauthenticated route: show email/role, password + name form, submit accept → land in panel. |

Keep existing **Create user** (password known to admin) as alternate path.

```mermaid
sequenceDiagram
  participant Admin as Admin SPA
  participant API as FastAPI
  participant SQ as SQLite
  participant Invitee as Invitee browser

  Admin->>API: POST /admin/invites (JWT)
  API->>SQ: INSERT admin_invites (token_hash, email, role, expires)
  API-->>Admin: invite_url + plain_token (once)
  Invitee->>API: GET /auth/invites/{token}
  API-->>Invitee: email, role
  Invitee->>API: POST /auth/invites/{token}/accept
  API->>SQ: INSERT users; SET used_at
  API-->>Invitee: access + refresh tokens
```

## Architectural impact

| Area | Impact |
|------|--------|
| §2.1 Tenancy admin | New invite router / auth accept endpoints |
| §5 Auth | Public accept path; still tenant = `users.id` after accept |
| §2.4 SQLite | Migration on `admin_invites` |
| Workers / pipeline / Mongo | None |
| Deploy | No new env vars for v1 (link base from `window.location.origin` or optional `PUBLIC_APP_URL` later) |

## Risks / mitigations

| Risk | Mitigation |
|------|------------|
| Token leakage in logs/URLs | Hash at rest; one-time show; short TTL (72h default) |
| Open registration abuse | Accept only with valid unused unexpired token |
| Admin role via invite | Allowed but confirm in UI copy; audit via `created_by` |
| Migration of empty table | No rows expected; still handle `token` → `token_hash` if any |
| Dual create-user vs invite confusion | Label UI: “Create with password” vs “Invite by email” |

## Doc updates (same change)

- `docs/architecture.md` §2.1 / §5 — invite flow + diagram note  
- `docs/dev-cheatsheet.md` — invite feature → files → tests  
- `docs/plans/README.md` — mark this plan Done when shipped  
- Root `README.md` — brief admin invite mention if onboarding section fits  

## Test plan

| Layer | Cases |
|-------|--------|
| Unit | Token hash helper; expiry / used guards |
| API | Create invite as admin; list; revoke; accept happy path; reject expired/used/bad token; reject duplicate email; viewer cannot create invite |
| Migration | New columns / indexes present |
| Frontend | Invite dialog + accept page Vitest |

Commands while iterating:

```bash
pytest tests/api/test_admin_invites.py tests/unit/test_migrations.py -q
cd frontend && npm run test -- src/pages/admin/Users.test.tsx src/pages/InviteAccept.test.tsx
```

## Implementation order

1. Failing migration + API tests  
2. Migration + invite service/router + auth accept  
3. Admin Users UI + `/invite/:token` page  
4. Sync architecture / cheatsheet / this plan status  
5. Run focused then broader tests  

## Decision for approver

Default assumptions unless you change them:

- Default expiry **72 hours**  
- Invite may grant **admin** role  
- Accept returns **JWT pair** (auto-login)  
- No email sending in v1 (admin copies link)  

Reply **approve implement** to build, or adjust assumptions first.
