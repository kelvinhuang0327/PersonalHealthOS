# P44 – Report Download Token URL Risk Policy

**Stage**: P44  
**Classification**: P44_REPORT_DOWNLOAD_TOKEN_RISK_DOCUMENTED  
**Status**: COMPLETE  
**Branch**: main  
**Starting HEAD**: `2c38ebb` (P43 closure)  
**Commits**: `e95d151` (tests), C2, C3  
**Date**: 2026-05-24  

---

## Summary

P39 documented residual risk R5: the report download token appears in the URL query string, creating potential token leakage through server-side access logs or other URL-exposure mechanisms. P44 audits the current download flow, verifies the token-alone threat is mitigated by P20's JWT owner requirement, adds tests for the previously untested "no JWT" scenario, and documents the accepted residual risk.

**Result**: No backend code change required. Tests added. Risk documented and classified.

---

## Governance Pre-flight

| Check | Result |
|-------|--------|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| Status | Clean ✅ |
| HEAD | `2c38ebb` (P43 docs) ✅ |

---

## Investigation

### Current Report Download Contract

```
POST /api/v1/reports/generate        → { report_id, status }
GET  /api/v1/reports/{report_id}     → { status, download_url }  [requires JWT owner]
GET  /api/v1/reports/download/{id}?token=<token>  [requires JWT owner + token]
```

**`generate_report`** (POST):
- Requires `get_current_user` (JWT) + `get_target_person`
- Stores `owner_user_id = str(current_user.id)` in `_REPORT_STATE`
- Generates a UUID `token` stored in `_REPORT_STATE`, never returned directly to client

**`get_report_status`** (GET `/{report_id}`):
- Requires `get_current_user` (JWT)
- Returns 404 if `owner_user_id != current_user.id`
- When ready: builds `download_url = f'/api/v1/reports/download/{report_id}?token={token}'`
- Token is embedded in the URL returned to the owner only

**`download_report`** (GET `/download/{report_id}`):
- Requires `get_current_user` (JWT) — **added in P20**
- Checks `owner_user_id == current_user.id` → 404 if mismatch
- Checks `token == state['token']` → 403 if mismatch
- Checks expiry (1 hour) → 403 if expired
- Returns `FileResponse` (PDF) only if all checks pass

### Frontend Flow (post-P20, confirmed in investigation)

```tsx
// report-export-modal.tsx — handleDownload()
const res = await fetch(fullUrl, {
  headers: token ? { Authorization: `Bearer ${token}` } : {},
})
const blob = await res.blob()
const objectUrl = URL.createObjectURL(blob)
// ... a.click() to trigger download
```

The frontend uses `fetch + blob + createObjectURL` — **no browser navigation, no `<a href target="_blank">`**. The download URL containing the token is only used as a `fetch()` argument, not as a navigation target.

---

## Token Leakage Vector Analysis

| Vector | Status | Evidence |
|--------|--------|---------|
| Browser history | **NOT AT RISK** | `fetch()` does not create browser history entries |
| Copied address bar URL | **NOT AT RISK** | No browser navigation (fetch+blob) |
| Cross-origin Referer header | **NOT AT RISK** | Same-origin fetch; browser omits Referer for same-origin |
| Server-side access logs | **⚠ RESIDUAL RISK** | nginx/uvicorn logs include query string: `?token=<uuid>` |
| APM / observability tooling | **⚠ RESIDUAL RISK** | URL params captured in traces if full URL logging enabled |
| DevTools Network tab | **LOCAL ONLY** | Accessible only to authenticated user on their own machine |

### Impact Assessment

Even if the token leaks via server-side logs:

- **No JWT + stolen token → HTTP 401** (OAuth2PasswordBearer rejects at auth layer)
- **Cross-user JWT + stolen token → HTTP 404** (owner mismatch guard)
- **Only owner JWT + correct token → HTTP 200**

**Impact**: LOW. The token is not exploitable without the matching owner JWT. Token alone does not grant access.

### Stale Docstring Note

`test_report_authorization_hardening.py` class `TestReportDownloadTokenOnly` contains:
> "The download endpoint is token-only (no JWT auth)"

This reflects the P18 state and is outdated. P20 added `get_current_user` to the download endpoint. The method `test_download_cross_user_denied` within the same class correctly documents the P20 behaviour. The class-level docstring was not modified in P44 (cosmetic change, out of scope). The P44 test file establishes the authoritative current policy.

---

## Test Gap Identified and Closed

**Gap**: "no JWT + valid token → 401" was not tested in any existing test file.

**Root cause**: P18's test class for the download endpoint was written with the assumption that the endpoint was token-only (no JWT). P20 silently added JWT as a required dependency and added `test_download_cross_user_denied` (which uses a valid JWT), but left the no-JWT path untested.

---

## Tests Added

**File**: `backend/tests/test_report_download_token_policy.py` (new, 5 tests)

| Class | Test | Assertion |
|-------|------|-----------|
| `TestDownloadEndpointRequiresJWT` | `test_no_jwt_valid_token_denied` | No Authorization header + valid token → **401** |
| `TestDownloadTokenStandaloneAttack` | `test_stolen_token_no_jwt_denied` | Server-log leak scenario: token + no JWT → **401** |
| `TestDownloadTokenStandaloneAttack` | `test_cross_user_jwt_valid_token_denied` | Attacker's valid JWT + stolen token → **404** |
| `TestDownloadTokenBodyDoesNotLeakToken` | `test_403_body_does_not_echo_token` | Wrong token → 403; body does not expose real/submitted token |
| `TestDownloadTokenBodyDoesNotLeakToken` | `test_404_body_does_not_echo_token` | Cross-user → 404; body does not leak token, report_id, owner id |

### Test Design Decisions

- **`_seed_ready_report`**: Seeds `_REPORT_STATE` directly (no `generate` call). File path is `/dev/null` — never reached because auth/owner/token checks raise `HTTPException` before `FileResponse`.
- **`_client_no_jwt`**: Overrides only `get_db` (SQLite); `get_current_user` remains the real OAuth2 validator. Requests without Authorization header → 401.
- **`autouse` fixture**: Clears both `_REPORT_STATE` and `app.dependency_overrides` before and after each test.

---

## Test Results

| Suite | Result |
|-------|--------|
| `test_report_download_token_policy.py` (5 new) | **5/5 passed** |
| `test_report_authorization_hardening.py` (9 existing) | **9/9 passed** |
| Combined targeted (14) | **14/14 passed** |
| `make runtime-smoke` | **118 passed, 2 skipped** |
| Full backend suite | **976 passed, 2 skipped** (971→976, +5) |

---

## Files Changed

| File | Change |
|------|--------|
| `backend/tests/test_report_download_token_policy.py` | **CREATED** — 5 tests, P44 policy coverage |

No backend production code was modified. No frontend files were modified.

---

## Accepted Residual Risk

| Risk | Level | Mitigation |
|------|-------|-----------|
| Token in server-side access logs | LOW | Token alone → 401; requires owner JWT to exploit |
| Token in APM URL traces | LOW | Same as above |

**Accepted for P44.** Token-URL leak is low impact because:
1. JWT owner check added in P20 is the primary gating credential.
2. Download token (UUID) is short-lived (1-hour expiry).
3. Frontend fetch+blob flow prevents browser history and address bar exposure.

---

## Recommended Future Mitigation (P45+)

Move token from URL query string to request header to eliminate server-log exposure:

```python
# Backend: accept token from X-Report-Download-Token header
X_Report_Download_Token = Header(alias='X-Report-Download-Token', default=None)

# Status response: return token separately (not embedded in URL)
class ReportStatusResponse(BaseModel):
    status: str
    download_url: Optional[str] = None
    download_token: Optional[str] = None  # returned only when status=ready
```

```tsx
// Frontend: strip token from URL, send as header
const res = await fetch(cleanDownloadUrl, {
  headers: {
    Authorization: `Bearer ${jwtToken}`,
    'X-Report-Download-Token': reportToken,
  },
})
```

**Scope**: Requires schema change (`ReportStatusResponse`), backend header parsing, frontend header addition, and updates to multiple schema-leakage tests. Out of P44 scope. Recommend P45.
