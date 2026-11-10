import {
  ArrowDownRight, ArrowRight, ArrowUpRight, BadgeCheck, Bot, Check,
  ChevronDown, CircleHelp, CreditCard, ExternalLink, Headphones,
  Laptop, LoaderCircle, Menu, MessageCircle, Package, Search, ShieldCheck,
  Sparkles, X,
} from "lucide-react";
import { FormEvent, lazy, Suspense, useCallback, useEffect, useMemo, useState } from "react";
import ProductCard from "./components/ProductCard";
import ProductImage from "./components/ProductImage";
import Sidebar, { type Page } from "./components/Sidebar";
import { api, formatMoney } from "./services/api";
import type { AgentReply, Cart, Order, Product } from "./types";

const SpendingChart = lazy(() => import("./components/SpendingChart"));

type ChatMessage = { role: "user" | "assistant"; text: string; reply?: AgentReply };

function App() {
  const [page, setPageState] = useState<Page>("home");
  const [products, setProducts] = useState<Product[]>([]);
  const [cart, setCart] = useState<Cart>({ items: [], total: "0" });
  const [orders, setOrders] = useState<Order[]>([]);
  const [health, setHealth] = useState<{ ai_mode: string; paypal_sandbox_configured: boolean } | null>(null);
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [compareIds, setCompareIds] = useState<number[]>([]);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatDraft, setChatDraft] = useState("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [checkout, setCheckout] = useState<{
    order_id: number; paypal_order_id: string; approval_url: string; total: string; currency: string;
  } | null>(null);
  const [paymentMessage, setPaymentMessage] = useState("");
  const [captureDone, setCaptureDone] = useState(false);
  const [paying, setPaying] = useState(false);

  const navigate = useCallback((target: Page) => {
    setPageState(target);
    setMobileOpen(false);
    setError("");
    if (target === "checkout") setCheckout(null);
  }, []);

  const refreshCart = useCallback(async () => setCart(await api.cart()), []);
  const refreshOrders = useCallback(async () => {
    setOrders(await api.orders());
  }, []);

  useEffect(() => {
    let active = true;
    Promise.all([api.products(), api.cart(), api.orders(), api.health()])
      .then(([catalogue, currentCart, currentOrders, serviceHealth]) => {
        if (!active) return;
        setProducts(catalogue);
        setCart(currentCart);
        setOrders(currentOrders);
        setHealth(serviceHealth);
      })
      .catch((cause: Error) => { if (active) setError(cause.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (window.location.pathname === "/checkout/return") {
      setPageState("checkout");
      const token = params.get("token");
      const orderId = Number(params.get("order_id"));
      if (token && Number.isInteger(orderId) && orderId > 0) {
        setCheckout({ order_id: orderId, paypal_order_id: token, approval_url: "", total: "", currency: "USD" });
        api.order(orderId)
          .then((order) => setCheckout((current) => current && ({ ...current, total: order.total, currency: order.currency })))
          .catch((cause: Error) => setError(cause.message));
      } else setError("PayPal return is missing a valid order reference.");
    } else if (window.location.pathname === "/checkout/cancel") {
      setPageState("checkout");
      const orderId = Number(params.get("order_id"));
      if (orderId) {
        api.cancelCheckout(orderId)
          .then(() => setPaymentMessage("Checkout cancelled. No payment was captured."))
          .catch((cause: Error) => setPaymentMessage(cause.message));
      } else setPaymentMessage("Checkout cancelled. No payment was captured.");
    }
  }, []);

  const notify = (message: string) => {
    setToast(message);
    window.setTimeout(() => setToast(""), 2600);
  };

  const addToCart = async (product: Product) => {
    try {
      const existing = cart.items.find((line) => line.product.id === product.id)?.quantity ?? 0;
      setCart(await api.setCartItem(product.id, existing + 1));
      notify(`${product.name} added to your cart`);
    } catch (cause) {
      setError((cause as Error).message);
    }
  };

  const updateQuantity = async (productId: number, quantity: number) => {
    try { setCart(await api.setCartItem(productId, quantity)); }
    catch (cause) { setError((cause as Error).message); }
  };

  const submitChat = async (event?: FormEvent, message?: string) => {
    event?.preventDefault();
    const prompt = (message ?? chatDraft).trim();
    if (!prompt || working) return;
    setChatDraft("");
    setChatMessages((current) => [...current, { role: "user", text: prompt }]);
    setWorking(true);
    setError("");
    try {
      const reply = await api.chat(prompt);
      setChatMessages((current) => [...current, { role: "assistant", text: reply.answer, reply }]);
      await refreshCart();
    } catch (cause) {
      setChatMessages((current) => [...current, { role: "assistant", text: `I couldn't complete that request: ${(cause as Error).message}` }]);
    } finally { setWorking(false); }
  };

  const openProduct = async (product: Product) => {
    try { setSelectedProduct(await api.product(product.id)); }
    catch { setSelectedProduct(product); }
    navigate("detail");
  };

  const startCheckout = async () => {
    setWorking(true);
    setError("");
    try {
      const result = await api.checkout();
      setCheckout(result);
      setPaymentMessage("");
    } catch (cause) { setError((cause as Error).message); }
    finally { setWorking(false); }
  };

  const capturePayment = async () => {
    if (!checkout || paying) return;
    setPaying(true);
    setError("");
    try {
      const result = await api.capture(checkout.paypal_order_id);
      setCaptureDone(result.payment_status === "paid");
      setPaymentMessage(
        result.payment_status === "paid"
          ? `Payment verified. PayPal transaction ${result.transaction_id ?? "confirmed"}.`
          : `PayPal reports ${result.paypal_status.toLowerCase()}; payment has not been marked paid.`,
      );
      await Promise.all([refreshCart(), refreshOrders()]);
    } catch (cause) { setError((cause as Error).message); }
    finally { setPaying(false); }
  };

  const filteredProducts = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return products;
    return products.filter((product) =>
      `${product.name} ${product.brand} ${product.category} ${product.description}`.toLowerCase().includes(term),
    );
  }, [products, search]);

  const cartCount = cart.items.reduce((sum, item) => sum + item.quantity, 0);

  return (
    <div className="app-shell">
      <Sidebar page={page} setPage={navigate} count={cartCount} collapsed={collapsed} setCollapsed={setCollapsed} mobileOpen={mobileOpen} />
      <main className="main-shell">
        <header className="topbar">
          <div className="breadcrumb"><span>Workspace</span><span className="crumb-slash">/</span><strong>{pageTitle(page)}</strong></div>
          <div className="topbar-right">
            <span className={`service-pill ${health?.ai_mode === "groq" ? "live" : "fallback"}`}>
              <span className="status-dot" />{health?.ai_mode === "groq" ? "AI agent live" : "Catalogue mode"}
            </span>
            <span className="avatar" aria-hidden="true">TC</span>
          </div>
        </header>
        {error && <div className="global-error" role="alert"><CircleHelp size={17} />{error}<button onClick={() => setError("")} aria-label="Dismiss error"><X size={15} /></button></div>}
        <div className="page-content">
          {loading ? <LoadingState /> : (
            <>
              {page === "home" && <HomePage products={products} onAdd={addToCart} onOpen={openProduct} onNavigate={navigate} onAsk={submitChat} search={search} setSearch={setSearch} />}
              {page === "assistant" && (
                <AssistantPage messages={chatMessages} draft={chatDraft} setDraft={setChatDraft} working={working} onSubmit={submitChat} onAdd={addToCart} onOpen={openProduct} onNavigate={navigate} />
              )}
              {page === "products" && (
                <ProductsPage products={filteredProducts} search={search} setSearch={setSearch} onAdd={addToCart} onOpen={openProduct} compareIds={compareIds} setCompareIds={setCompareIds} />
              )}
              {page === "detail" && selectedProduct && <DetailPage product={selectedProduct} onAdd={addToCart} onBack={() => navigate("products")} />}
              {page === "detail" && !selectedProduct && <EmptyState title="Product not found" detail="Choose a product from the catalogue." action="Browse products" onAction={() => navigate("products")} />}
              {page === "cart" && <CartPage cart={cart} onQuantity={updateQuantity} onCheckout={() => navigate("checkout")} onBrowse={() => navigate("products")} onOpen={openProduct} />}
              {page === "checkout" && (
                <CheckoutPage
                  cart={cart} checkout={checkout} paypalConfigured={health?.paypal_sandbox_configured ?? false}
                  paymentMessage={paymentMessage} captureDone={captureDone} paying={paying} working={working}
                  onStart={startCheckout} onApprove={capturePayment} onContinue={() => checkout?.approval_url && window.location.assign(checkout.approval_url)}
                  onOrders={() => { navigate("orders"); refreshOrders(); }}
                />
              )}
              {page === "orders" && <OrdersPage orders={orders} onRefresh={refreshOrders} />}
              {page === "insights" && <InsightsPage orders={orders} />}
            </>
          )}
        </div>
      </main>
      {toast && <div className="toast"><Check size={17} />{toast}</div>}
      <button className="mobile-menu" onClick={() => setMobileOpen(!mobileOpen)} aria-label="Toggle menu"><Menu size={20} /></button>
    </div>
  );
}

function pageTitle(page: Page) {
  return ({ home: "Overview", assistant: "AI shopping assistant", products: "Discover products", cart: "Your cart", orders: "My orders", insights: "AI insights", detail: "Product details", checkout: "Secure checkout" })[page];
}

function LoadingState() {
  return <div className="loading-state"><LoaderCircle className="spin" size={26} /><span>Connecting to your catalogue…</span></div>;
}

function HomePage({
  products, onAdd, onOpen, onNavigate, onAsk, search, setSearch,
}: {
  products: Product[]; onAdd: (product: Product) => void; onOpen: (product: Product) => void;
  onNavigate: (page: Page) => void; onAsk: (event?: FormEvent, message?: string) => void;
  search: string; setSearch: (value: string) => void;
}) {
  const featured = products.filter((product) => product.featured).slice(0, 4);
  return (
    <>
      <div className="welcome-row">
        <div><p className="eyebrow">MONDAY, YOUR WAY</p><h1>Good shopping starts<br />with <span>good questions.</span></h1>
          <p className="welcome-copy">Tell your personal shopping agent what matters. It compares real products, explains the trade-offs, and leaves every decision in your hands.</p></div>
        <div className="welcome-stats"><div><span>DEMO CATALOGUE</span><strong>{products.length}<small> products</small></strong></div><div><span>PAYMENT</span><strong>Approval-first</strong><small>PayPal Sandbox</small></div></div>
      </div>
      <section className="prompt-panel">
        <div className="prompt-heading"><div className="ai-orb"><Sparkles size={18} /></div><div><strong>What are you shopping for?</strong><span>Be specific. Your agent works with live catalogue data.</span></div><span className="secure-label"><ShieldCheck size={14} /> Your choice, always</span></div>
        <form className="prompt-form" onSubmit={(event) => { event.preventDefault(); onAsk(undefined, search); setSearch(""); onNavigate("assistant"); }}>
          <Search size={19} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="e.g. A light laptop for coding under $700" aria-label="Describe what you need" />
          <button type="submit" className="button-primary">Ask TrustCart <ArrowRight size={16} /></button>
        </form>
        <div className="prompt-suggestions"><span>TRY</span>{["Laptop for programming", "Noise-cancelling headphones", "Tablet for college"].map((item) => <button key={item} onClick={() => { onNavigate("assistant"); onAsk(undefined, item); }}>{item}<ArrowUpRight size={13} /></button>)}</div>
      </section>
      <div className="section-heading"><div><p className="eyebrow">CURATED FOR YOU</p><h2>Popular picks</h2></div><button className="text-button" onClick={() => onNavigate("products")}>Explore catalogue <ArrowRight size={16} /></button></div>
      {featured.length ? <div className="product-grid">{featured.map((product) => <ProductCard key={product.id} product={product} onAdd={onAdd} onOpen={onOpen} />)}</div> : <EmptyState title="Catalogue is empty" detail="Start the backend to load demonstration products." />}
      <section className="how-section">
        <div><p className="eyebrow">A BETTER WAY TO BUY</p><h2>Confidence at every step.</h2><p className="muted-copy">No black boxes. No surprise purchases. Just a helpful assistant that puts you in control.</p></div>
        <div className="how-steps">
          <div><span className="step-number">01</span><div className="step-icon"><MessageCircle size={18} /></div><strong>Tell us what matters</strong><p>Share your budget, needs and preferences in plain language.</p></div>
          <div><span className="step-number">02</span><div className="step-icon"><BadgeCheck size={18} /></div><strong>Compare with clarity</strong><p>Explore real catalogue options and understand the trade-offs.</p></div>
          <div><span className="step-number">03</span><div className="step-icon"><CreditCard size={18} /></div><strong>Approve every payment</strong><p>Review your cart and authorize checkout directly with PayPal.</p></div>
        </div>
      </section>
    </>
  );
}

function AssistantPage({
  messages, draft, setDraft, working, onSubmit, onAdd, onOpen, onNavigate,
}: {
  messages: ChatMessage[]; draft: string; setDraft: (value: string) => void; working: boolean;
  onSubmit: (event?: FormEvent, message?: string) => void; onAdd: (product: Product) => void;
  onOpen: (product: Product) => void; onNavigate: (page: Page) => void;
}) {
  return (
    <div className="assistant-layout">
      <section className="assistant-main">
        <div className="page-title-row"><div><p className="eyebrow">YOUR PERSONAL SHOPPING AGENT</p><h1>Let's find your fit.</h1></div><span className="live-tag"><span className="status-dot" /> Backend tools connected</span></div>
        {messages.length === 0 ? (
          <div className="assistant-empty">
            <div className="assistant-illustration"><div className="assistant-ring"><Bot size={34} /></div><span className="sparkle s-one">✦</span><span className="sparkle s-two">✧</span></div>
            <h2>What would you love to find?</h2><p>Share the details that matter and I’ll search the live catalogue for a good match.</p>
            <div className="starter-grid">{[
              { icon: <Laptop size={17} />, text: "Laptop for development under $700" },
              { icon: <Headphones size={17} />, text: "Over-ear headphones for travel" },
              { icon: <Package size={17} />, text: "Compare two tablets for note-taking" },
            ].map(({ icon, text }) => <button key={text} onClick={() => onSubmit(undefined, text)}><span>{icon}</span>{text}<ArrowUpRight size={15} /></button>)}</div>
          </div>
        ) : (
          <div className="chat-log">
            {messages.map((message, index) => (
              <div key={`${message.role}-${index}`} className={`chat-message ${message.role}`}>
                <div className="chat-avatar">{message.role === "assistant" ? <Sparkles size={16} /> : "You"}</div>
                <div className="chat-content"><div className="chat-speaker">{message.role === "assistant" ? "TrustCart AI" : "You"}{message.role === "assistant" && message.reply && <span className={`mode-tag ${message.reply.mode}`}>{message.reply.mode === "groq" ? "GROQ AI" : "FALLBACK"}</span>}</div><p>{message.text}</p>
                  {message.reply?.products?.length ? <div className="recommendation-grid">{message.reply.products.slice(0, 4).map((product) => <ProductCard key={product.id} product={product} compact onAdd={onAdd} onOpen={onOpen} />)}</div> : null}
                </div>
              </div>
            ))}
            {working && <div className="thinking"><LoaderCircle size={16} className="spin" />Checking the live catalogue…</div>}
          </div>
        )}
        <form className="chat-composer" onSubmit={(event) => onSubmit(event)}>
          <textarea value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); onSubmit(); } }} placeholder="Tell me what you're looking for…" rows={2} />
          <div><span><ShieldCheck size={14} /> No purchase without your approval</span><button className="button-primary" disabled={working || !draft.trim()}>Send <ArrowRight size={16} /></button></div>
        </form>
      </section>
      <aside className="assistant-aside">
        <div className="aside-card agent-card"><div className="aside-icon"><Bot size={18} /></div><h3>Your agent, your rules.</h3><p>Recommendations use catalogue records, not made-up prices or availability. Payment approval always stays with you.</p><div className="capability"><Check size={14} /> Live product search</div><div className="capability"><Check size={14} /> Budget-aware ranking</div><div className="capability"><Check size={14} /> No autonomous payments</div></div>
        <div className="aside-card"><div className="aside-title"><span>QUICK ACTION</span><ChevronDown size={16} /></div><button className="aside-action" onClick={() => onNavigate("cart")}><ShoppingBagIcon />Review your cart<ArrowRight size={15} /></button><button className="aside-action" onClick={() => onNavigate("orders")}><Package size={17} />Track an order<ArrowRight size={15} /></button></div>
        <div className="privacy-note"><ShieldCheck size={16} /><span>Your chat helps personalize this session. We never share your payment credentials with the AI.</span></div>
      </aside>
    </div>
  );
}

function ShoppingBagIcon() {
  return <CreditCard size={17} />;
}

function ProductsPage({
  products, search, setSearch, onAdd, onOpen, compareIds, setCompareIds,
}: {
  products: Product[]; search: string; setSearch: (value: string) => void;
  onAdd: (product: Product) => void; onOpen: (product: Product) => void;
  compareIds: number[]; setCompareIds: (ids: number[]) => void;
}) {
  const compared = products.filter((product) => compareIds.includes(product.id));
  return (
    <>
      <div className="page-title-row"><div><p className="eyebrow">THE DEMONSTRATION CATALOGUE</p><h1>Discover something good.</h1><p className="muted-copy">Real seeded product records. Clear specs. No hidden ranking.</p></div><span className="catalogue-count">{products.length} items</span></div>
      <div className="catalogue-toolbar"><div className="catalogue-search"><Search size={18} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search products, brands, categories…" /></div><span>Showing in-stock products</span></div>
      {products.length ? <div className="product-grid">{products.map((product) => <div key={product.id} className="product-wrapper">{productActionsLocal(product, onAdd, onOpen)}<button className={`compare-toggle ${compareIds.includes(product.id) ? "selected" : ""}`} onClick={() => setCompareIds(compareIds.includes(product.id) ? compareIds.filter((id) => id !== product.id) : compareIds.length < 4 ? [...compareIds, product.id] : compareIds)}>{compareIds.includes(product.id) ? <Check size={14} /> : <ChevronDown size={14} />} Compare</button></div>)}</div> : <EmptyState title="No products match" detail="Try another search or clear the search box." action="Clear search" onAction={() => setSearch("")} />}
      {compared.length > 0 && <section className="comparison-panel"><div className="comparison-heading"><div><p className="eyebrow">SIDE BY SIDE</p><h2>Compare picks <span>{compared.length}/4</span></h2></div><button className="plain-button" onClick={() => setCompareIds([])}>Clear</button></div><div className="comparison-table"><div className="comparison-row comparison-head"><span>Product</span>{compared.map((product) => <strong key={product.id}>{product.name}</strong>)}</div>{["price", ...new Set(compared.flatMap((product) => Object.keys(product.specs)))].map((key) => <div key={key} className="comparison-row"><span>{key === "price" ? "Price" : key.replaceAll("_", " ")}</span>{compared.map((product) => <span key={product.id}>{key === "price" ? formatMoney(product.price) : product.specs[key] ?? "—"}</span>)}</div>)}</div></section>}
    </>
  );
}

function productActionsLocal(product: Product, onAdd: (product: Product) => void, onOpen: (product: Product) => void) {
  return <ProductCard product={product} onAdd={onAdd} onOpen={onOpen} />;
}

function DetailPage({ product, onAdd, onBack }: { product: Product; onAdd: (product: Product) => void; onBack: () => void }) {
  return (
    <div className="detail-layout"><button className="text-button back-link" onClick={onBack}><ArrowRight className="back-arrow" size={15} />Back to catalogue</button>
      <div className="detail-grid"><div className="detail-image"><ProductImage product={product} /><span className="product-category">{product.category}</span></div>
        <div className="detail-copy"><p className="eyebrow">{product.brand.toUpperCase()} · DEMONSTRATION CATALOGUE</p><h1>{product.name}</h1><p>{product.description}</p><div className="detail-price">{formatMoney(product.price)} <span>· {product.stock} in stock</span></div><div className="detail-specs"><h3>Specifications</h3>{Object.entries(product.specs).map(([key, value]) => <div key={key}><span>{key.replaceAll("_", " ")}</span><strong>{value}</strong></div>)}</div><button className="button-primary detail-add" disabled={!product.stock} onClick={() => onAdd(product)}><CreditCard size={17} />Add to cart</button><div className="secure-note"><ShieldCheck size={16} />You’ll review and approve payment before checkout.</div></div>
      </div>
    </div>
  );
}

function CartPage({ cart, onQuantity, onCheckout, onBrowse, onOpen }: {
  cart: Cart; onQuantity: (id: number, quantity: number) => void; onCheckout: () => void;
  onBrowse: () => void; onOpen: (product: Product) => void;
}) {
  return (
    <><div className="page-title-row"><div><p className="eyebrow">YOUR SHORTLIST</p><h1>Shopping cart</h1><p className="muted-copy">Nothing is purchased until you approve it at checkout.</p></div></div>
      {!cart.items.length ? <EmptyState title="Your cart is waiting" detail="Add a product from Discover or ask the assistant for ideas." action="Browse products" onAction={onBrowse} /> : <div className="cart-layout"><div className="cart-lines">{cart.items.map(({ product, quantity, subtotal }) => <div className="cart-line" key={product.id}><button className="cart-thumb" onClick={() => onOpen(product)} aria-label={`View ${product.name}`}><ProductImage product={product} /></button><div className="cart-product"><strong>{product.name}</strong><span>{product.brand} · {formatMoney(product.price)}</span><div className="quantity-control"><button onClick={() => onQuantity(product.id, quantity - 1)} aria-label="Decrease quantity">−</button><span>{quantity}</span><button onClick={() => onQuantity(product.id, quantity + 1)} aria-label="Increase quantity">+</button></div></div><div className="cart-line-price"><strong>{formatMoney(subtotal)}</strong><button onClick={() => onQuantity(product.id, 0)}>Remove</button></div></div>)}</div>
      <aside className="order-summary"><p className="eyebrow">ORDER SUMMARY</p><h3>Ready when you are.</h3><div className="summary-row"><span>Items ({cart.items.reduce((sum, item) => sum + item.quantity, 0)})</span><strong>{formatMoney(cart.total)}</strong></div><div className="summary-row"><span>Shipping</span><span>Calculated at checkout</span></div><div className="summary-total"><span>Subtotal</span><strong>{formatMoney(cart.total)}</strong></div><button className="button-primary checkout-button" onClick={onCheckout}>Continue to checkout <ArrowRight size={16} /></button><div className="summary-safe"><ShieldCheck size={16} /><span>Server-verified totals<br />PayPal Sandbox approval required</span></div></aside></div>}
    </>
  );
}

function CheckoutPage({
  cart, checkout, paypalConfigured, paymentMessage, captureDone, paying, working,
  onStart, onApprove, onContinue, onOrders,
}: {
  cart: Cart; checkout: { order_id: number; paypal_order_id: string; approval_url: string; total: string; currency: string } | null;
  paypalConfigured: boolean; paymentMessage: string; captureDone: boolean; paying: boolean; working: boolean;
  onStart: () => void; onApprove: () => void; onContinue: () => void; onOrders: () => void;
}) {
  const returning = window.location.pathname === "/checkout/return";
  return <div className="checkout-page"><div className="page-title-row"><div><p className="eyebrow">SECURE CHECKOUT</p><h1>{returning ? "PayPal approval received." : "One last look."}</h1><p className="muted-copy">Your payment is never captured without your approval.</p></div><span className="secure-checkout-label"><ShieldCheck size={16} /> Secure Sandbox flow</span></div>
    <div className="checkout-layout"><div className="checkout-card"><div className="checkout-step"><span className="step-check"><Check size={15} /></span><div><strong>Review your order</strong><small>Prices are recalculated by the server from the catalogue.</small></div></div>
      {checkout ? <div className="checkout-order-line"><span>Order #{checkout.order_id}</span><strong>{checkout.total ? formatMoney(checkout.total, checkout.currency) : "Amount verified by server"}</strong></div> : cart.items.length ? cart.items.map((item) => <div className="checkout-order-line" key={item.product.id}><span>{item.product.name} × {item.quantity}</span><strong>{formatMoney(item.subtotal)}</strong></div>) : <div className="checkout-order-line"><span>Cart total</span><strong>{formatMoney(cart.total)}</strong></div>}
      <div className="checkout-step second"><span className={checkout ? "step-check" : "step-number-icon"}>{checkout ? <Check size={15} /> : "2"}</span><div><strong>Approve with PayPal</strong><small>You’ll review the final amount on PayPal Sandbox.</small></div></div>
      {!paypalConfigured && !returning && !checkout && <div className="config-warning"><CircleHelp size={18} /><span>PayPal Sandbox isn’t configured. Add your Sandbox client ID and secret to the backend environment to enable checkout. No simulated payment is available.</span></div>}
      {paymentMessage && <div className={`payment-result ${captureDone ? "success" : ""}`}>{captureDone && <BadgeCheck size={18} />}{paymentMessage}</div>}
      {checkout?.approval_url && <button className="button-primary checkout-button" onClick={onContinue}><ExternalLink size={16} />Continue to PayPal Sandbox</button>}
      {checkout && returning && !captureDone && <button className="button-primary checkout-button" disabled={paying} onClick={onApprove}>{paying ? <LoaderCircle size={16} className="spin" /> : <ShieldCheck size={16} />}Confirm and capture payment</button>}
      {captureDone && <button className="button-primary checkout-button" onClick={onOrders}>View my orders <ArrowRight size={16} /></button>}
      {!checkout && paypalConfigured && <button className="button-primary checkout-button" disabled={working || cart.items.length === 0} onClick={onStart}>{working ? <LoaderCircle size={16} className="spin" /> : <ShieldCheck size={16} />}Create PayPal approval order</button>}
      <p className="checkout-footnote"><ShieldCheck size={14} /> PayPal credentials are kept on the backend. The AI cannot approve or capture a payment.</p>
    </div><aside className="checkout-aside"><div className="checkout-aside-icon"><ShieldCheck size={22} /></div><h3>Trust is built in.</h3><p>TrustCart sends your cart total to our backend, which verifies catalogue pricing before creating a PayPal Sandbox order.</p><div><Check size={15} />Explicit approval</div><div><Check size={15} />Server-side capture verification</div><div><Check size={15} />Transaction history</div></aside></div></div>;
}

function OrdersPage({ orders, onRefresh }: { orders: Order[]; onRefresh: () => Promise<void> }) {
  useEffect(() => { onRefresh().catch(() => undefined); }, [onRefresh]);
  return <><div className="page-title-row"><div><p className="eyebrow">YOUR PURCHASE HISTORY</p><h1>My orders</h1><p className="muted-copy">Live status from your TrustCart order records.</p></div><button className="plain-button" onClick={onRefresh}>Refresh</button></div>
    {!orders.length ? <EmptyState title="No orders yet" detail="Your order and payment history will appear here after checkout." /> : <div className="orders-list">{orders.map((order) => <article className="order-card" key={order.id}><div className="order-top"><div><span className="order-id">ORDER #{order.id}</span><span className="order-date">{new Date(order.created_at).toLocaleDateString()}</span></div><span className={`order-status ${order.payment_status}`}>{order.payment_status.replaceAll("_", " ")}</span></div><div className="order-items">{order.items.map((item, index) => <div key={`${item.product_name}-${index}`}><span>{item.product_name} <small>× {item.quantity}</small></span><strong>{formatMoney(Number(item.unit_price) * item.quantity, order.currency)}</strong></div>)}</div><div className="order-bottom"><span>Order status: {order.status.replaceAll("_", " ")}</span><strong>{formatMoney(order.total, order.currency)}</strong></div></article>)}</div>}
  </>;
}

function InsightsPage({ orders }: { orders: Order[] }) {
  const paid = orders.filter((order) => order.payment_status === "paid");
  const total = paid.reduce((sum, order) => sum + Number(order.total), 0);
  const chartData = paid.reduce<{ month: string; amount: number }[]>((data, order) => {
    const month = new Date(order.created_at).toLocaleDateString(undefined, { month: "short", year: "2-digit" });
    const found = data.find((item) => item.month === month);
    if (found) found.amount += Number(order.total);
    else data.push({ month, amount: Number(order.total) });
    return data;
  }, []).slice(-6);
  const mostOrdered = Object.entries(paid.flatMap((order) => order.items).reduce<Record<string, number>>((acc, item) => {
    acc[item.product_name] = (acc[item.product_name] ?? 0) + item.quantity;
    return acc;
  }, {})).sort((a, b) => b[1] - a[1])[0];
  return <><div className="page-title-row"><div><p className="eyebrow">PERSONAL SHOPPING SNAPSHOT</p><h1>Insights that make sense.</h1><p className="muted-copy">Built from your verified order history only — no guessed activity.</p></div></div>
    <div className="insight-metrics"><div><span>VERIFIED SPEND</span><strong>{formatMoney(total)}</strong><small>Across {paid.length} paid orders</small></div><div><span>ORDERS PLACED</span><strong>{orders.length}</strong><small>{orders.filter((order) => order.payment_status !== "paid").length} awaiting payment / other</small></div><div><span>MOST ORDERED</span><strong className="metric-item">{mostOrdered?.[0] ?? "—"}</strong><small>{mostOrdered ? `${mostOrdered[1]} unit(s) in paid orders` : "No paid order data yet"}</small></div></div>
    <section className="chart-card"><div className="chart-heading"><div><p className="eyebrow">SPENDING HISTORY</p><h2>Your spending over time</h2></div><span><span className="chart-dot" /> Paid orders only</span></div>
      {chartData.length ? <Suspense fallback={<div className="chart-container">Loading spending chart…</div>}><SpendingChart data={chartData} /></Suspense> : <div className="chart-empty"><div><ArrowDownRight size={19} /></div><strong>Your spending story starts here.</strong><p>Verified purchases will appear in this chart after a completed PayPal Sandbox checkout.</p></div>}
    </section>
    <div className="insight-note"><Sparkles size={17} /><span><strong>Budget-aware by design.</strong> The shopping assistant can prioritize products under a budget you choose. This page summarizes recorded orders; it does not infer a personal budget.</span></div>
  </>;
}

function EmptyState({ title, detail, action, onAction }: { title: string; detail: string; action?: string; onAction?: () => void }) {
  return <div className="empty-state"><div><Package size={21} /></div><strong>{title}</strong><p>{detail}</p>{action && onAction && <button className="button-secondary" onClick={onAction}>{action}<ArrowRight size={15} /></button>}</div>;
}

export default App;
