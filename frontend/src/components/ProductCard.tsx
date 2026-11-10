import { ArrowUpRight, Heart, ShoppingBag } from "lucide-react";
import { useState } from "react";
import type { Product } from "../types";
import { formatMoney } from "../services/api";
import ProductImage from "./ProductImage";

type Props = {
  product: Product;
  onAdd: (product: Product) => void;
  onOpen: (product: Product) => void;
  compact?: boolean;
};

export default function ProductCard({ product, onAdd, onOpen, compact = false }: Props) {
  const [saved, setSaved] = useState(false);
  return (
    <article className={`product-card ${compact ? "product-card-compact" : ""}`}>
      <div className="product-image">
        <ProductImage product={product} />
        <span className="product-category">{product.category}</span>
        <button
          className={`save-product ${saved ? "saved" : ""}`}
          onClick={(event) => { event.stopPropagation(); setSaved(!saved); }}
          aria-label={saved ? "Remove from saved items" : "Save item"}
        ><Heart size={16} fill={saved ? "currentColor" : "none"} /></button>
      </div>
      <div className="product-card-body">
        <div className="product-brand">{product.brand}</div>
        <button className="product-name" onClick={() => onOpen(product)}>{product.name}<ArrowUpRight size={15} /></button>
        {!compact && <p className="product-description">{product.description}</p>}
        {product.reason && <p className="product-reason">{product.reason}</p>}
        <div className="product-card-bottom">
          <div>
            <strong>{formatMoney(product.price)}</strong>
            <span className={product.stock > 0 ? "in-stock" : "out-stock"}>
              {product.stock > 0 ? `${product.stock} in stock` : "Out of stock"}
            </span>
          </div>
          <button className="icon-button add-button" disabled={!product.stock} onClick={() => onAdd(product)} aria-label={`Add ${product.name} to cart`}>
            <ShoppingBag size={17} />
          </button>
        </div>
      </div>
    </article>
  );
}
