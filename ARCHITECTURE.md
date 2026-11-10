# TrustCart AI architecture

## Components

```text
React / TypeScript / Vite
  ├─ Home, assistant, catalogue/detail, cart, checkout, orders, insights
  ├─ API client: customer demo ID + typed requests
  └─ Recharts: derived paid-order summary
          │ HTTP/JSON (CORS)
          ▼
FastAPI
  ├─ routers: products, cart, agent, orders/payments
  ├─ services: catalogue/ranking, cart/order, Groq tool loop, PayPal REST
  ├─ Pydantic request/response validation
  └─ SQLAlchemy → SQLite
       ├─ products
       ├─ cart_items
       ├─ orders → order_items
       ├─ payment_transactions
       └─ conversations
```

## Data ownership and flow

- SQLAlchemy is the source of truth for products, stock, cart quantities, order snapshots, payment transaction IDs/statuses and conversation records.
- `Product.specs_json` stores typed-at-the-edge product specification dictionaries. The API response exposes a JSON object, not the database string.
- Product search applies category, keyword and maximum-price filters to catalogue rows. Recommendations rank only in-stock database products and omit every product above the supplied budget.
- Cart quantity writes validate the requested product and current stock. Totals are recalculated from product rows on each read and during order creation.
- Checkout snapshots the then-current catalogue price and product name into an order. PayPal receives the backend-calculated total, not a browser-supplied amount.
- On the return route, a customer action triggers server-side capture. The backend maps the PayPal order to the current demo customer, verifies the returned PayPal order ID and exact amount/currency, then persists transaction and order status. Duplicate capture requests return the persisted successful transaction.
- AI insights derive spend and order counts from persisted orders with `payment_status == "paid"`; no inferred personal budget or synthetic history is presented.

## Agent tools

Groq receives tool schemas and a system instruction restricting factual claims to tool output. The backend executes only:

1. `search_products`
2. `compare_products`
3. `recommend_product`
4. `manage_cart`
5. `get_order_status`
6. `payment_assistance`

The payment-assistance tool reports configuration and describes the flow; it does not create, approve or capture a payment. Payment capture is a separate API operation reached after the customer approves on PayPal and confirms in the UI. Groq responses never serve as price, stock or payment evidence.

When no Groq key is present, the backend performs simple catalogue filtering and labels every answer `Fallback catalogue mode (not AI-generated)`. Groq transport/API errors also return a clearly labeled fallback response. Fallback does not claim model reasoning or execute financial actions.

## External APIs

- **Groq:** OpenAI-compatible chat-completions endpoint with JSON-schema function tools. API key and model are backend configuration.
- **PayPal:** Sandbox OAuth client-credentials token, Orders v2 create, customer approval redirect, and Orders v2 capture/status read. PayPal credentials remain in backend environment variables. Only Sandbox is configured by default.

## Security boundaries and demo assumptions

- Price, stock, cart total, order total, capture status and transaction ID are backend-owned.
- The client cannot mark an order paid. A success URL alone does not affect payment status.
- Product and comparison tools read from the database; unsupported tool names fail instead of being executed.
- A capture must map to the session's local order and match its server-snapshotted amount and currency.
- The browser's `X-Customer-Id` is a random local-storage value, **not an authenticated identity**. This supports an isolated hackathon demo only. A deployment handling real users must replace it with server-issued, authenticated sessions and enforce authorization on every customer-scoped resource.
- API keys must be set in backend `.env` only; `.env` must not be committed.
- SQLite `with_for_update` does not provide production-grade inventory reservation semantics. The demo rechecks stock before capture, but production must introduce transactional inventory reservations and a reconciliation strategy.
