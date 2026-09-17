import { defineStore } from "pinia";
import { computed, ref } from "vue";
import { login as apiLogin, type LoginPayload } from "@/api/auth";

export const useAuthStore = defineStore("auth", () => {
  const token = ref<string | null>(localStorage.getItem("sfls_token"));
  const username = ref<string | null>(localStorage.getItem("sfls_username"));
  const role = ref<string>(localStorage.getItem("sfls_role") || "admin");
  const classTeamId = ref<number | null>(
    localStorage.getItem("sfls_class_team_id")
      ? Number(localStorage.getItem("sfls_class_team_id"))
      : null,
  );

  const isAdmin = computed(() => role.value === "admin");
  const isLeader = computed(() => role.value === "leader");

  async function login(payload: LoginPayload) {
    const res = await apiLogin(payload);
    token.value = res.access_token;
    username.value = res.username;
    role.value = res.role;
    classTeamId.value = res.class_team_id;
    localStorage.setItem("sfls_token", res.access_token);
    localStorage.setItem("sfls_username", res.username);
    localStorage.setItem("sfls_role", res.role);
    if (res.class_team_id != null) {
      localStorage.setItem("sfls_class_team_id", String(res.class_team_id));
    } else {
      localStorage.removeItem("sfls_class_team_id");
    }
  }

  function logout() {
    token.value = null;
    username.value = null;
    role.value = "admin";
    classTeamId.value = null;
    localStorage.removeItem("sfls_token");
    localStorage.removeItem("sfls_username");
    localStorage.removeItem("sfls_role");
    localStorage.removeItem("sfls_class_team_id");
  }

  function isAuthenticated(): boolean {
    return !!token.value;
  }

  return {
    token,
    username,
    role,
    classTeamId,
    isAdmin,
    isLeader,
    login,
    logout,
    isAuthenticated,
  };
});
