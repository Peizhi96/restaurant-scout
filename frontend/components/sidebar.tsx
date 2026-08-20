import Link from "next/link";

const links = [
  { href: "/dashboard", label: "Overview", mark: "O" },
  { href: "/listings", label: "All listings", mark: "L" },
  { href: "/external-leads", label: "External leads", mark: "E" },
];

export function Sidebar() {
  return (
    <aside className="sidebar">
      <Link className="brand" href="/dashboard" aria-label="Restaurant Scout home">
        <span className="brand-mark">RS</span>
        <span>
          <strong>Restaurant Scout</strong>
          <small>Acquisition intelligence</small>
        </span>
      </Link>
      <nav aria-label="Primary navigation">
        <p className="nav-label">Workspace</p>
        {links.map((link) => (
          <Link href={link.href} key={link.href} className="nav-link">
            <span className="nav-mark">{link.mark}</span>
            {link.label}
          </Link>
        ))}
      </nav>
      <div className="sidebar-foot">
        <span className="live-dot" />
        Daily collection active
      </div>
    </aside>
  );
}
