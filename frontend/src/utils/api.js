/**
 * axios 인스턴스. Vite proxy를 통해 /api → localhost:8000.
 */

import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  timeout: 10000,
});

export default api;
