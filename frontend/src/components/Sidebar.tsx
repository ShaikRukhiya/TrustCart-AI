import {
  BarChart3, Bot, ChevronLeft, ChevronRight, Home, PackageSearch, ShoppingBag,
} from "lucide-react";

export type Page = "home" | "assistant" | "products" | "cart" | "orders" | "insights" | "detail" | "checkout";

const links: { page: Page; label: string; icon: typeof Home }[] = [
  { page: "home", label: "Overview", icon: Home },
  { page: "assistant", label: "AI assistant", icon: Bot },
  { page: "products", label: "Discover", icon: PackageSearch },
  { page: "cart", label: "Your cart", icon: ShoppingBag },
  { page: "orders", label: "Orders", icon: PackageSearch },
  { page: "insights", label: "AI insights", icon: BarChart3 },
];

export default function Sidebar({
  page, setPage, count, collapsed, setCollapsed, mobileOpen,
}: {
  page: Page; setPage: (page: Page) => void; count: number;
  collapsed: boolean; setCollapsed: (value: boolean) => void;
  mobileOpen: boolean;
}) {
  return (
    <aside className={`sidebar ${collapsed ? "collapsed" : ""} ${mobileOpen ? "mobile-open" : ""}`}>
      <button className="brand-lockup" onClick={() => setPage("home")} aria-label="TrustCart AI home">
        <span className="brand-mark">t<span>.</span></span>
        {!collapsed && <span className="brand-name">trustcart<span>AI</span></span>}
      </button>
      <div className="nav-label">{!collapsed && "WORKSPACE"}</div>
      <nav className="side-nav">
        {links.map(({ page: target, label, icon: Icon }) => (
          <button key={target} className={`nav-link ${page === target ? "active" : ""}`} onClick={() => setPage(target)} title={collapsed ? label : undefined}>
            <Icon size={18} />
            {!collapsed && <span>{label}</span>}
            {!collapsed && target === "cart" && count > 0 && <span className="nav-count">{count}</span>}
          </button>
        ))}
      </nav>
      <div className="sidebar-bottom">
        <div className="trust-card">
          <div className="trust-icon">✓</div>
          {!collapsed && <div><strong>Shop with trust</strong><small>Every choice is yours.</small></div>}
        </div>
        <button className="collapse-button" onClick={() => setCollapsed(!collapsed)} aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}>
          {collapsed ? <ChevronRight size={17} /> : <ChevronLeft size={17} />} {!collapsed && "Collapse"}
        </button>
      </div>
    </aside>
  );
}
