import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";
import { useAuthStore } from "@/stores/auth";

/**
 * 业务模块路由集中在此。每新增一个功能 tab，在 children 中追加即可，
 * meta.title 用于侧边栏与面包屑展示。
 */
const routes: RouteRecordRaw[] = [
  {
    path: "/login",
    name: "login",
    component: () => import("@/views/LoginView.vue"),
    meta: { public: true },
  },
  {
    path: "/",
    component: () => import("@/layouts/MainLayout.vue"),
    redirect: "/academic-years",
    children: [
      {
        path: "academic-years",
        name: "academic-years",
        component: () => import("@/views/AcademicYearView.vue"),
        meta: { title: "学年设置" },
      },
      {
        path: "events",
        name: "events",
        component: () => import("@/views/EventView.vue"),
        meta: { title: "项目" },
      },
      {
        path: "registration",
        name: "registration",
        component: () => import("@/views/RegistrationView.vue"),
        meta: { title: "报名" },
      },
      {
        path: "schedule",
        name: "schedule",
        component: () => import("@/views/ScheduleView.vue"),
        meta: { title: "竞赛日程" },
      },
      {
        path: "settings",
        name: "settings",
        component: () => import("@/views/SettingView.vue"),
        meta: { title: "系统设置" },
      },
    ],
  },
  { path: "/:pathMatch(.*)*", redirect: "/" },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to) => {
  const auth = useAuthStore();
  if (!to.meta.public && !auth.isAuthenticated()) {
    return { name: "login", query: { redirect: to.fullPath } };
  }
  if (to.name === "login" && auth.isAuthenticated()) {
    return { path: "/" };
  }
  return true;
});

export default router;
