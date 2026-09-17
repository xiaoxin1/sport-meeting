<script setup lang="ts">
import { reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage, type FormInstance, type FormRules } from "element-plus";
import { useAuthStore } from "@/stores/auth";
import { CLASS_OPTIONS, GRADE_GROUPS } from "@/config/constants";

const auth = useAuthStore();
const router = useRouter();
const route = useRoute();

const formRef = ref<FormInstance>();
const loading = ref(false);
const form = reactive({ username: "", password: "", grade: "", class_name: "" });

const rules: FormRules = {
  username: [{ required: true, message: "请输入用户名/领队姓名", trigger: "blur" }],
  password: [{ required: true, message: "请输入密码", trigger: "blur" }],
};

async function submit() {
  if (!formRef.value) return;
  await formRef.value.validate(async (valid) => {
    if (!valid) return;
    loading.value = true;
    try {
      await auth.login({
        username: form.username,
        password: form.password,
        grade: form.grade || undefined,
        class_name: form.class_name || undefined,
      });
      // 领队默认进入报名页
      const fallback = auth.isLeader ? "/registration" : "/";
      const redirect = (route.query.redirect as string) || fallback;
      router.push(redirect);
    } catch (e: any) {
      ElMessage.error(e?.response?.data?.detail || "登录失败");
    } finally {
      loading.value = false;
    }
  });
}
</script>

<template>
  <div class="login-page">
    <div class="login-card sfls-card">
      <div class="login-brand">
        <div class="mark">SFLS</div>
        <h1 class="title">苏州外国语学校运动会系统</h1>
        <p class="subtitle">Suzhou Foreign Language School Sports Meeting</p>
      </div>
      <el-form ref="formRef" :model="form" :rules="rules" @keyup.enter="submit">
        <p class="login-tip">管理员登录：年级和班级留空。领队登录：填写年级、班级，用户名为领队姓名。</p>
        <div class="login-row">
          <el-form-item prop="grade">
            <el-select
              v-model="form.grade"
              placeholder="年级（领队填）"
              size="large"
              clearable
              filterable
              allow-create
              default-first-option
              style="width: 100%"
            >
              <el-option v-for="g in GRADE_GROUPS" :key="g" :label="g" :value="g" />
            </el-select>
          </el-form-item>
          <el-form-item prop="class_name">
            <el-select
              v-model="form.class_name"
              placeholder="班级（领队填）"
              size="large"
              clearable
              filterable
              allow-create
              default-first-option
              style="width: 100%"
            >
              <el-option v-for="c in CLASS_OPTIONS" :key="c" :label="c" :value="c" />
            </el-select>
          </el-form-item>
        </div>
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="用户名 / 领队姓名" size="large" :prefix-icon="'User'" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            size="large"
            show-password
            :prefix-icon="'Lock'"
          />
        </el-form-item>
        <el-button type="primary" size="large" class="submit" :loading="loading" @click="submit">
          登录
        </el-button>
      </el-form>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1f3a5f 0%, #2f5686 100%);
}
.login-card {
  width: 380px;
  padding: 40px 36px;
}
.login-brand {
  text-align: center;
  margin-bottom: 28px;
}
.mark {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  background: var(--sfls-accent);
  color: #1f2937;
  font-weight: 700;
  font-size: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
}
.title {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
  color: var(--sfls-text);
}
.subtitle {
  font-size: 12px;
  color: var(--sfls-text-secondary);
  margin: 6px 0 0;
}
.submit {
  width: 100%;
}
.login-tip {
  font-size: 12px;
  color: var(--sfls-text-secondary);
  margin: 0 0 14px;
  line-height: 1.5;
}
.login-row {
  display: flex;
  gap: 12px;
}
.login-row .el-form-item {
  flex: 1;
}
</style>
