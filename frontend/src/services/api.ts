import type { AgentReply, Cart, Order, Product } from "../types";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api";
const storageKey = "trustcart-customer-id";

function getCustomerId(): string {
  let id = localStorage.getItem(storageKey);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(storageKey, id);
  }
  return id;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-Customer-Id": getCustomerId(),
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  products: (params = "") => request<Product[]>(`/products${params}`),
  product: (id: number) => request<Product>(`/products/${id}`),
  cart: () => request<Cart>("/cart"),
  setCartItem: (product_id: number, quantity: number) =>
    request<Cart>("/cart/items", {
      method: "PUT",
      body: JSON.stringify({ product_id, quantity }),
    }),
  chat: (message: string) =>
    request<AgentReply>("/agent/chat", {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
  orders: () => request<Order[]>("/orders"),
  order: (id: number) => request<Order>(`/orders/${id}`),
  checkout: () =>
    request<{ order_id: number; paypal_order_id: string; approval_url: string; status: string; total: string; currency: string }>(
      "/checkout",
      { method: "POST" },
    ),
  capture: (paypalOrderId: string) =>
    request<{ order_id: number; payment_status: string; paypal_status: string; transaction_id: string | null }>(
      `/payments/${encodeURIComponent(paypalOrderId)}/capture`,
      { method: "POST" },
    ),
  cancelCheckout: (orderId: number) =>
    request<{ order_id: number; status: string; payment_status: string }>(
      `/checkout/${orderId}/cancel`,
      { method: "POST" },
    ),
  health: () =>
    request<{ status: string; ai_mode: string; paypal_sandbox_configured: boolean }>("/health"),
};

export function formatMoney(value: string | number, currency = "USD") {
  return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(Number(value));
}
