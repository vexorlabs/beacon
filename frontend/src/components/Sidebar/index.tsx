import {
  LayoutDashboard,
  Bug,
  FlaskConical,
  Settings,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";
import { useNavigate, useLocation } from "react-router-dom";
import { useNavigationStore } from "@/store/navigation";
import type { LucideIcon } from "lucide-react";
import { useEffect } from "react";

interface NavItemProps {
  icon: LucideIcon;
  label: string;
  isActive: boolean;
  collapsed: boolean;
  onClick: () => void;
}

function NavItem({ icon: Icon, label, isActive, collapsed, onClick }: NavItemProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={collapsed ? label : undefined}
      className={`flex items-center gap-2 w-full h-7 px-1.5 rounded-md text-[13px] transition-colors ${
        collapsed ? "justify-center" : ""
      } ${
        isActive
          ? "bg-secondary text-foreground font-medium"
          : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
      }`}
    >
      <Icon size={14} className="flex-shrink-0" />
      {!collapsed && <span className="truncate">{label}</span>}
    </button>
  );
}

const NAV_ITEMS: { icon: LucideIcon; label: string; path: string }[] = [
  { icon: LayoutDashboard, label: "Dashboard", path: "/" },
  { icon: Bug, label: "Traces", path: "/traces" },
  { icon: FlaskConical, label: "Playground", path: "/playground" },
];

export default function Sidebar() {
  const location = useLocation();
  const navigate = useNavigate();
  const collapsed = useNavigationStore((s) => s.sidebarCollapsed);
  const toggleSidebar = useNavigationStore((s) => s.toggleSidebar);

  const isActive = (path: string) => {
    if (path === "/") return location.pathname === "/";
    return location.pathname.startsWith(path);
  };

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "\\") {
        e.preventDefault();
        toggleSidebar();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [toggleSidebar]);

  return (
    <aside
      className="h-screen flex-shrink-0 flex flex-col bg-sidebar transition-[width] duration-200 ease-in-out"
      style={{ width: collapsed ? 48 : 220 }}
    >
      <div className={`flex items-center pt-3 pb-2 ${collapsed ? "justify-center px-1.5" : "justify-between px-3"}`}>
        {!collapsed && (
          <span className="text-sm font-semibold text-foreground tracking-tight">
            Beacon
          </span>
        )}
        <button
          type="button"
          onClick={toggleSidebar}
          title={collapsed ? "Expand sidebar (Cmd+\\)" : "Collapse sidebar (Cmd+\\)"}
          className="flex items-center justify-center w-6 h-6 rounded-md text-muted-foreground hover:text-foreground hover:bg-secondary/50 transition-colors"
        >
          {collapsed ? <PanelLeftOpen size={14} /> : <PanelLeftClose size={14} />}
        </button>
      </div>

      <nav className={`flex-1 flex flex-col gap-0.5 ${collapsed ? "px-1.5" : "px-2"}`}>
        {NAV_ITEMS.map((item) => (
          <NavItem
            key={item.path}
            icon={item.icon}
            label={item.label}
            isActive={isActive(item.path)}
            collapsed={collapsed}
            onClick={() => navigate(item.path)}
          />
        ))}
      </nav>

      <nav className={`flex flex-col gap-0.5 pb-3 ${collapsed ? "px-1.5" : "px-2"}`}>
        <NavItem
          icon={Settings}
          label="Settings"
          isActive={isActive("/settings")}
          collapsed={collapsed}
          onClick={() => navigate("/settings")}
        />
      </nav>
    </aside>
  );
}
