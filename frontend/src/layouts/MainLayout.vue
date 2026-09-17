<script setup lang="ts">
import { computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessageBox } from "element-plus";
import { navItems } from "@/config/nav";
import { useAuthStore } from "@/stores/auth";
import { useAcademicYearStore } from "@/stores/academicYear";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const yearStore = useAcademicYearStore();

const activeMenu = computed(() => route.path);

// 领队仅显示允许的菜单（报名）
const visibleNav = computed(() =>
  auth.isLeader ? navItems.filter((i) => i.leaderAllowed) : navItems,
);

onMounted(() => {
  if (!yearStore.loaded) yearStore.refresh();
});

async function handleLogout() {
  await ElMessageBox.confirm("确定要退出登录吗？", "提示", { type: "warning" });
  auth.logout();
  router.push("/login");
}
</script>

<template>
  <el-container class="layout">
    <el-aside width="220px" class="sidebar">
      <div class="brand">
        <div class="brand-mark">SFLS</div>
        <div class="brand-text">
          <div class="brand-name">运动会系统</div>
          <div class="brand-sub">苏州外国语学校</div>
        </div>
      </div>
      <el-menu :default-active="activeMenu" router class="menu">
        <el-menu-item
          v-for="item in visibleNav"
          :key="item.index"
          :index="item.index"
          :disabled="item.disabled"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.title }}</span>
          <el-tag v-if="item.disabled" size="small" type="info" class="soon">待开发</el-tag>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="year-badge">
          <span class="year-label">当前学年</span>
          <span v-if="yearStore.active" class="year-value">{{ yearStore.active.name }}</span>
          <span v-else class="year-empty">未设置</span>
        </div>
        <el-dropdown @command="handleLogout">
          <span class="user">
            <el-icon><Avatar /></el-icon>
            {{ auth.username }}
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>

      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.layout {
  height: 100vh;
}
.sidebar {
  background: var(--sfls-primary);
  display: flex;
  flex-direction: column;
}
.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 18px;
}
.brand-mark {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: var(--sfls-accent);
  color: #1f2937;
  font-weight: 700;
  font-size: 15px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.brand-name {
  color: #fff;
  font-weight: 600;
  font-size: 15px;
}
.brand-sub {
  color: rgba(255, 255, 255, 0.6);
  font-size: 12px;
}
.menu {
  border-right: none;
  background: transparent;
  flex: 1;
}
.menu :deep(.el-menu-item) {
  color: rgba(255, 255, 255, 0.75);
}
.menu :deep(.el-menu-item.is-active) {
  color: #fff;
  background: var(--sfls-primary-light);
}
.menu :deep(.el-menu-item:hover) {
  background: var(--sfls-primary-light);
}
.soon {
  margin-left: auto;
  transform: scale(0.85);
}
.header {
  background: var(--sfls-surface);
  border-bottom: 1px solid var(--sfls-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.year-badge {
  display: flex;
  align-items: center;
  gap: 8px;
}
.year-label {
  font-size: 13px;
  color: var(--sfls-text-secondary);
}
.year-value {
  font-weight: 600;
  color: var(--sfls-primary);
}
.year-empty {
  color: var(--sfls-text-secondary);
}
.user {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  color: var(--sfls-text);
}
.main {
  padding: 24px;
  background: var(--sfls-bg);
}
</style>
