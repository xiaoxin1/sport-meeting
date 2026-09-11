<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  aiOptimize,
  getSchedule,
  regenerate,
  updateConfig,
  updateEntry,
  type ScheduleData,
  type ScheduleEntry,
} from "@/api/schedule";
import { useAcademicYearStore } from "@/stores/academicYear";
import ScheduleDetail from "./schedule/ScheduleDetail.vue";

const yearStore = useAcademicYearStore();
const data = ref<ScheduleData | null>(null);
const loading = ref(false);
const busy = ref(false);

const detailVisible = ref(false);
const detailEntryId = ref<number | null>(null);

const editDialog = ref(false);
const editForm = reactive({
  id: 0,
  day_index: 1,
  period: "上午",
  order_no: 1,
  start_time: "",
  end_time: "",
  venue: "",
});

const configDialog = ref(false);
const aiDialog = ref(false);
const aiMessage = ref("");
const cfgForm = reactive({ days: 2, lanes: 8, hard_rules: "", soft_rules: "" });

// 按 (day, period) 分段，保留顺序
const sections = computed(() => {
  const out: { key: string; day: number; period: string; label: string; rows: ScheduleEntry[] }[] =
    [];
  if (!data.value) return out;
  const dates = data.value.day_dates || {};
  for (const e of data.value.entries) {
    const key = `${e.day_index}-${e.period}`;
    let sec = out.find((s) => s.key === key);
    if (!sec) {
      const dateStr = dates[String(e.day_index)] || `第 ${e.day_index} 天`;
      sec = {
        key,
        day: e.day_index,
        period: e.period,
        label: `${dateStr} · ${e.period}`,
        rows: [],
      };
      out.push(sec);
    }
    sec.rows.push(e);
  }
  return out;
});

const aiHistory = computed(() => data.value?.config?.ai_history || []);

async function load() {
  loading.value = true;
  try {
    data.value = await getSchedule();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "加载失败");
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  if (!yearStore.loaded) await yearStore.refresh();
  await load();
});

async function handleRegenerate() {
  await ElMessageBox.confirm(
    "将按当前配置与报名情况重新生成整份日程，并清空 AI 追加优化记录。确定继续？",
    "重新生成",
    { type: "warning", confirmButtonText: "重新生成" },
  );
  busy.value = true;
  try {
    await regenerate();
    await load();
    ElMessage.success("已重新生成日程");
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "生成失败");
  } finally {
    busy.value = false;
  }
}

function openAI() {
  aiMessage.value = "";
  aiDialog.value = true;
}

async function submitAI() {
  if (!aiMessage.value.trim()) {
    ElMessage.warning("请输入优化要求");
    return;
  }
  await ElMessageBox.confirm(
    "将把你的要求追加到规则后发送给 DeepSeek 重新编排时间与顺序。确定继续？",
    "AI 优化",
    { type: "info", confirmButtonText: "开始优化" },
  );
  busy.value = true;
  try {
    await aiOptimize(aiMessage.value.trim());
    aiDialog.value = false;
    await load();
    ElMessage.success("AI 优化完成");
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "AI 优化失败");
  } finally {
    busy.value = false;
  }
}

function openConfig() {
  const c = data.value?.config;
  if (c) {
    cfgForm.days = c.days;
    cfgForm.lanes = c.lanes;
    cfgForm.hard_rules = c.hard_rules;
    cfgForm.soft_rules = c.soft_rules;
  }
  configDialog.value = true;
}

async function saveConfig() {
  busy.value = true;
  try {
    await updateConfig({ ...cfgForm });
    configDialog.value = false;
    await load();
    ElMessage.success("配置已保存（下次生成时生效）");
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "保存失败");
  } finally {
    busy.value = false;
  }
}

function openDetail(row: ScheduleEntry) {
  detailEntryId.value = row.id;
  detailVisible.value = true;
}

function editEntry(row: ScheduleEntry) {
  editForm.id = row.id;
  editForm.day_index = row.day_index;
  editForm.period = row.period;
  editForm.order_no = row.order_no;
  editForm.start_time = row.start_time;
  editForm.end_time = row.end_time;
  editForm.venue = row.venue;
  editDialog.value = true;
}

async function saveEntry() {
  busy.value = true;
  try {
    await updateEntry(editForm.id, {
      day_index: editForm.day_index,
      period: editForm.period,
      order_no: editForm.order_no,
      start_time: editForm.start_time,
      end_time: editForm.end_time,
      venue: editForm.venue,
    });
    editDialog.value = false;
    await load();
    ElMessage.success("已保存");
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "保存失败");
  } finally {
    busy.value = false;
  }
}

function roundTag(t: string) {
  return t === "决赛" ? "danger" : "warning";
}
function groupLabel(row: ScheduleEntry) {
  if (row.round_type === "预赛") return `${row.group_count} 组 / 取 ${row.advance_count} 名`;
  return `${row.group_count} 组`;
}
function typeLabel(row: ScheduleEntry) {
  return row.is_team ? "团队" : "个人";
}
</script>

<template>
  <div class="schedule-page" v-loading="loading">
    <div class="page-head">
      <div>
        <h2 class="title">竞赛日程</h2>
        <p class="sub">
          {{ data?.config?.generated_at ? `最近生成：${data.config.generated_at}` : "尚未生成日程" }}
        </p>
      </div>
      <div class="actions">
        <el-button :disabled="busy" @click="openConfig">规则配置</el-button>
        <el-button type="primary" :loading="busy" @click="handleRegenerate">重新生成</el-button>
        <el-button type="success" plain :disabled="busy || !data?.entries.length" @click="openAI">
          AI 优化
        </el-button>
      </div>
    </div>

    <el-empty v-if="!loading && !data?.entries.length" description="暂无日程，点击“重新生成”开始编排" />

    <div v-for="sec in sections" :key="sec.key" class="section">
      <div class="section-title">{{ sec.label }}</div>
      <el-table :data="sec.rows" border stripe size="default" class="sched-table">
        <el-table-column type="index" label="序号" width="60" align="center" />
        <el-table-column prop="event_name" label="项目名称" width="110" show-overflow-tooltip />
        <el-table-column prop="group_name" label="组别" width="100" />
        <el-table-column prop="gender" label="性别" width="70" align="center" />
        <el-table-column label="类型" width="70" align="center">
          <template #default="{ row }">{{ typeLabel(row) }}</template>
        </el-table-column>
        <el-table-column label="赛次" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="roundTag(row.round_type)" effect="light" size="small">{{ row.round_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="组数" width="120" align="center">
          <template #default="{ row }">{{ groupLabel(row) }}</template>
        </el-table-column>
        <el-table-column label="时间" width="160" align="center">
          <template #default="{ row }">
            <span v-if="row.start_time">{{ row.start_time }} - {{ row.end_time }}</span>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="场地" width="100" align="center">
          <template #default="{ row }">
            <span v-if="row.venue">{{ row.venue }}</span>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="130" align="center" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="editEntry(row)">编辑</el-button>
            <el-button link type="primary" size="small" @click="openDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 编辑赛次 -->
    <el-dialog v-model="editDialog" title="编辑赛次" width="560px">
      <el-form :model="editForm" label-width="90px">
        <el-form-item label="比赛天数">
          <el-input-number v-model="editForm.day_index" :min="1" :max="3" />
        </el-form-item>
        <el-form-item label="时段">
          <el-radio-group v-model="editForm.period">
            <el-radio value="上午">上午</el-radio>
            <el-radio value="下午">下午</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="顺序号">
          <el-input-number v-model="editForm.order_no" :min="1" />
        </el-form-item>
        <el-form-item label="开始时间">
          <el-time-select
            v-model="editForm.start_time"
            start="07:00"
            end="18:00"
            step="00:05"
            placeholder="选择时间"
          />
        </el-form-item>
        <el-form-item label="结束时间">
          <el-time-select
            v-model="editForm.end_time"
            start="07:00"
            end="18:00"
            step="00:05"
            placeholder="选择时间"
          />
        </el-form-item>
        <el-form-item label="场地">
          <el-input v-model="editForm.venue" placeholder="例如：田径场、篮球场A" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialog = false">取消</el-button>
        <el-button type="primary" :loading="busy" @click="saveEntry">保存</el-button>
      </template>
    </el-dialog>

    <!-- 规则配置 -->
    <el-dialog v-model="configDialog" title="规则配置" width="720px" top="6vh">
      <el-form label-width="96px">
        <el-form-item label="比赛天数">
          <el-radio-group v-model="cfgForm.days">
            <el-radio :value="2">两天</el-radio>
            <el-radio :value="3">三天</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="跑道数">
          <el-input-number v-model="cfgForm.lanes" :min="2" :max="12" />
        </el-form-item>
        <el-form-item label="强规则">
          <el-input v-model="cfgForm.hard_rules" type="textarea" :rows="5" />
        </el-form-item>
        <el-form-item label="软规则">
          <el-input v-model="cfgForm.soft_rules" type="textarea" :rows="9" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="configDialog = false">取消</el-button>
        <el-button type="primary" :loading="busy" @click="saveConfig">保存</el-button>
      </template>
    </el-dialog>

    <!-- AI 优化 -->
    <el-dialog v-model="aiDialog" title="AI 优化" width="640px">
      <p class="ai-hint">用自然语言描述调整要求，会追加到既有规则后发送给 DeepSeek（重新登录或重新生成后清空）。</p>
      <el-input
        v-model="aiMessage"
        type="textarea"
        :rows="4"
        placeholder="例如：把男子100米决赛安排在上午最后，避免和跳远撞场"
      />
      <div v-if="aiHistory.length" class="ai-history">
        <div class="ai-history-title">已追加的优化记录</div>
        <ol>
          <li v-for="(h, i) in aiHistory" :key="i">{{ h }}</li>
        </ol>
      </div>
      <template #footer>
        <el-button @click="aiDialog = false">取消</el-button>
        <el-button type="success" :loading="busy" @click="submitAI">开始优化</el-button>
      </template>
    </el-dialog>

    <ScheduleDetail
      v-model="detailVisible"
      :entry-id="detailEntryId"
      @refreshed="load"
    />
  </div>
</template>

<style scoped>
.schedule-page {
  padding: 4px 2px 40px;
}
.page-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 18px;
}
.title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #1f2d3d;
}
.sub {
  margin: 4px 0 0;
  font-size: 13px;
  color: #909399;
}
.section {
  margin-bottom: 26px;
}
.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  padding: 8px 14px;
  margin-bottom: 10px;
  background: linear-gradient(90deg, #eef2f7, #f7f9fc);
  border-left: 4px solid #409eff;
  border-radius: 4px;
}
.sched-table {
  width: 100%;
}
.muted {
  color: #c0c4cc;
}
.ai-hint {
  margin: 0 0 12px;
  font-size: 13px;
  color: #909399;
}
.ai-history {
  margin-top: 16px;
  padding: 10px 14px;
  background: #f7f9fc;
  border-radius: 6px;
}
.ai-history-title {
  font-size: 13px;
  font-weight: 600;
  color: #606266;
  margin-bottom: 6px;
}
.ai-history ol {
  margin: 0;
  padding-left: 18px;
  font-size: 13px;
  color: #606266;
}
</style>

