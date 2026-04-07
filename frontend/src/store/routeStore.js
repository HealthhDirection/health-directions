/**
 * zustand 기반 경로 상태 관리.
 */

import { create } from "zustand";

const useRouteStore = create((set) => ({
  origin: null, // { lat, lng, name }
  destination: null, // { lat, lng, name }
  routes: [], // 추천 경로 목록
  loading: false,

  setOrigin: (origin) => set({ origin }),
  setDestination: (destination) => set({ destination }),
  setRoutes: (routes) => set({ routes, loading: false }),
  setLoading: (loading) => set({ loading }),
}));

export default useRouteStore;
