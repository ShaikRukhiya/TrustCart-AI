# TrustCart AI

TrustCart AI is a demonstration shopping agent that searches a real SQLite catalogue, compares and ranks products, manages a server-validated cart, and offers an approval-first PayPal Sandbox workflow. It is not a generic chatbot: when Groq is configured it can call an allow-listed set of backend tools; without Groq it explicitly identifies itself as catalogue fallback mode.

> **Demo and currency:** the seeded catalogue and PayPal Sandbox default use **USD** so the demo uses a PayPal-supported currency. The example Indian-rupee request in the project brief is not converted; enter a budget in the displayed catalogue currency. Seeded records are demonstration data, not live offers.

## Architecture

- `frontend/`: React, TypeScript, Vite, Tailwind CSS, Lucide icons and Recharts.
- `backend/app/`: FastAPI routes, Pydantic schemas, SQLAlchemy models/services, SQLite and external API clients.
- `backend/tests/`: FastAPI `TestClient` tests using an isolated in-memory SQLite database.
- `ARCHITECTURE.md`: component map, data flow and security boundaries.
- `PROJECT_AUDIT.md`: requirement-by-requirement implementation and verification status.

### Request and payment flow

1. The browser requests products, cart and order data from FastAPI. Browser input never supplies trusted prices.
2. The assistant sends the user prompt to Groq with JSON-schema tools when `GROQ_API_KEY` is configured. FastAPI executes only the defined product, comparison, recommendation, cart, order-status and payment-assistance functions. If Groq is unavailable, the response is clearly labeled **Fallback catalogue mode (not AI-generated)**.
3. Cart and order totals are calculated from SQLAlchemy product rows. Checkout revalidates stock and snapshots product names, unit prices, quantities and the total.
4. The backend creates a PayPal Orders v2 Sandbox order. The customer leaves TrustCart and approves on PayPal. Returning to TrustCart exposes a separate confirmation action; only then does the backend capture.
5. FastAPI verifies the returned PayPal order ID, capture status, currency and exact amount against the persisted order before marking it paid, recording the capture transaction, reducing stock and clearing the cart.

## Requirements

- Python 3.10+ (developed with Python 3.12)
- Node.js 20+ and npm
- Groq API key is optional; fallback search works without it.
- PayPal Sandbox REST app credentials are optional; payments remain disabled until both credentials are configured. No payment is simulated.

## Windows PowerShell setup

Open two PowerShell terminals from the project folder.

### 1. Backend

```powershell
cd "D:\TrustCart AI\backend"
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env and add optional API credentials.
uvicorn app.main:app --reload --env-file .env
```

The API is at `http://localhost:8000`; Swagger docs are at `http://localhost:8000/docs`. On first startup, SQLAlchemy creates `trustcart.db` and seeds 24 demonstration products. Set `DATABASE_URL` to change the database location.

### 2. Frontend

```powershell
cd "D:\TrustCart AI\frontend"
npm install
npm run dev
```

Open the Vite URL (normally `http://localhost:5173`). The frontend calls `http://localhost:8000/api` by default; set `VITE_API_URL` at build time to use another API URL.

If port 5173 is occupied, Vite may select another local port. Localhost/127.0.0.1 development origins are accepted by the API; set `FRONTEND_ORIGIN` in the backend `.env` to the actual Vite URL before using PayPal, because it is also used for PayPal return and cancel URLs.

### Environment variables

| Variable | Required | Purpose |
|---|---:|---|
| `DATABASE_URL` | No | SQLAlchemy URL; defaults to local SQLite |
| `FRONTEND_ORIGIN` | No | Allowed CORS origin and PayPal return/cancel URL origin |
| `GROQ_API_KEY` | No | Groq API key; absent/unavailable uses clearly labeled fallback |
| `GROQ_MODEL` | No | Groq chat model, defaults to `llama-3.3-70b-versatile` |
| `PAYPAL_CLIENT_ID` | For PayPal | PayPal Developer Sandbox REST app client ID |
| `PAYPAL_CLIENT_SECRET` | For PayPal | PayPal Developer Sandbox REST app secret; backend only |
| `PAYPAL_BASE_URL` | No | Defaults to `https://api-m.sandbox.paypal.com` |
| `PAYPAL_CURRENCY` | No | Defaults to `USD`; must match the catalogue's configured currency |

Never put PayPal secrets in `frontend/`, commit `.env`, or use live credentials in this demo.

### PayPal Sandbox setup

1. Sign in to the [PayPal Developer Dashboard](https://developer.paypal.com/dashboard/).
2. Create a Sandbox REST app and use its client ID and secret in the backend `.env`.
3. Create a Sandbox business account and a separate personal test account in the dashboard.
4. Restart the backend. `GET /api/health` should report `paypal_sandbox_configured: true`.
5. Add a product, start checkout, continue to PayPal Sandbox and sign in as the test buyer. Return to TrustCart and explicitly confirm capture.

The integration uses OAuth client credentials, `POST /v2/checkout/orders`, the returned `approve` link, and `POST /v2/checkout/orders/{id}/capture`. The client secret is only read by the backend. See [PayPal Orders v2](https://developer.paypal.com/docs/api/orders/v2/) and [PayPal REST authentication](https://developer.paypal.com/api/rest/requests/).

## API endpoints

All customer-scoped endpoints accept `X-Customer-Id`; the browser creates a persistent random demo-session identifier. **This is a demo identity, not authentication.** Replace it with authenticated server-issued sessions before handling real customer data or payments.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | API, AI mode and PayPal configuration status |
| `GET` | `/api/products?q=&category=&max_price=&featured=` | Search/filter catalogue |
| `GET` | `/api/products/{product_id}` | Product details |
| `GET` | `/api/cart` | Current session cart and server-calculated total |
| `PUT` | `/api/cart/items` | Set quantity (`0` removes); validates stock |
| `POST` | `/api/agent/chat` | Tool-using Groq agent or labeled fallback |
| `POST` | `/api/checkout` | Revalidate cart and create a PayPal approval order |
| `POST` | `/api/payments/{paypal_order_id}/capture` | Capture/verify after PayPal approval |
| `POST` | `/api/checkout/{order_id}/cancel` | Cancel a pending unpaid checkout |
| `GET` | `/api/orders` | Current session order history |
| `GET` | `/api/orders/{order_id}` | Customer-scoped order details |

## Testing

Backend tests:

```powershell
cd "D:\TrustCart AI\backend"
python -m pytest tests -q
```

Frontend production build:

```powershell
cd "D:\TrustCart AI\frontend"
npm run build
```

The payment tests intentionally do not fake a successful PayPal transaction. Without Sandbox credentials, checkout returns a configuration error and an unpaid local record. Complete a real Sandbox buyer approval to verify the external integration end to end.

## Demo walkthrough

1. Start the API and frontend; browse the featured demonstration catalogue.
2. Ask the assistant for an item and budget (use USD, the demo currency). If Groq is not configured, check the visible fallback label.
3. Open a product, add it to the cart, and change/remove quantities.
4. With PayPal Sandbox credentials configured, create an approval order, approve it with a Sandbox buyer, then confirm capture after returning.
5. Review the persisted order and verified spending insights. Without credentials, the checkout stays visibly unavailable rather than showing a fake payment.

## Known limitations

- The customer header is an untrusted demo-session identifier. There is no login, signed session, production authorization, CSRF protection, or account recovery.
- Product and payment amounts use USD by default. There is no exchange-rate conversion, tax, shipping, refund, dispute, webhook or live-payment implementation.
- Groq and PayPal external calls require credentials/network and are not exercised by the automated suite. PayPal `PENDING` captures are recorded and rechecked from PayPal on a later capture-status request; webhook-based reconciliation is not included.
- SQLite initialization uses `create_all`; production schema migrations, concurrency-safe inventory reservations, rate limits, audit retention and deployment hardening are out of scope.
- Product images use placeholder URLs; catalogue entries and stock are illustrative.
