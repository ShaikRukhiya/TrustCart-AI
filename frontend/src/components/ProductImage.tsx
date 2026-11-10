import type { Product } from "../types";

const PRODUCT_IMAGES: Record<string, string> = {
  "AeroBook 14": "/products/aerobook-14.jpg",
  "ThinkPad E14 Gen 5": "/products/thinkpad-e14-gen-5.jpg",
  "IdeaPad Slim 5": "/products/ideapad-slim-5.jpg",
  "MacBook Air 13": "/products/macbook-air-13.jpg",
  "VivoBook 15": "/products/vivobook-15.jpg",
  "Pavilion Plus 14": "/products/pavilion-plus-14.jpg",
  "Galaxy S24": "/products/galaxy-s24.jpg",
  "Pixel 8a": "/products/pixel-8a.jpg",
  "iPhone 15": "/products/iphone-15.jpg",
  "Nord 4": "/products/nord-4.jpg",
  "QuietComfort Ultra": "/products/quietcomfort-ultra.jpg",
  "WH-1000XM5": "/products/wh-1000xm5.jpg",
  "AirPods Pro 2": "/products/airpods-pro-2.jpg",
  "Soundcore Space One": "/products/soundcore-space-one.jpg",
  "iPad Air 11": "/products/ipad-air-11.jpg",
  "Galaxy Tab S9 FE": "/products/galaxy-tab-s9-fe.jpg",
  "Kindle Paperwhite": "/products/kindle-paperwhite.jpg",
  "MX Master 3S": "/products/mx-master-3s.jpg",
  "Keychron K2 Pro": "/products/keychron-k2-pro.jpg",
  "Dell UltraSharp 27": "/products/dell-ultrasharp-27.jpg",
  "LG UltraGear 27": "/products/lg-ultragear-27.jpg",
  "Anker 737 Power Bank": "/products/anker-737-power-bank.jpg",
  "EcoFlow River 2": "/products/ecoflow-river-2.jpg",
  "Fitbit Charge 6": "/products/fitbit-charge-6.jpg",
};

const FALLBACK_IMAGE = "/products/product-fallback.svg";

function getImageSource(product: Pick<Product, "name" | "image_url">) {
  const imageUrl = product.image_url.trim();
  if (imageUrl && !/placehold\.co/i.test(imageUrl)) return imageUrl;
  return PRODUCT_IMAGES[product.name] ?? FALLBACK_IMAGE;
}

export default function ProductImage({ product }: { product: Product }) {
  const src = getImageSource(product);

  return (
    <img
      key={src}
      src={src}
      alt={product.name}
      onError={(event) => {
        const image = event.currentTarget;
        if (image.dataset.fallbackApplied) return;
        image.dataset.fallbackApplied = "true";
        image.src = FALLBACK_IMAGE;
      }}
    />
  );
}
