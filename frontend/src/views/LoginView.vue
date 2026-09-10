<script setup lang="ts">
import { reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage, type FormInstance, type FormRules } from "element-plus";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();
const router = useRouter();
const route = useRoute();

const formRef = ref<FormInstance>();
const loading = ref(false);
const form = reactive({ username: "", password: "" });

const rules: FormRules = {
  username: [{ required: true, message: "请输入用户名", trigger: "blur" }],
  password: [{ required: true, message: "请输入密码", trigger: "blur" }],
};

async function submit() {
  if (!formRef.value) return;
  await formRef.value.validate(async (valid) => {
    if (!valid) return;
    loading.value = true;
    try {
      await auth.login(form);
      const redirect = (route.query.redirect as string) || "/";
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
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="用户名" size="large" :prefix-icon="'User'" />
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
</style>
