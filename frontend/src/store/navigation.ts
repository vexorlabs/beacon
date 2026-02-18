import { create } from "zustand";

export type Page = "dashboard" | "traces" | "playground" | "settings";

interface NavigationStore {
  currentPage: Page;
  navigate: (page: Page) => void;
}

export const useNavigationStore = create<NavigationStore>((set) => ({
  currentPage: "dashboard",
  navigate: (page: Page) => set({ currentPage: page }),
}));
