export type Product = {
  id: number;
  name: string;
  category: string;
  brand: string;
  description: string;
  price: string;
  stock: number;
  image_url: string;
  specs: Record<string, string>;
  featured: boolean;
  reason?: string;
};

export type CartLine = { product: Product; quantity: number; subtotal: string };
export type Cart = { items: CartLine[]; total: string };
export type Order = {
  id: number;
  status: string;
  payment_status: string;
  currency: string;
  total: string;
  created_at: string;
  items: { product_name: string; unit_price: string; quantity: number }[];
};
export type AgentReply = {
  answer: string;
  mode: "groq" | "fallback";
  tool_calls: { name: string; arguments: Record<string, unknown> }[];
  products: Product[];
};
