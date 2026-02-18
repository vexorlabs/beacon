import { create } from "zustand";

export type Page = "dashboard" | "traces" | "playground" | "settings";

interface NavigationStore {
  currentPage: Page;
  sidebarCollapsed: boolean;
  navigate: (page: Page) => void;
  toggleSidebar: () => void;
}

export const useNavigationStore = create<NavigationStore>((set) => ({
  currentPage: "dashboard",
  sidebarCollapsed: false,
  navigate: (page: Page) => set({ currentPage: page }),
  toggleSidebar: () =>
    set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
}));
