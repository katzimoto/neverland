import { Link } from "@tanstack/react-router";
import { Search, MessageSquare, Bell, History, Bookmark, Settings, Shield } from "lucide-react";
import styles from "./NavRail.module.css";

interface NavItem {
  to: string;
  label: string;
  icon: React.ReactNode;
  adminOnly?: boolean;
}

const NAV_ITEMS: NavItem[] = [
  { to: "/search", label: "Search", icon: <Search size={20} /> },
  { to: "/qa", label: "Q&A", icon: <MessageSquare size={20} /> },
  { to: "/subscriptions", label: "Subscriptions", icon: <Bookmark size={20} /> },
  { to: "/notifications", label: "Notifications", icon: <Bell size={20} /> },
  { to: "/history", label: "History", icon: <History size={20} /> },
];

const ADMIN_ITEM: NavItem = {
  to: "/admin",
  label: "Admin",
  icon: <Shield size={20} />,
  adminOnly: true,
};

interface NavRailProps {
  isAdmin: boolean;
  unreadCount?: number;
}

export function NavRail({ isAdmin, unreadCount = 0 }: NavRailProps) {
  const items = isAdmin ? [...NAV_ITEMS, ADMIN_ITEM] : NAV_ITEMS;

  return (
    <nav className={styles.rail} aria-label="Primary navigation">
      <div className={styles.mark} aria-label="Neverland">N</div>
      <ul className={styles.list} role="list">
        {items.map((item) => (
          <li key={item.to}>
            <Link
              to={item.to}
              className={styles.item}
              activeProps={{ className: `${styles.item} ${styles.active}` }}
            >
              <span className={styles.icon} aria-hidden>
                {item.to === "/notifications" && unreadCount > 0 ? (
                  <span className={styles.badgeWrap}>
                    {item.icon}
                    <span className={styles.badge} aria-label={`${unreadCount} unread`}>
                      {unreadCount > 9 ? "9+" : unreadCount}
                    </span>
                  </span>
                ) : (
                  item.icon
                )}
              </span>
              <span className={styles.label}>{item.label}</span>
            </Link>
          </li>
        ))}
      </ul>
      <div className={styles.bottom}>
        <Link to="/settings/profile" className={styles.item} aria-label="Settings">
          <span className={styles.icon} aria-hidden><Settings size={20} /></span>
          <span className={styles.label}>Settings</span>
        </Link>
      </div>
    </nav>
  );
}
