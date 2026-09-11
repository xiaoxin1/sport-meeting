<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  buildFinals,
  getEntryDetail,
  updateLanes,
  updateResults,
  type EntryDetail,
  type LaneResult,
  type LaneUpdate,
} from "@/api/schedule";

const props = defineProps<{
  modelValue: boolean;
  entryId: number | null;
}>();
const emit = defineEmits<{
  "update:modelValue": [v: boolean];
  refreshed: [];
}>();

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit("update:modelValue", v),
});

const detail = ref<EntryDetail | null>(null);
const loading = ref(false);
const saving = ref(false);
const building = ref(false);

const isPrelim = computed(() => detail.value?.round_type === "预赛");
const title = computed(() =>
  detail.value
    ? `${detail.value.event_name} · ${detail.value.group_name} · ${detail.value.gender} · ${detail.value.round_type}`
    : "赛次详情",
);

async function load() {
  if (props.entryId === null) return;
  loading.value = true;
  try {
    detail.value = await getEntryDetail(props.entryId);
  } finally {
    loading.value = false;
  }
}

watch(
  () => [props.modelValue, props.entryId],
  ([open]) => {
    if (open) load();
  },
);

async function save() {
  if (!detail.value) return;
  const results: LaneResult[] = [];
  for (const g of detail.value.groups) {
    for (const ln of g.lanes) {
      results.push({ lane_id: ln.id, result: ln.result, rank: ln.rank });
    }
  }
  saving.value = true;
  try {
    detail.value = await updateResults(detail.value.id, results);
    ElMessage.success("成绩已保存");
    emit("refreshed");
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "保存失败");
  } finally {
    saving.value = false;
  }
}

async function saveLanes() {
  if (!detail.value) return;
  const lanes: LaneUpdate[] = [];
  for (const g of detail.value.groups) {
    for (const ln of g.lanes) {
      lanes.push({
        lane_id: ln.id,
        athlete_id: ln.athlete_id,
        class_team_id: ln.class_team_id,
      });
    }
  }
  saving.value = true;
  try {
    detail.value = await updateLanes(detail.value.id, lanes);
    ElMessage.success("分组已保存");
    emit("refreshed");
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "保存失败");
  } finally {
    saving.value = false;
  }
}

async function handleBuildFinals() {
  if (!detail.value) return;
  await ElMessageBox.confirm(
    "将根据本预赛的成绩（名次优先）生成决赛名单，覆盖已有决赛分组。确定继续？",
    "生成决赛名单",
    { type: "warning", confirmButtonText: "生成" },
  );
  building.value = true;
  try {
    await buildFinals(detail.value.id);
    ElMessage.success("决赛名单已生成，可在决赛赛次中查看");
    emit("refreshed");
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "生成失败");
  } finally {
    building.value = false;
  }
}
</script>

<template>
  <el-drawer v-model="visible" size="62%" :title="title">
    <div v-loading="loading">
      <template v-if="detail">
        <div class="bar">
          <span class="tip">
            {{ detail.is_team ? "团队项目" : "个人项目" }} ·
            {{ detail.group_count }} 组
            <template v-if="detail.round_type === '预赛'">
              · 取前 {{ detail.advance_count }} 名进决赛
            </template>
            · {{ detail.start_time }}-{{ detail.end_time }} · {{ detail.venue }}
          </span>
          <div class="ops">
            <el-button
              v-if="isPrelim"
              type="warning"
              :loading="building"
              @click="handleBuildFinals"
            >
              生成决赛名单
            </el-button>
            <el-button type="success" :loading="saving" @click="saveLanes">保存分组</el-button>
            <el-button type="primary" :loading="saving" @click="save">保存成绩</el-button>
          </div>
        </div>

        <div v-for="g in detail.groups" :key="g.id" class="group">
          <h4>第 {{ g.group_no }} 组</h4>
          <el-table :data="g.lanes" size="small" border stripe>
            <el-table-column label="分道" prop="lane_no" width="70" />
            <template v-if="!detail.is_team">
              <el-table-column label="号码" prop="number" width="90" />
              <el-table-column label="姓名" prop="athlete_name" min-width="100" />
            </template>
            <el-table-column label="年级班级" min-width="130">
              <template #default="{ row }">
                {{ row.grade }}{{ row.class_name }}
              </template>
            </el-table-column>
            <el-table-column label="成绩" min-width="140">
              <template #default="{ row }">
                <el-input v-model="row.result" size="small" placeholder="如 13.20 / 1.65m" />
              </template>
            </el-table-column>
            <el-table-column label="名次" width="110">
              <template #default="{ row }">
                <el-input-number
                  v-model="row.rank"
                  size="small"
                  :min="1"
                  controls-position="right"
                  style="width: 90px"
                />
              </template>
            </el-table-column>
            <template #empty>本组暂无选手</template>
          </el-table>
        </div>
        <el-empty v-if="!detail.groups.length" description="暂无分组" />
      </template>
    </div>
  </el-drawer>
</template>

<style scoped>
.bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  gap: 12px;
}
.tip {
  font-size: 13px;
  color: var(--sfls-text-secondary);
}
.ops {
  display: flex;
  gap: 10px;
}
.group {
  margin-bottom: 18px;
}
.group h4 {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 600;
}
</style>
