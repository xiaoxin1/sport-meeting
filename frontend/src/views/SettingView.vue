<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { getSettings, updateSetting, type Setting } from "@/api/settings";

const loading = ref(false);
const settings = ref<Setting[]>([]);
const apiKeyValue = ref("");
const baseUrlValue = ref("");

async function load() {
  loading.value = true;
  try {
    settings.value = await getSettings();
    const apiKey = settings.value.find((s) => s.key === "deepseek_api_key");
    const baseUrl = settings.value.find((s) => s.key === "deepseek_base_url");
    apiKeyValue.value = apiKey?.value || "";
    baseUrlValue.value = baseUrl?.value || "https://api.deepseek.com";
  } finally {
    loading.value = false;
  }
}

async function save() {
  loading.value = true;
  try {
    await updateSetting("deepseek_api_key", apiKeyValue.value);
    await updateSetting("deepseek_base_url", baseUrlValue.value);
    ElMessage.success("保存成功");
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "保存失败");
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  load();
});
</script>

<template>
  <div class="setting-view">
    <div class="header">
      <h2>系统设置</h2>
    </div>

    <el-card v-loading="loading" class="setting-card">
      <template #header>
        <span>DeepSeek API 配置</span>
      </template>

      <el-form label-width="140px" label-position="left">
        <el-form-item label="API Key">
          <el-input
            v-model="apiKeyValue"
            placeholder="请输入 DeepSeek API Key"
            type="password"
            show-password
            clearable
          />
          <div class="tip">
            在
            <a href="https://platform.deepseek.com" target="_blank">platform.deepseek.com</a>
            注册并获取 API Key，用于 AI 优化日程功能
          </div>
        </el-form-item>

        <el-form-item label="Base URL">
          <el-input
            v-model="baseUrlValue"
            placeholder="https://api.deepseek.com"
            clearable
          />
          <div class="tip">通常使用默认值即可</div>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="loading" @click="save">保存配置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<style scoped>
.setting-view {
  padding: 24px;
}

.header {
  margin-bottom: 24px;
}

.header h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 500;
}

.setting-card {
  max-width: 800px;
}

.tip {
  margin-top: 8px;
  font-size: 13px;
  color: #909399;
  line-height: 1.5;
}

.tip a {
  color: #409eff;
  text-decoration: none;
}

.tip a:hover {
  text-decoration: underline;
}
</style>
