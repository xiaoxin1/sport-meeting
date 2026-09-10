import axios from "axios";

/** 统一 axios 实例：注入 token、集中处理 401。 */
const client = axios.create({
  baseURL: "/api",
  timeout: 30000,
});

client.interceptors.request.use((config) => {
  const token = localStorage.getItem("sfls_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

client.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("sfls_token");
      if (location.pathname !== "/login") {
        location.href = "/login";
      }
    }
    return Promise.reject(error);
  },
);

export default client;
