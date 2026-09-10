import { defineStore } from "pinia";
import { ref } from "vue";
import { login as apiLogin, type LoginPayload } from "@/api/auth";

export const useAuthStore = defineStore("auth", () => {
  const token = ref<string | null>(localStorage.getItem("sfls_token"));
  const username = ref<string | null>(localStorage.getItem("sfls_username"));

  async function login(payload: LoginPayload) {
    const res = await apiLogin(payload);
    token.value = res.access_token;
    username.value = res.username;
    localStorage.setItem("sfls_token", res.access_token);
    localStorage.setItem("sfls_username", res.username);
  }

  function logout() {
    token.value = null;
    username.value = null;
    localStorage.removeItem("sfls_token");
    localStorage.removeItem("sfls_username");
  }

  function isAuthenticated(): boolean {
    return !!token.value;
  }

  return { token, username, login, logout, isAuthenticated };
});
