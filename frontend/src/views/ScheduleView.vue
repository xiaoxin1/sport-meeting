<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  aiOptimize,
  aiCheck,
  clearSchedule,
  createEntry,
  deleteEntry,
  generateSchedule,
  getSchedule,
  updateEntry,
  type ScheduleData,
  type ScheduleEntry,
} from "@/api/schedule";
import { listEvents, type Event } from "@/api/events";
import { VENUES } from "@/config/constants";
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
  start_time: "",
  end_time: "",
  venue: "",
});

const createDialog = ref(false);
const events = ref<Event[]>([]);
const createForm = reactive({
  event_id: null as number | null,
  day_index: 1,
  period: "上午",
  round_type: "决赛",
  start_time: "",
  end_time: "",
  venue: "",
});

const aiDialog = ref(false);
const aiMessage = ref("");
const aiMode = ref<"optimize" | "check">("optimize"); // 区分是优化还是检查

// AI 缺陷/优化报告
const reportVisible = ref(false);
const reportIssues = ref<string[]>([]);
const reportMode = ref<"generate" | "optimize" | "check">("optimize");


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

// 筛选：按日期(天)与上下午
const filterDay = ref<number | "">("");
const filterPeriod = ref<string>("");

// 可选的日期列表（含日期文案）
const dayOptions = computed(() => {
  const dates = data.value?.day_dates || {};
  const days = [...new Set(sections.value.map((s) => s.day))].sort((a, b) => a - b);
  return days.map((d) => ({
    value: d,
    label: dates[String(d)] || `第 ${d} 天`,
  }));
});

// 可选的时段列表
const periodOptions = computed(() =>
  [...new Set(sections.value.map((s) => s.period))],
);

// 新增赛次时可选的日期（按配置天数，含尚无赛次的天）
const createDayOptions = computed(() => {
  const dates = data.value?.day_dates || {};
  const total = data.value?.config?.days || 2;
  const out: { value: number; label: string }[] = [];
  for (let d = 1; d <= total; d++) {
    out.push({ value: d, label: dates[String(d)] || `第 ${d} 天` });
  }
  return out;
});

const filteredSections = computed(() =>
  sections.value.filter((s) => {
    const okDay = !filterDay.value || s.day === filterDay.value;
    const okPeriod = !filterPeriod.value || s.period === filterPeriod.value;
    return okDay && okPeriod;
  }),
);

// 将UTC时间转换为本地时间显示
const generatedAtLocal = computed(() => {
  if (!data.value?.config?.generated_at) return null;
  // 后端返回的是UTC时间字符串，需要加上Z标识表示UTC时区
  const utcTimeString = data.value.config.generated_at.endsWith('Z')
    ? data.value.config.generated_at
    : data.value.config.generated_at + 'Z';
  const utcDate = new Date(utcTimeString);
  return utcDate.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  });
});

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

async function handleClear() {
  const { value: pwd } = await ElMessageBox.prompt(
    "将删除当前学年的全部日程，且清空 AI 优化记录。请输入管理员密码确认。",
    "清除日程",
    {
      type: "warning",
      confirmButtonText: "清除日程",
      inputType: "password",
      inputPlaceholder: "管理员密码",
      inputValidator: (v) => (v ? true : "请输入管理员密码"),
    },
  );
  busy.value = true;
  try {
    await clearSchedule(pwd);
    await load();
    ElMessage.success("已清除日程");
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "清除失败");
  } finally {
    busy.value = false;
  }
}

function openAI() {
  aiMode.value = "optimize";
  aiMessage.value = "";
  aiDialog.value = true;
}

function openAICheck() {
  aiMode.value = "check";
  aiMessage.value = "";
  aiDialog.value = true;
}

const hasEntries = computed(() => !!data.value?.entries.length);

async function handleGenerate() {
  await ElMessageBox.confirm(
    "将按规则确定性生成日程（清空旧日程）。规则包括：按天数自动分配小学/初高中赛段、先预赛后决赛、智能分组分道、避免运动员时间冲突等。确定继续？",
    "规则生成日程",
    { type: "warning", confirmButtonText: "开始生成" },
  );
  busy.value = true;
  try {
    await generateSchedule();
    await load();
    ElMessage.success("规则生成完成");
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "生成失败");
  } finally {
    busy.value = false;
  }
}

async function submitAI() {
  if (!hasEntries.value) {
    ElMessage.warning("请先使用规则生成日程，再进行 AI 操作");
    return;
  }
  const extra = aiMessage.value.trim();

  if (aiMode.value === "check") {
    // AI 检查模式：不修改日程，只返回建议
    await ElMessageBox.confirm(
      "将把当前日程连同配置规则送给 DeepSeek 检查分析。此过程可能持续数分钟，请勿关闭页面。确定继续？",
      "AI 检查",
      { type: "info", confirmButtonText: "开始检查" },
    );
    busy.value = true;
    try {
      const res = await aiCheck(extra);
      aiDialog.value = false;
      reportMode.value = res.mode;
      reportIssues.value = res.issues || [];
      reportVisible.value = true;
      ElMessage.success("AI 检查完成");
    } catch (e: any) {
      ElMessage.error(e?.response?.data?.detail || "AI 检查失败");
    } finally {
      busy.value = false;
    }
  } else {
    // AI 优化模式：会修改日程
    await ElMessageBox.confirm(
      "将把当前日程连同配置规则送给 DeepSeek 优化时间与顺序。此过程可能持续数分钟，请勿关闭页面。确定继续？",
      "AI 优化",
      { type: "info", confirmButtonText: "开始优化" },
    );
    busy.value = true;
    try {
      const res = await aiOptimize(extra);
      aiDialog.value = false;
      await load();
      reportMode.value = res.mode;
      reportIssues.value = res.issues || [];
      reportVisible.value = true;
      ElMessage.success("AI 优化完成");
    } catch (e: any) {
      ElMessage.error(e?.response?.data?.detail || "AI 优化失败");
    } finally {
      busy.value = false;
    }
  }
}

function openDetail(row: ScheduleEntry) {
  detailEntryId.value = row.id;
  detailVisible.value = true;
}

function editEntry(row: ScheduleEntry) {
  editForm.id = row.id;
  editForm.start_time = row.start_time;
  editForm.end_time = row.end_time;
  editForm.venue = row.venue;
  editDialog.value = true;
}

async function saveEntry() {
  busy.value = true;
  try {
    await updateEntry(editForm.id, {
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

async function openCreate() {
  createForm.event_id = null;
  createForm.day_index = 1;
  createForm.period = "上午";
  createForm.round_type = "决赛";
  createForm.start_time = "";
  createForm.end_time = "";
  createForm.venue = "";
  if (!events.value.length) {
    try {
      events.value = await listEvents();
    } catch (e: any) {
      ElMessage.error(e?.response?.data?.detail || "加载项目失败");
    }
  }
  createDialog.value = true;
}

// 选中项目后，场地默认取该项目的场地（仍可手动改）
function onCreateEventChange(id: number | null) {
  const ev = events.value.find((e) => e.id === id);
  if (ev) createForm.venue = ev.venue;
}

async function saveCreate() {
  if (!createForm.event_id) {
    ElMessage.warning("请选择项目");
    return;
  }
  busy.value = true;
  try {
    await createEntry({
      event_id: createForm.event_id,
      day_index: createForm.day_index,
      period: createForm.period,
      round_type: createForm.round_type,
      start_time: createForm.start_time,
      end_time: createForm.end_time,
      venue: createForm.venue,
    });
    createDialog.value = false;
    await load();
    ElMessage.success("已新增赛次");
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "新增失败");
  } finally {
    busy.value = false;
  }
}

async function removeEntry(row: ScheduleEntry) {
  await ElMessageBox.confirm(
    `确定删除赛次「${row.event_name} · ${row.group_name} · ${row.round_type}」？`,
    "删除赛次",
    { type: "warning", confirmButtonText: "删除" },
  );
  busy.value = true;
  try {
    await deleteEntry(row.id);
    await load();
    ElMessage.success("已删除");
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "删除失败");
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
          {{ generatedAtLocal ? `最近生成：${generatedAtLocal}` : "尚未生成日程" }}
        </p>
      </div>
      <div class="actions">
        <el-button type="danger" plain :disabled="busy || !data?.entries.length" @click="handleClear">
          清除日程
        </el-button>
        <el-button :disabled="busy" @click="openCreate">新增赛次</el-button>
        <el-button type="primary" :loading="busy" @click="handleGenerate">
          规则生成
        </el-button>
        <el-button type="info" :loading="busy" :disabled="!hasEntries" @click="openAICheck">
          AI 检查
        </el-button>
        <el-button type="success" :loading="busy" :disabled="!hasEntries" @click="openAI">
          AI 优化
        </el-button>
      </div>
    </div>

    <el-empty v-if="!loading && !data?.entries.length" description="暂无日程，点击「规则生成」开始编排" />

    <div v-if="data?.entries.length" class="toolbar">
      <el-select v-model="filterDay" placeholder="全部日期" clearable style="width: 200px">
        <el-option v-for="d in dayOptions" :key="d.value" :label="d.label" :value="d.value" />
      </el-select>
      <el-select v-model="filterPeriod" placeholder="全部时段" clearable style="width: 140px">
        <el-option v-for="p in periodOptions" :key="p" :label="p" :value="p" />
      </el-select>
      <span class="count">共 {{ filteredSections.length }} 个时段</span>
    </div>

    <el-empty
      v-if="data?.entries.length && !filteredSections.length"
      description="没有符合筛选条件的日程"
    />

    <div v-for="sec in filteredSections" :key="sec.key" class="section">
      <div class="section-title">{{ sec.label }}</div>
      <el-table :data="sec.rows" border stripe size="default" class="sched-table">
        <el-table-column type="index" label="序号" width="60" align="center" />
        <el-table-column prop="event_name" label="项目名称" min-width="120" show-overflow-tooltip />
        <el-table-column prop="group_name" label="组别" min-width="120" />
        <el-table-column prop="gender" label="性别" min-width="120" align="center" />
        <el-table-column label="类型" min-width="120" align="center">
          <template #default="{ row }">{{ typeLabel(row) }}</template>
        </el-table-column>
        <el-table-column label="赛次" min-width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="roundTag(row.round_type)" effect="light" size="small">{{ row.round_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="组数" min-width="120" align="center">
          <template #default="{ row }">{{ groupLabel(row) }}</template>
        </el-table-column>
        <el-table-column label="时间" min-width="120" align="center">
          <template #default="{ row }">
            <span v-if="row.start_time">{{ row.start_time }} - {{ row.end_time }}</span>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="场地" min-width="120" align="center">
          <template #default="{ row }">
            <span v-if="row.venue">{{ row.venue }}</span>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="120" align="center" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="editEntry(row)">编辑</el-button>
            <el-button link type="primary" size="small" @click="openDetail(row)">详情</el-button>
            <el-button link type="danger" size="small" @click="removeEntry(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 编辑赛次（仅时间与场地，日程按时间自动排序） -->
    <el-dialog v-model="editDialog" title="编辑赛次" width="560px">
      <el-form :model="editForm" label-width="90px">
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
          <el-select
            v-model="editForm.venue"
            placeholder="选择或输入场地"
            filterable
            allow-create
            default-first-option
            style="width: 100%"
          >
            <el-option v-for="v in VENUES" :key="v" :label="v" :value="v" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialog = false">取消</el-button>
        <el-button type="primary" :loading="busy" @click="saveEntry">保存</el-button>
      </template>
    </el-dialog>

    <!-- 新增赛次 -->
    <el-dialog v-model="createDialog" title="新增赛次" width="560px">
      <el-form :model="createForm" label-width="90px">
        <el-form-item label="项目">
          <el-select
            v-model="createForm.event_id"
            placeholder="选择项目"
            filterable
            style="width: 100%"
            @change="onCreateEventChange"
          >
            <el-option
              v-for="ev in events"
              :key="ev.id"
              :label="`${ev.name} · ${ev.group_name} · ${ev.gender}`"
              :value="ev.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="日期">
          <el-select v-model="createForm.day_index" placeholder="选择日期" style="width: 100%">
            <el-option
              v-for="d in createDayOptions"
              :key="d.value"
              :label="d.label"
              :value="d.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="时段">
          <el-radio-group v-model="createForm.period">
            <el-radio value="上午">上午</el-radio>
            <el-radio value="下午">下午</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="赛次">
          <el-radio-group v-model="createForm.round_type">
            <el-radio value="预赛">预赛</el-radio>
            <el-radio value="决赛">决赛</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="开始时间">
          <el-time-select
            v-model="createForm.start_time"
            start="07:00"
            end="18:00"
            step="00:05"
            placeholder="选择时间"
          />
        </el-form-item>
        <el-form-item label="结束时间">
          <el-time-select
            v-model="createForm.end_time"
            start="07:00"
            end="18:00"
            step="00:05"
            placeholder="选择时间"
          />
        </el-form-item>
        <el-form-item label="场地">
          <el-select
            v-model="createForm.venue"
            placeholder="默认取项目场地，可修改"
            filterable
            allow-create
            default-first-option
            style="width: 100%"
          >
            <el-option v-for="v in VENUES" :key="v" :label="v" :value="v" />
          </el-select>
        </el-form-item>
      </el-form>
      <p class="ai-hint">新增为空赛次，分组与选手请在“详情”中手动添加。</p>
      <template #footer>
        <el-button @click="createDialog = false">取消</el-button>
        <el-button type="primary" :loading="busy" @click="saveCreate">创建</el-button>
      </template>
    </el-dialog>

    <!-- AI 优化/检查 -->
    <el-dialog v-model="aiDialog" :title="aiMode === 'check' ? 'AI 检查' : 'AI 优化'" width="640px">
      <p class="ai-hint">
        <span v-if="aiMode === 'check'">
          将把当前日程连同配置规则发送给 DeepSeek 进行检查分析，找出可以优化的地方。不会修改日程。下方可填写本次检查的关注点（可留空）。此过程可能持续数分钟。
        </span>
        <span v-else>
          将把当前日程连同配置规则发送给 DeepSeek 优化时间与顺序。下方额外要求会作为本次优化提示一并送出（可留空）。此过程可能持续数分钟。
        </span>
      </p>
      <el-input
        v-model="aiMessage"
        type="textarea"
        :rows="4"
        :placeholder="aiMode === 'check'
          ? '本次检查关注点（可留空）。例如：重点检查运动员冲突和场地利用效率'
          : '本次优化要求（可留空）。例如：把男子100米决赛安排在上午最后，避免和跳远撞场'"
      />
      <template #footer>
        <el-button @click="aiDialog = false">取消</el-button>
        <el-button
          :type="aiMode === 'check' ? 'info' : 'success'"
          :loading="busy"
          @click="submitAI"
        >
          {{ aiMode === 'check' ? '开始检查' : '开始优化' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 缺陷 / 优化报告 -->
    <el-dialog
      v-model="reportVisible"
      :title="reportMode === 'check' ? 'AI 检查报告' : '本次优化报告'"
      width="640px"
    >
      <p class="ai-hint">
        <span v-if="reportMode === 'check'">
          以下为 AI 检查发现的优化建议，供参考调整。
        </span>
        <span v-else>
          以下为 AI 自评与系统校验发现的缺陷或可优化点，供人工复核调整。
        </span>
      </p>
      <ol v-if="reportIssues.length" class="report-list">
        <li v-for="(it, i) in reportIssues" :key="i">{{ it }}</li>
      </ol>
      <el-empty v-else description="未发现明显缺陷" />
      <template #footer>
        <el-button type="primary" @click="reportVisible = false">知道了</el-button>
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
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 18px;
}
.toolbar .count {
  margin-left: auto;
  color: var(--sfls-text-secondary);
  font-size: 13px;
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
.report-list {
  margin: 0 0 12px;
  padding-left: 18px;
  font-size: 14px;
  color: #606266;
  line-height: 1.8;
}
.report-list li {
  margin-bottom: 8px;
}
</style>

