import { LayoutDashboard, Bug, FlaskConical, Settings } from "lucide-react";
import { useNavigationStore } from "@/store/navigation";
import type { Page } from "@/store/navigation";
import type { LucideIcon } from "lucide-react";

interface NavItemProps {
  icon: LucideIcon;
  label: string;
  page: Page;
  isActive: boolean;
  onClick: () => void;
}

function NavItem({ icon: Icon, label, isActive, onClick }: NavItemProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex items-center gap-2 w-full h-7 px-1.5 rounded-md text-[13px] transition-colors ${
        isActive
          ? "bg-secondary text-foreground font-medium"
          : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
      }`}
    >
      <Icon size={14} className="flex-shrink-0" />
      {label}
    </button>
  );
}

const NAV_ITEMS: { icon: LucideIcon; label: string; page: Page }[] = [
  { icon: LayoutDashboard, label: "Dashboard", page: "dashboard" },
  { icon: Bug, label: "Traces", page: "traces" },
  { icon: FlaskConical, label: "Playground", page: "playground" },
];

export default function Sidebar() {
  const currentPage = useNavigationStore((s) => s.currentPage);
  const navigate = useNavigationStore((s) => s.navigate);

  return (
    <aside className="w-[220px] h-screen flex-shrink-0 flex flex-col bg-sidebar">
      <div className="px-3 pt-3 pb-2">
        <span className="text-sm font-semibold text-foreground tracking-tight">
          Beacon
        </span>
      </div>

      <nav className="flex-1 flex flex-col gap-0.5 px-2">
        {NAV_ITEMS.map((item) => (
          <NavItem
            key={item.page}
            icon={item.icon}
            label={item.label}
            page={item.page}
            isActive={currentPage === item.page}
            onClick={() => navigate(item.page)}
          />
        ))}

        <NavItem
          icon={Settings}
          label="Settings"
          page="settings"
          isActive={currentPage === "settings"}
          onClick={() => navigate("settings")}
        />
      </nav>
    </aside>
  );
}
