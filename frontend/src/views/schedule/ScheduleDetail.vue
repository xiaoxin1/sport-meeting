<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  buildFinals,
  getEntryDetail,
  updateLanes,
  updateResults,
  type EntryDetail,
} from "@/api/schedule";
import { listClasses, listAthletes } from "@/api/registration";

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
const athletes = ref<Array<{ id: number; name: string; number: string; grade: string; class_name: string }>>([]);
const classes = ref<Array<{ id: number; grade: string; class_name: string; label: string }>>([]);
const editingLaneId = ref<number | null>(null);
const editForm = reactive({
  athlete_id: null as number | null,
  class_team_id: null as number | null,
  result: "",
  rank: null as number | null,
});

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

async function loadOptionsIfNeeded() {
  if (!detail.value) return;
  // 懒加载选手/班级数据
  if (detail.value.is_team && classes.value.length === 0) {
    const classList = await listClasses();
    classes.value = classList.map((c: any) => ({
      id: c.id,
      grade: c.grade,
      class_name: c.class_name,
      label: `${c.grade}${c.class_name}`,
    }));
  } else if (!detail.value.is_team && athletes.value.length === 0) {
    const athleteList = await listAthletes();
    athletes.value = athleteList.map((a: any) => ({
      id: a.id,
      name: a.name,
      number: a.number || "",
      grade: a.grade,
      class_name: a.class_name,
    }));
  }
}

function startEdit(row: any) {
  editingLaneId.value = row.id;
  editForm.athlete_id = row.athlete_id;
  editForm.class_team_id = row.class_team_id;
  editForm.result = row.result || "";
  editForm.rank = row.rank;
  loadOptionsIfNeeded();
}

function cancelEdit() {
  editingLaneId.value = null;
}

async function saveLane(row: any) {
  if (!detail.value) return;
  saving.value = true;
  try {
    // 同时更新分道选手和成绩
    const laneUpdate = {
      lane_id: row.id,
      athlete_id: editForm.athlete_id,
      class_team_id: editForm.class_team_id,
    };
    const resultUpdate = {
      lane_id: row.id,
      result: editForm.result,
      rank: editForm.rank,
    };

    // 先更新分道
    await updateLanes(detail.value.id, [laneUpdate]);
    // 再更新成绩
    detail.value = await updateResults(detail.value.id, [resultUpdate]);

    editingLaneId.value = null;
    ElMessage.success("已保存");
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
            · {{ detail.start_time || '未设置' }}-{{ detail.end_time || '未设置' }} · {{ detail.venue }}
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
          </div>
        </div>

        <div v-for="g in detail.groups" :key="g.id" class="group">
          <h4>第 {{ g.group_no }} 组</h4>
          <el-table :data="g.lanes" size="small" border stripe>
            <el-table-column label="分道" prop="lane_no" width="70" align="center" />
            <template v-if="!detail.is_team">
              <el-table-column label="号码" min-width="120">
                <template #default="{ row }">
                  <template v-if="editingLaneId === row.id">
                    <el-select
                      v-model="editForm.athlete_id"
                      filterable
                      clearable
                      placeholder="选择选手"
                      size="small"
                      style="width: 100%"
                    >
                      <el-option
                        v-for="a in athletes"
                        :key="a.id"
                        :label="`${a.number} ${a.name} (${a.grade}${a.class_name})`"
                        :value="a.id"
                      />
                    </el-select>
                  </template>
                  <template v-else>{{ row.number }}</template>
                </template>
              </el-table-column>
              <el-table-column label="姓名" min-width="120">
                <template #default="{ row }">{{ row.athlete_name }}</template>
              </el-table-column>
              <el-table-column label="年级班级" min-width="120">
                <template #default="{ row }">{{ row.grade }}{{ row.class_name }}</template>
              </el-table-column>
            </template>
            <template v-else>
              <el-table-column label="班级" min-width="120">
                <template #default="{ row }">
                  <template v-if="editingLaneId === row.id">
                    <el-select
                      v-model="editForm.class_team_id"
                      filterable
                      clearable
                      placeholder="选择班级"
                      size="small"
                      style="width: 100%"
                    >
                      <el-option
                        v-for="c in classes"
                        :key="c.id"
                        :label="c.label"
                        :value="c.id"
                      />
                    </el-select>
                  </template>
                  <template v-else>{{ row.grade }}{{ row.class_name }}</template>
                </template>
              </el-table-column>
            </template>
            <el-table-column label="成绩" min-width="120">
              <template #default="{ row }">
                <template v-if="editingLaneId === row.id">
                  <el-input
                    v-model="editForm.result"
                    size="small"
                    placeholder="如 13.20"
                  />
                </template>
                <template v-else>{{ row.result || "-" }}</template>
              </template>
            </el-table-column>
            <el-table-column label="名次" min-width="120">
              <template #default="{ row }">
                <template v-if="editingLaneId === row.id">
                  <el-input-number
                    v-model="editForm.rank"
                    size="small"
                    :min="1"
                    controls-position="right"
                    style="width: 100%"
                  />
                </template>
                <template v-else>{{ row.rank || "-" }}</template>
              </template>
            </el-table-column>
            <el-table-column label="操作" min-width="120" align="center">
              <template #default="{ row }">
                <template v-if="editingLaneId === row.id">
                  <el-button
                    type="primary"
                    size="small"
                    :loading="saving"
                    @click="saveLane(row)"
                  >
                    保存
                  </el-button>
                  <el-button size="small" @click="cancelEdit">取消</el-button>
                </template>
                <template v-else>
                  <el-button type="primary" size="small" link @click="startEdit(row)">
                    编辑
                  </el-button>
                </template>
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
