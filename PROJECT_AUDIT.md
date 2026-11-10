# TrustCart AI verification audit

**Audit date:** 2026-11-10  
**Environment:** Windows PowerShell, Python 3.12, Node.js/npm, local SQLite

Status meanings: **PASS** = verified by a local check; **FAIL** = verified gap; **NOT TESTED** = evidence could not be established; **BLOCKED** = requires credentials or external access.

## Scope and limitations

- Read `README.md`, `ARCHITECTURE.md`, and this audit. They are the project's Markdown documentation.
- Reviewed the full application/test source set (29 files), frontend manifests/configuration (8 files), backend dependency/environment example (2 files), and root documentation/ignore files (4 files): 43 project files total.
- The workspace has no `.git` directory. `git status --short` and `git rev-parse --show-toplevel` both returned `fatal: not a git repository`. Therefore, the requested list of exactly 39 changed files cannot be reconciled to a base revision (**NOT TESTED**); no claim is made that these 43 files are exactly the 39 changed files. Local `.env` and SQLite data were treated as runtime files, not source.

## Requirement results

| Requirement | Status | Evidence |
|---|---|---|
| Read README and all project documentation | **PASS** | Read all three project Markdown files; README updated to document port fallback and cancellation behavior. |
| Verify all 39 changed files | **NOT TESTED** | No Git metadata exists to identify the changed-file set. Reviewed the 43 project source, test, config, and documentation files listed above. |
| Verify backend/frontend dependencies | **PASS** | `python -m pip check`: `No broken requirements found.` `npm ls --depth=0`: installed dependency tree resolves, including React 18.3.1, TypeScript 5.7.3, Vite 6.4.6, and Recharts 2.15.4. |
| Start both servers using documented PowerShell commands | **PASS** | Backend startup completed at `http://127.0.0.1:8000`; frontend started at `http://localhost:5174/` because 5173 was occupied. `/api/health`, Swagger, and Vite returned HTTP 200. |
| Test every backend API endpoint | **PASS** | Repeatable tests in `backend/tests/test_api.py` and an isolated `TestClient` endpoint matrix cover health, product list/detail, cart read/write, agent chat, checkout, payment capture, cancellation, and order list/detail. Results are detailed below. |
| Verify AI tool calling using Groq | **BLOCKED** | `GROQ_API_KEY` is empty. The mocked test verifies all six tool calls against the seeded test database; it is not a real Groq response. No AI response is claimed. |
| Verify product search, comparison, and recommendations | **PASS** | API search/filter checks passed; the Groq-tool test double exercised search, compare, and recommendation functions with a strict budget. Browser search returned one Sony product; the comparison showed two products; fallback assistant returned four catalogue results for a laptop budget query. |
| Test cart calculations and stock validation | **PASS** | API totals matched catalogue price × quantity; quantity zero removed an item; overstock returned 409 and negative quantity returned 422. Browser showed `$549.00` for one item and `$1,098.00` for two. |
| Verify PayPal Sandbox create, approval, capture, and payment verification | **BLOCKED** | Both PayPal credential fields are empty. No live Sandbox order, buyer approval, capture, or verification was attempted; no transaction is represented as real. Unconfigured checkout returned 503 and left the order unpaid. Test doubles cover pending, amount mismatch, and idempotent capture logic only. |
| Test failure cases, invalid inputs, and duplicate payment prevention | **PASS** | Empty chat and negative quantity returned 422; unknown product/order returned 404; overstock returned 409; no-credential checkout returned 503; amount mismatch returned 502 and remained unpaid; repeated mocked capture returned the existing transaction and called the capture provider once. A failed checkout can no longer be falsely reported as cancelled (see fixes). |
| Test React frontend in the browser | **PASS** | Browser loaded 24 products with no alert or console/page errors after the CORS fix. Tested search, comparison, add-to-cart, quantity update, assistant fallback, checkout warning, save toggle, mobile menu, Orders, and Insights. The browser automation's pointer-click helper timed out waiting for a stable target; handlers were verified with DOM-dispatched clicks. Manual mouse/touch interaction was not tested. |
| Run backend tests and frontend production build | **PASS** | Backend: `16 passed, 1 warning`. Frontend TypeScript check and Vite production build succeeded; Vite reported a non-fatal 550.02 kB minified charts chunk warning. |
| Check hardcoded secrets, exposed credentials, and non-functional buttons | **PASS** | No credential patterns found in application source/docs; `.env` is ignored by `.gitignore`; Groq and PayPal values were checked only for presence and all are empty. The inert “TC” button was changed to a non-interactive avatar. Save-item toggles its visible state but is component-local and not persisted. |
| Production customer authorization and concurrency safety | **FAIL** | This remains a demo, not production-ready: `X-Customer-Id` is client-controlled and is not authentication; SQLite does not provide production inventory reservations. These documented limitations were not expanded into unrelated features. |

## Commands and results

### Startup

Backend, from the README:

```powershell
Set-Location 'D:\TrustCart AI\backend'
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --env-file .env
```

Result: Uvicorn started and application startup completed on `http://127.0.0.1:8000`.

Frontend, from the README:

```powershell
Set-Location 'D:\TrustCart AI\frontend'
npm run dev
```

Result: Vite 6.4.6 started on `http://localhost:5174/`; it reported `Port 5173 is in use, trying another one...`. The initial 5174 browser request failed CORS with `Disallowed CORS origin`; `backend/app/main.py` was updated to allow local development origins on alternate localhost ports, and that live preflight then returned 200. An external origin (`https://untrusted.example`) still returned 400. For PayPal return/cancel URLs, set `FRONTEND_ORIGIN` in `backend/.env` to the actual Vite URL.

Live health result:

```json
{"status":"ok","ai_mode":"fallback","paypal_sandbox_configured":false}
```

### Tests, build, and dependency checks

```powershell
Set-Location 'D:\TrustCart AI\backend'
.\.venv\Scripts\python.exe -m pytest tests -q
```

Result: `16 passed, 1 warning in 2.49s`. Warning: Starlette deprecates using `httpx` with `starlette.testclient`; it did not fail tests.

```powershell
Set-Location 'D:\TrustCart AI\frontend'
npm run build
```

Result: `tsc -b` and `vite build` succeeded. Non-fatal warning: `charts-BuYVnoQj.js` is 550.02 kB minified (157.78 kB gzip), above Vite's 500 kB advisory threshold.

```powershell
Set-Location 'D:\TrustCart AI\backend'
.\.venv\Scripts\python.exe -m pip check
Set-Location 'D:\TrustCart AI\frontend'
npm ls --depth=0
```

Result: `No broken requirements found.` and all top-level frontend dependencies resolved.

### Endpoint and behavior matrix

Repeatable command for the backend suite:

```powershell
Set-Location 'D:\TrustCart AI\backend'
.\.venv\Scripts\python.exe -m pytest tests -q
```

The additional isolated `TestClient` matrix used in-memory SQLite (no persistent test data). Results:

| Endpoint / case | Result |
|---|---|
| `GET /api/health` | 200 |
| `GET /api/products` and query/category/budget/featured filters | 200 |
| `GET /api/products/{id}` / missing product | 200 / 404 |
| `GET /api/cart`; valid `PUT /api/cart/items`; remove with quantity 0 | 200 |
| `PUT /api/cart/items` over stock / negative quantity / unknown product | 409 / 422 / 404 |
| `POST /api/agent/chat` / empty message | 200 labeled fallback / 422 |
| `POST /api/checkout` without PayPal credentials | 503; local order remains unpaid |
| `POST /api/payments/{id}/capture` unknown order | 404 |
| Mocked capture with exact amount, then duplicate capture | 200; second call reuses transaction; provider called once |
| Mocked capture amount mismatch | 502; order remains unpaid |
| `POST /api/checkout/{id}/cancel` pending unpaid / failed checkout | 200 cancelled / 409 |
| `GET /api/orders`; owner and other-customer order detail | 200 / 200 and 404 respectively |

Mocked PayPal IDs and responses exist only in isolated tests; they are not external PayPal transactions. The live test made no checkout request that could have reached PayPal.

## Fixes made and retest

- `backend/app/main.py`: added localhost/127.0.0.1 CORS matching for Vite's alternate local ports. Verified live 5174 preflight is 200 and an untrusted external origin remains 400.
- `backend/app/routers/orders.py`: cancellation now accepts only pending unpaid orders. A failed checkout previously returned 200 without changing state; it now returns 409. Added regression coverage.
- `backend/tests/test_api.py`: added endpoint, validation, cancellation, amount-mismatch, and duplicate-capture coverage. Final suite: 16 passed.
- `frontend/src/App.tsx` and `frontend/src/index.css`: changed the inert customer initials button to a non-interactive avatar while preserving its appearance. Browser verified zero avatar buttons and one avatar element.
- `README.md`: documented alternate Vite ports, PayPal origin configuration, and pending-only cancellation.
- Final `npm run build`: succeeded after frontend changes.

## Remaining blockers and files needing configuration or future work

| File(s) | Status | Action / limitation |
|---|---|---|
| `backend/.env` | **BLOCKED** | Add Groq and PayPal Sandbox credentials to exercise real external integrations. Keep secrets server-side; do not include their values in this report. Set `FRONTEND_ORIGIN` to the actual Vite URL before Sandbox approval/return testing. |
| `backend/app/routers/cart.py`, `backend/app/models.py` | **FAIL for production** | Replace the spoofable customer header with authenticated server-issued identity and authorization. Demo-only behavior is documented. |
| `backend/app/services/order_service.py` | **FAIL for production concurrency** | Add transactional stock reservation/reconciliation before handling concurrent real orders; SQLite row locking is not sufficient. |
| `frontend/src/components/ProductCard.tsx` | **NOT TESTED for persistence** | Save-item control toggles visually but does not persist favorites or provide a saved-items page. No persistence requirement/API exists in this demo. |

## Overall

Local application behavior, endpoint validation, dependency resolution, frontend build, mocked payment safety paths, and browser flows passed after the fixes above. The project is **not fully externally verified or production-ready**: actual Groq calls and all PayPal Sandbox lifecycle steps are blocked by missing credentials; the exact set of 39 changed files cannot be established without Git metadata; authentication and production inventory concurrency remain known gaps.
