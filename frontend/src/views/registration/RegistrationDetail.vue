<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from "element-plus";
import {
  addAthlete,
  deleteAthlete,
  getClassDetail,
  updateAthlete,
  updateTeamEvents,
  type Athlete,
  type AthleteInput,
  type ClassTeamDetail,
} from "@/api/registration";
import type { Event } from "@/api/events";

const props = defineProps<{
  modelValue: boolean;
  classId: number | null;
  events: Event[];
}>();
const emit = defineEmits<{
  "update:modelValue": [v: boolean];
}>();

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit("update:modelValue", v),
});

const detail = ref<ClassTeamDetail | null>(null);
const loading = ref(false);

// 个人项目 / 团队项目 按年级过滤（组别 == 班级年级）
const personEvents = computed(() =>
  props.events.filter((e) => !e.is_team && e.group_name === detail.value?.grade),
);
const teamEvents = computed(() =>
  props.events.filter((e) => e.is_team && e.group_name === detail.value?.grade),
);
const eventMap = computed(() => {
  const m = new Map<number, Event>();
  props.events.forEach((e) => m.set(e.id, e));
  return m;
});

async function load() {
  if (props.classId === null) return;
  loading.value = true;
  try {
    detail.value = await getClassDetail(props.classId);
    selectedTeamEvents.value = [...detail.value.team_event_ids];
  } finally {
    loading.value = false;
  }
}

watch(
  () => [props.modelValue, props.classId],
  ([open]) => {
    if (open) load();
  },
);

// ---- 学生表单 ----
const athleteDialog = ref(false);
const editingAthleteId = ref<number | null>(null);
const formRef = ref<FormInstance>();
const form = reactive<AthleteInput>({ name: "", gender: "男", event_ids: [] });
const rules: FormRules = {
  name: [{ required: true, message: "请输入姓名", trigger: "blur" }],
  gender: [{ required: true, message: "请选择性别", trigger: "change" }],
};

function openAddAthlete() {
  editingAthleteId.value = null;
  Object.assign(form, { name: "", gender: "男", event_ids: [] });
  athleteDialog.value = true;
}

function openEditAthlete(a: Athlete) {
  editingAthleteId.value = a.id;
  Object.assign(form, { name: a.name, gender: a.gender, event_ids: [...a.event_ids] });
  athleteDialog.value = true;
}

async function submitAthlete() {
  if (!formRef.value || props.classId === null) return;
  await formRef.value.validate(async (valid) => {
    if (!valid) return;
    try {
      if (editingAthleteId.value === null) {
        await addAthlete(props.classId!, { ...form });
        ElMessage.success("已添加");
      } else {
        await updateAthlete(editingAthleteId.value, { ...form });
        ElMessage.success("已保存");
      }
      athleteDialog.value = false;
      await load();
    } catch (e: any) {
      ElMessage.error(e?.response?.data?.detail || "操作失败");
    }
  });
}

async function removeAthlete(a: Athlete) {
  await ElMessageBox.confirm(`确定删除「${a.name}」？`, "提示", { type: "warning" });
  await deleteAthlete(a.id);
  ElMessage.success("已删除");
  await load();
}

function eventNames(ids: number[]): string {
  return ids
    .map((id) => eventMap.value.get(id)?.name)
    .filter(Boolean)
    .join("、");
}

// ---- 团队项目 ----
const selectedTeamEvents = ref<number[]>([]);
const savingTeam = ref(false);

async function saveTeamEvents() {
  if (props.classId === null) return;
  savingTeam.value = true;
  try {
    detail.value = await updateTeamEvents(props.classId, selectedTeamEvents.value);
    ElMessage.success("团队项目已保存");
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "保存失败");
  } finally {
    savingTeam.value = false;
  }
}
</script>

<template>
  <el-drawer v-model="visible" size="60%" :title="detail ? `${detail.grade}${detail.class_name} · 报名详情` : '报名详情'">
    <div v-loading="loading">
      <template v-if="detail">
        <div class="meta sfls-card">
          <span>领队：{{ detail.leader_name || "—" }}</span>
          <span>男生人数：{{ detail.male_count }}</span>
          <span>女生人数：{{ detail.female_count }}</span>
        </div>

        <!-- 个人项目报名 -->
        <div class="section-head">
          <h3>个人项目报名</h3>
          <el-button type="primary" size="small" :icon="'Plus'" @click="openAddAthlete">
            添加报名
          </el-button>
        </div>
        <el-table :data="detail.athletes" stripe border>
          <el-table-column label="姓名" prop="name" min-width="120" />
          <el-table-column label="性别" prop="gender" min-width="90" />
          <el-table-column label="号码" min-width="90">
            <template #default="{ row }">
              <span v-if="row.number">{{ row.number }}</span>
              <span v-else class="muted">未生成</span>
            </template>
          </el-table-column>
          <el-table-column label="报名项目" min-width="200">
            <template #default="{ row }">
              <span v-if="row.event_ids.length">{{ eventNames(row.event_ids) }}</span>
              <span v-else class="muted">—</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" min-width="120">
            <template #default="{ row }">
              <el-button link type="primary" @click="openEditAthlete(row)">编辑</el-button>
              <el-button link type="danger" @click="removeAthlete(row)">删除</el-button>
            </template>
          </el-table-column>
          <template #empty>暂无个人报名</template>
        </el-table>

        <!-- 团队项目报名 -->
        <div class="section-head">
          <h3>团队项目报名</h3>
          <el-button type="primary" size="small" :loading="savingTeam" @click="saveTeamEvents">
            保存团队项目
          </el-button>
        </div>
        <el-checkbox-group v-model="selectedTeamEvents" class="team-group">
          <el-checkbox v-for="e in teamEvents" :key="e.id" :value="e.id" border>
            {{ e.name }}（{{ e.gender }}）
          </el-checkbox>
        </el-checkbox-group>
        <el-empty v-if="!teamEvents.length" description="该年级暂无团队项目" :image-size="60" />
      </template>
    </div>

    <!-- 学生新增/编辑 -->
    <el-dialog
      v-model="athleteDialog"
      :title="editingAthleteId === null ? '添加报名' : '编辑报名'"
      width="480px"
      append-to-body
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="姓名" prop="name">
          <el-input v-model="form.name" placeholder="学生姓名" />
        </el-form-item>
        <el-form-item label="性别" prop="gender">
          <el-radio-group v-model="form.gender">
            <el-radio-button value="男">男</el-radio-button>
            <el-radio-button value="女">女</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="报名项目">
          <el-select
            v-model="form.event_ids"
            multiple
            filterable
            placeholder="选择个人项目（可多选）"
            style="width: 100%"
          >
            <el-option
              v-for="e in personEvents"
              :key="e.id"
              :label="`${e.name}（${e.gender}）`"
              :value="e.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="athleteDialog = false">取消</el-button>
        <el-button type="primary" @click="submitAthlete">保存</el-button>
      </template>
    </el-dialog>
  </el-drawer>
</template>

<style scoped>
.meta {
  display: flex;
  gap: 28px;
  padding: 14px 18px;
  margin-bottom: 20px;
  font-size: 14px;
}
.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 20px 0 12px;
}
.section-head h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
}
.team-group {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}
.muted {
  color: var(--sfls-text-secondary);
}
</style>
