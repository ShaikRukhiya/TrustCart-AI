# TrustCart AI — Final demo readiness

**Reviewed:** 2026-11-10  
**Evidence source:** current implementation, `PROJECT_AUDIT.md`, `README.md`, and `backend/tests/test_api.py`.

Status meanings: **PASS** = verified by a local browser/API check or automated test; **FAIL** = known gap; **BLOCKED** = requires credentials/external service; **NOT TESTED** = not yet verified.

## Readiness summary

- **PASS** — Local catalogue, search, product comparison, fallback recommendations, cart totals/stock validation, API validation, frontend build, and the audited browser flows.
- **BLOCKED** — Live Groq inference/tool calls and all real PayPal Sandbox lifecycle steps. The audit found the Groq and PayPal credential values unset. Do not present fallback answers or mocked payment tests as live integration success.
- **NOT TESTED** — An actual PayPal failed-capture response. The test suite checks checkout without credentials, cancellation, pending-to-completed mocked verification, amount mismatch, and duplicate capture, but does not exercise a PayPal `FAILED` capture response.
- **FAIL for production** — Customer identity is a client-provided demo header; inventory concurrency is not production-safe.

## Features with passing evidence

| Status | Feature | Evidence |
|---|---|---|
| **PASS** | Backend and frontend dependency checks | `python -m pip check`: no broken requirements. `npm ls --depth=0`: top-level dependencies resolve. |
| **PASS** | Backend API tests | `16 passed` in `backend/tests/test_api.py` (one Starlette/httpx deprecation warning). |
| **PASS** | Frontend TypeScript check and production build | `npm run build` succeeds. Vite emits a non-fatal advisory for the 550.02 kB minified charts chunk. |
| **PASS** | API and seeded catalogue | Health, product list/detail, filtering and missing-product behavior tested; 24 seeded demo products displayed in browser. |
| **PASS** | Product search and comparison | Browser search for Sony returns one result; selecting two products renders the comparison panel. |
| **PASS** | Recommendations without Groq | Fallback is clearly labeled `FALLBACK` / “not AI-generated”; browser returned four in-budget laptop results. This is catalogue filtering, not model output. |
| **PASS** | Cart and stock checks | Server total equals product price × quantity; quantity zero removes an item; over-stock returns 409 and negative quantity returns 422. Browser showed $549.00 for one AeroBook and $1,098.00 for two. |
| **PASS** | Validation and customer scoping | Empty chat and invalid quantity return 422; missing products/orders return 404; another demo customer cannot read an order. This is not authentication. |
| **PASS** | Local payment safety checks | Without PayPal credentials, checkout returns 503 and remains unpaid. Mocked tests verify pending is not paid, wrong amount is rejected, and repeating a successful mock capture does not call capture again. No real payment was made. |
| **PASS** | Browser shopping flows | Catalogue, comparison, add-to-cart, quantity update, fallback assistant, checkout warning, save toggle, mobile menu, Orders and Insights were exercised. Browser reported no page/console errors after the alternate-port CORS fix. |
| **PASS** | Alternate Vite port CORS | Live origin `http://127.0.0.1:5174` preflight returns 200; an unrelated external origin returns 400. |

## Features requiring Groq credentials

| Status | Feature | What is and is not verified |
|---|---|---|
| **BLOCKED** | Live Groq response and tool calling | No `GROQ_API_KEY` was configured during the audit. The six-tool execution loop was exercised with a mocked Groq HTTP client against the test catalogue; this does not establish that the real key, model, network, or provider response works. |
| **PASS** | No-key/failure fallback | No-key mode returns a labelled catalogue fallback; a simulated Groq transport failure also returns a labelled fallback. |
| **NOT TESTED** | Live Groq budget/tool accuracy | After setting a valid key, check the response mode and actual tool calls, then verify every recommendation against catalogue prices. Never rely on model prose for price, stock or payment facts. |

### Configure Groq safely

1. Obtain a Groq API key from the Groq account/dashboard over its official HTTPS site. Do not paste it into chat, source code, frontend environment variables, screenshots, or a commit.
2. In a PowerShell terminal:

   ```powershell
   Set-Location 'D:\TrustCart AI\backend'
   if (-not (Test-Path .env)) { Copy-Item .env.example .env }
   notepad .env
   ```

3. Set `GROQ_API_KEY` in `backend\.env`. Keep the configured `GROQ_MODEL` unless you have verified that the account supports the selected model. Do not put the key in `frontend\.env`, `VITE_*`, or browser storage.
4. Save the file, restart the backend, and check `GET http://127.0.0.1:8000/api/health`; `ai_mode` should report `groq`. This confirms configuration detection, not a successful provider request.
5. In the app, ask: **“Find a laptop for Python development under $700 and compare the best options.”** Check that the response shows `GROQ AI`, the products are database products and all are at or below $700. If it shows `FALLBACK`, the real AI call is still unverified/unavailable.
6. If Groq rejects the key/model or is unreachable, use the visible fallback mode and report the live integration as **FAIL** (tested failure) or **NOT TESTED** (no conclusive response)—do not claim a live AI success.

## Features requiring PayPal Sandbox credentials

| Status | Feature | What and why it remains outstanding |
|---|---|---|
| **BLOCKED** | Sandbox OAuth, order creation, approval redirect, capture, and live payment verification | `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET` were unset. No PayPal order, buyer approval, capture, transaction, or real payment verification was made. |
| **PASS** | No-credential behavior | Checkout remains visibly unavailable and returns 503; it does not simulate a payment or mark the order paid. |
| **PASS** | Mocked payment verification paths | Isolated test responses exercise pending/recheck, exact amount/currency validation, wrong-amount rejection and duplicate-capture idempotency. These are unit/API tests—not PayPal Sandbox transactions. |
| **NOT TESTED** | Real cancellation and failed capture | The local pending-order cancellation path is tested with a mocked checkout order. A real Sandbox buyer cancellation and a PayPal `FAILED` capture response have not been tested. |

### Configure PayPal Sandbox safely

1. In the PayPal Developer Dashboard, create/use a **Sandbox REST app** and separate Sandbox **business (merchant)** and **personal (buyer)** accounts. Never use live credentials for this demo.
2. In the backend only, open the ignored local environment file:

   ```powershell
   Set-Location 'D:\TrustCart AI\backend'
   if (-not (Test-Path .env)) { Copy-Item .env.example .env }
   notepad .env
   ```

3. Set `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET` from the Sandbox REST app. Keep `PAYPAL_BASE_URL=https://api-m.sandbox.paypal.com` and `PAYPAL_CURRENCY=USD`. Do not put either credential in frontend code, browser storage, source control, or this report.
4. Set `FRONTEND_ORIGIN` to the exact browser origin printed by Vite (for example `http://localhost:5173` or `http://localhost:5174`). The API accepts local development origins, but PayPal return/cancel URLs use `FRONTEND_ORIGIN`; set it before starting the backend.
5. Save `.env` and restart the backend so settings reload. Check `GET http://127.0.0.1:8000/api/health`; `paypal_sandbox_configured: true` means only that both fields are present—it does **not** prove PayPal authentication works.
6. Use a demo cart and proceed to checkout. Follow the returned PayPal **Sandbox** approval link and sign in with the Sandbox personal buyer account. After PayPal returns to TrustCart, explicitly choose **Confirm and capture payment**.
7. Claim a successful payment only if the UI reports verified payment, the order is `paid` in Orders, and the backend has returned a PayPal transaction/capture ID. If authentication, create, approve, capture, amount/currency verification, or redirect fails, report that exact step as **FAIL**. Never retry using live credentials.

## Exact PowerShell startup commands

Use two separate PowerShell terminals. If credentials are being configured, edit `backend\.env` as above first. From the backend folder, activate the environment and run the documented server command:

```powershell
Set-Location 'D:\TrustCart AI\backend'
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --env-file .env
```

In the second terminal:

```powershell
Set-Location 'D:\TrustCart AI\frontend'
npm run dev
```

Open the exact Local URL Vite prints. It normally uses `http://localhost:5173`; when 5173 is occupied, Vite may choose another port. If using PayPal, make `FRONTEND_ORIGIN` match that URL and restart the backend. The API is at `http://127.0.0.1:8000`; Swagger is at `http://127.0.0.1:8000/docs`.

Optional local checks, in additional terminals:

```powershell
Set-Location 'D:\TrustCart AI\backend'
.\.venv\Scripts\python.exe -m pytest tests -q
```

```powershell
Set-Location 'D:\TrustCart AI\frontend'
npm run build
```

## Five-minute hackathon demo script

This script is safe to run without external credentials. Speak honestly about the mode shown in the UI.

| Time | Demo action and talk track | Status |
|---|---|---|
| **0:00–0:30** | Open the app and introduce it as a shopping assistant over a seeded 24-product catalogue. Point out the service pill. Say **“Catalogue mode”** when Groq is not configured; do not call it live AI. | **PASS** for local page/catalogue; live AI **BLOCKED** without a key. |
| **0:30–1:20** | Choose **Discover**. Search `Sony`, show the WH-1000XM5 result, clear search and select two products with **Compare**. Point out price/spec differences from catalogue data. | **PASS** |
| **1:20–2:10** | Choose **AI assistant** and ask “Find a laptop for Python development under $700.” Identify the `FALLBACK` label if present, and show that displayed matches are actual in-stock catalogue products within budget. If a valid Groq key is configured and the response says `GROQ AI`, explain that mode accurately; claim the live path only after seeing the provider-backed response and tool results. | Fallback **PASS**; live Groq **BLOCKED** until actually verified. |
| **2:10–3:00** | Add the AeroBook 14 from a product card, open **Your cart**, increase quantity from one to two, and show the total changing from $549.00 to $1,098.00. Mention the server rejects quantities above stock. | **PASS** |
| **3:00–4:20** | Open checkout. If PayPal is not configured, show the explicit “isn’t configured” warning and state no payment is simulated; do not imply a purchase. If Sandbox is configured and verified, create the approval order, switch to the Sandbox buyer, approve it, return to TrustCart, explicitly confirm capture, then verify the transaction ID and `paid` order. | Unconfigured warning **PASS**; real order/approval/capture **BLOCKED** until actually completed. |
| **4:20–5:00** | Show **Orders** and **AI insights**. With no verified paid order, explain that insights do not invent spending history. With a completed verified Sandbox order, show the saved order and paid-only insights. Close with the demo-only identity and inventory-concurrency limitations. | Pages **PASS**; real paid-order insight **BLOCKED** until a Sandbox payment succeeds. |

Do not use a mocked transaction in the live demo as proof of PayPal. Do not claim a live Groq response based on the fallback path or the fake-client test.

## Payment test scenarios

All test doubles are isolated; they do not contact PayPal, settle money, or prove the Sandbox integration.

| Scenario | Steps | Current evidence/status |
|---|---|---|
| **Successful payment** | With Sandbox credentials, create an order, approve as the Sandbox buyer, return to TrustCart, explicitly confirm capture, then verify the UI/order status is `paid` and a PayPal capture ID exists. | **BLOCKED** for real Sandbox. Exact-amount completed capture and pending-to-completed verification pass with mocked provider responses. |
| **Cancelled payment** | Create a Sandbox approval order, choose Cancel/Return on the PayPal approval page, and verify TrustCart returns to its cancel route. Confirm the local order becomes `cancelled` and no capture ID/payment is recorded. Do not confuse cancelling before approval with a failed capture. | **NOT TESTED** with a real Sandbox buyer. Pending-unpaid local cancellation passes a mocked API test; cancelling a non-pending/non-unpaid order returns 409. |
| **Failed payment/capture** | Use only a Sandbox order and buyer. If the provider returns a capture response with a failed status, verify the local order becomes `payment_failed`/`failed` and is never shown as paid; preserve the provider error and transaction status for diagnosis. If Sandbox cannot reliably produce this outcome, exercise it only with an isolated fake PayPal response in a test environment and label it mocked. | **NOT TESTED** for a real capture or a `FAILED` provider response in the current suite. Invalid amount is a separate tested rejection: API returns 502 and order remains unpaid. |
| **Duplicate capture** | After one verified successful capture, submit the same capture request again for the same PayPal order. Verify the same stored capture ID/status is returned and no second provider capture, stock decrement, or transaction record is created. | **PASS** with a mocked provider regression test (`test_mocked_completed_capture_is_idempotent`). **BLOCKED** as a real Sandbox duplicate-capture exercise until credentials and a successful Sandbox order exist. |

## Known limitations and remaining UI gaps

| Status | Limitation or gap | Impact |
|---|---|---|
| **FAIL for production** | `X-Customer-Id` is generated/stored by the browser and is not authenticated or server-signed. | Demo session separation only; do not use for real customer accounts/data/payments without adding authentication/authorization. |
| **FAIL for production** | SQLite `with_for_update` is not a robust inventory reservation mechanism; the demo rechecks stock but does not reserve it transactionally across concurrent checkouts. | Concurrent orders can race. Not suitable for production inventory/payment reconciliation. |
| **FAIL / visual-only** | The product-card **Save item** heart changes its appearance using component-local state but does not persist favorites or expose a saved-items collection. | Treat it as a visual demo toggle, not a durable save feature. |
| **NOT TESTED** | Manual mouse/touch interaction across browsers/devices. | Browser automation verified page state and DOM event behavior; its pointer-click helper timed out waiting for stable targets. |
| **PASS with advisory** | Production frontend build. | Build succeeds, but Vite warns the charts chunk is 550.02 kB minified. |
| **NOT TESTED** | Reconciliation for provider disputes/webhooks, refunds, tax/shipping, live payments, and real-user security. | Explicitly out of demo scope; do not imply support. |

## Final status

**PASS** for the locally tested demo flows and existing automated checks. **BLOCKED** for real Groq and PayPal Sandbox until credentials are configured and provider-backed interactions actually succeed. **NOT TESTED** for a real cancelled/failed PayPal outcome. The app remains a hackathon demo, not a production-ready commerce system.
