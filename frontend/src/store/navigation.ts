import { create } from "zustand";

interface NavigationStore {
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
}

export const useNavigationStore = create<NavigationStore>((set) => ({
  sidebarCollapsed: false,
  toggleSidebar: () =>
    set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
}));
