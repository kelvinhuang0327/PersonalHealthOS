# P45 – Report Download Token: URL → Header Migration

**Stage**: P45  
**Classification**: P45_REPORT_DOWNLOAD_TOKEN_HEADER_HARDENED  
**Status**: COMPLETE  
**Branch**: main  
**Starting HEAD**: `389b7fa` (P44 closure)  
**Commits**: `97c6096` (backend), `47f0148` (frontend), `51a7ca8` (tests)  
**Date**: 2026-05-24  

---

## Summary

P44 documented that the download token appearing in the URL query string could leak via server-side access logs. P45 implements the deferred mitigation: the backend now accepts the token from an `X-Report-Download-Token` request header, and the frontend extracts the token from `download_url`, strips it from the request URL, and sends it as a header. Token no longer appears in the fetch URL seen by the web server.

---

## Governance Pre-flight

| Check | Result |
|-------|--------|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| Status | Clean ✅ |
| Head | `389b7fa` (P44 docs) ✅ |

---

## Backend Token Contract

### Before P45

```python
@router.get('/download/{report_id}')
def download_report(
    report_id: str,
    token: str,                                          # required query param only
    current_user: Annotated[User, Depends(get_current_user)],
):
    if token != state.get('token'):
        raise HTTPException(status_code=403, detail='Invalid token')
```

Token was a **required query string parameter** — appeared in every access log.

### After P45

```python
@router.get('/download/{report_id}')
def download_report(
    report_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    token: Optional[str] = Query(default=None),
    x_report_download_token: Optional[str] = Header(default=None, alias='X-Report-Download-Token'),
):
    # Header takes priority; query string is the backward-compatible fallback.
    provided_token = x_report_download_token or token
    ...
    if not provided_token or provided_token != state.get('token'):
        raise HTTPException(status_code=403, detail='Invalid token')
```

**Token resolution order**:
1. `X-Report-Download-Token` header (preferred — does not appear in URL)
2. `?token=` query parameter (backward-compatible fallback)

**Strict header preference**: If header is present but invalid, request is rejected (HTTP 403) even when a valid query token is also supplied. This prevents an attacker from forcing fallback to an observed query token.

---

## Frontend Change

**File**: `frontend/app/components/platform/report-export-modal.tsx` — `handleDownload()`

### Before P45

```tsx
const fullUrl = downloadUrl.startsWith('http') ? downloadUrl : `${apiBase}${downloadUrl}`
// ↑ fullUrl includes ?token=<uuid> — appears in server access log

const res = await fetch(fullUrl, {
  headers: token ? { Authorization: `Bearer ${token}` } : {},
})
```

### After P45

```tsx
const fullUrl = downloadUrl.startsWith('http') ? downloadUrl : `${apiBase}${downloadUrl}`

// Extract token from URL and strip before fetch (P45 hardening)
let fetchUrl = fullUrl
let reportToken: string | null = null
try {
  const parsed = new URL(fullUrl)
  reportToken = parsed.searchParams.get('token')
  parsed.searchParams.delete('token')
  fetchUrl = parsed.toString()          // ← no token in URL
} catch {
  // URL parsing failed; fall back to original URL
}

const headers: Record<string, string> = {}
if (jwtToken) headers['Authorization'] = `Bearer ${jwtToken}`
if (reportToken) headers['X-Report-Download-Token'] = reportToken  // ← token in header

const res = await fetch(fetchUrl, { headers })
```

`fetchUrl` sent to server: `/api/v1/reports/download/{id}` — **no token in URL**.  
Token sent via header: **not captured by standard URL-based access logs**.

---

## Status Response (Unchanged)

`ReportStatusResponse` schema is **not changed**:
- `status: str`
- `download_url: Optional[str]` — still contains `?token=...` (needed so frontend has access to the token value)

The token embedded in `download_url` is used by the frontend to extract the token for the header; the actual fetch request strips it. The status endpoint requires owner JWT, so `download_url` is only returned to the authenticated owner.

`test_response_leakage.py` schema assertions remain valid — no `download_token` field added.

---

## Query String Backward Compatibility

The `?token=` query parameter **remains supported** as a fallback. This preserves backward compatibility for:
- Any existing API clients not yet migrated
- Direct API calls in tests using `params={'token': ...}`

All existing test files (`test_report_authorization_hardening.py`, `test_injection_smoke.py`) continue to pass without modification.

---

## Tests Added (P45)

**File**: `backend/tests/test_report_download_token_policy.py` — new class `TestHeaderTokenDownload` (7 tests)

| Test | Validates |
|------|-----------|
| `test_header_token_owner_jwt_succeeds` | Header token + no query → **200** PDF |
| `test_query_token_backward_compat_succeeds` | Query token + no header → **200** (backward compat) |
| `test_header_preferred_header_valid_query_invalid` | Header valid + query invalid → **200** (header wins) |
| `test_header_preferred_header_invalid_query_valid_rejected` | Header invalid + query valid → **403** (no silent fallback) |
| `test_no_token_at_all_denied` | No header + no query → **403** |
| `test_cross_user_jwt_valid_header_token_denied` | Cross-user JWT + header token → **404** |
| `test_no_jwt_valid_header_token_denied` | No JWT + header token → **401** |

The 3 success-path tests (→ 200) use `tmp_path` (pytest fixture) to create a real temp PDF file. The 4 failure-path tests use `_seed_ready_report` with `/dev/null` — file not reached before `HTTPException` fires.

---

## Validation Results

| Suite | Result |
|-------|--------|
| `test_report_download_token_policy.py` (12 total: 5 old + 7 new) | **12/12 passed** |
| `test_report_authorization_hardening.py` (9 existing) | **9/9 passed** |
| `test_response_leakage.py` (12 existing) | **12/12 passed** |
| Frontend `tsc --noEmit` | **0 errors** |
| `make runtime-smoke` | **118 passed, 2 skipped** |
| Full backend suite | **983 passed, 2 skipped** (976→983, +7) |

---

## Files Changed

| File | Change |
|------|--------|
| `backend/app/api/reports.py` | Added `Header`, `Query` imports; download endpoint now accepts `X-Report-Download-Token` header with query fallback |
| `frontend/app/components/platform/report-export-modal.tsx` | `handleDownload()` strips token from URL, sends via `X-Report-Download-Token` header |
| `backend/tests/test_report_download_token_policy.py` | Added `from pathlib import Path`, `_seed_ready_report_with_pdf()`, `TestHeaderTokenDownload` (7 tests) |

---

## Threat Model After P45

| Vector | Status |
|--------|--------|
| Server-side access logs (query string) | **MITIGATED** — fetch URL no longer contains token |
| Browser history | **NOT AT RISK** (unchanged — fetch+blob) |
| Copied URL from address bar | **NOT AT RISK** (unchanged — fetch+blob) |
| Request headers in access logs | LOW — headers not logged by default in nginx/uvicorn standard config |
| DevTools Network tab | LOCAL ONLY (developer, authenticated) |
| Stolen token + no JWT | **→ 401** (unchanged) |
| Stolen token + cross-user JWT | **→ 404** (unchanged) |

---

## Remaining Limitations

| Item | Status |
|------|--------|
| `download_url` still contains `?token=...` in status response | Accepted — needed for frontend token extraction; status endpoint requires owner JWT |
| Header logging in non-standard server config | LOW — not logged by default; operational concern, not code gap |
| Query string fallback still accepted | Intentional backward compat; no known active usage after P45 |
