<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from "element-plus";
import {
  createEvent,
  deleteEvent,
  listEvents,
  updateEvent,
  type Event,
  type EventInput,
} from "@/api/events";
import { GENDERS, GRADE_GROUPS } from "@/config/constants";
import { useAcademicYearStore } from "@/stores/academicYear";

const yearStore = useAcademicYearStore();
const events = ref<Event[]>([]);
const loading = ref(false);
const keyword = ref("");
const filterGroup = ref("");

const dialogVisible = ref(false);
const editingId = ref<number | null>(null);
const formRef = ref<FormInstance>();
const form = reactive<EventInput>({
  name: "",
  group_name: "",
  gender: "男",
  final_teams: 0,
  is_team: false,
  description: "",
});

const rules: FormRules = {
  name: [{ required: true, message: "请输入项目名称", trigger: "blur" }],
  group_name: [{ required: true, message: "请选择组别", trigger: "change" }],
  gender: [{ required: true, message: "请选择性别", trigger: "change" }],
};

const filtered = computed(() =>
  events.value.filter((e) => {
    const okKw = !keyword.value || e.name.includes(keyword.value);
    const okGroup = !filterGroup.value || e.group_name === filterGroup.value;
    return okKw && okGroup;
  }),
);

async function load() {
  loading.value = true;
  try {
    events.value = await listEvents();
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

function openCreate() {
  editingId.value = null;
  Object.assign(form, {
    name: "",
    group_name: "",
    gender: "男",
    final_teams: 0,
    is_team: false,
    description: "",
  });
  dialogVisible.value = true;
}

function openEdit(row: Event) {
  editingId.value = row.id;
  Object.assign(form, {
    name: row.name,
    group_name: row.group_name,
    gender: row.gender,
    final_teams: row.final_teams,
    is_team: row.is_team,
    description: row.description,
  });
  dialogVisible.value = true;
}

async function submit() {
  if (!formRef.value) return;
  await formRef.value.validate(async (valid) => {
    if (!valid) return;
    try {
      if (editingId.value === null) {
        await createEvent({ ...form });
        ElMessage.success("已创建项目");
      } else {
        await updateEvent(editingId.value, { ...form });
        ElMessage.success("已保存");
      }
      dialogVisible.value = false;
      await load();
    } catch (e: any) {
      ElMessage.error(e?.response?.data?.detail || "操作失败");
    }
  });
}

async function handleDelete(row: Event) {
  await ElMessageBox.confirm(
    `确定删除项目「${row.name}·${row.group_name}·${row.gender}」？`,
    "提示",
    { type: "warning" },
  );
  await deleteEvent(row.id);
  ElMessage.success("已删除");
  await load();
}

function genderTag(g: string) {
  return g === "男" ? "" : g === "女" ? "danger" : "warning";
}
</script>

<template>
  <div>
    <div class="page-head">
      <div>
        <h2 class="sfls-page-title">项目</h2>
        <p class="sfls-page-subtitle">
          维护本学年的比赛项目。项目名称 + 组别 + 性别 构成唯一项目。
        </p>
      </div>
      <el-button type="primary" :icon="'Plus'" :disabled="!yearStore.active" @click="openCreate">
        新建项目
      </el-button>
    </div>

    <el-alert
      v-if="!yearStore.active"
      type="warning"
      :closable="false"
      title="尚未设置当前学年，请先在「学年设置」中创建并激活学年。"
      class="mb"
    />

    <div class="sfls-card table-card">
      <div class="toolbar">
        <el-input
          v-model="keyword"
          placeholder="搜索项目名称"
          :prefix-icon="'Search'"
          clearable
          style="width: 220px"
        />
        <el-select v-model="filterGroup" placeholder="全部组别" clearable style="width: 160px">
          <el-option v-for="g in GRADE_GROUPS" :key="g" :label="g" :value="g" />
        </el-select>
        <span class="count">共 {{ filtered.length }} 个项目</span>
      </div>

      <el-table
        :data="filtered"
        v-loading="loading"
        stripe
        :default-sort="{ prop: 'name', order: 'ascending' }"
      >
        <el-table-column
          label="项目名称"
          prop="name"
          min-width="160"
          sortable
          :sort-method="(a: Event, b: Event) => a.name.localeCompare(b.name, 'zh')"
        />
        <el-table-column
          label="组别"
          prop="group_name"
          min-width="160"
          sortable
          :sort-method="(a: Event, b: Event) => a.group_name.localeCompare(b.group_name, 'zh')"
        />
        <el-table-column
          label="性别"
          prop="gender"
          min-width="160"
          sortable
          :sort-method="(a: Event, b: Event) => a.gender.localeCompare(b.gender, 'zh')"
        >
          <template #default="{ row }">
            <el-tag :type="genderTag(row.gender)" size="small" effect="light">
              {{ row.gender }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          label="类型"
          prop="is_team"
          min-width="160"
          sortable
          :sort-method="(a: Event, b: Event) => Number(a.is_team) - Number(b.is_team)"
        >
          <template #default="{ row }">
            {{ row.is_team ? "团队" : "个人" }}
          </template>
        </el-table-column>
        <el-table-column
          label="决赛队伍"
          prop="final_teams"
          min-width="160"
          sortable
        >
          <template #default="{ row }">
            {{ row.final_teams || "—" }}
          </template>
        </el-table-column>
        <el-table-column label="项目介绍" prop="description" min-width="160">
          <template #default="{ row }">
            <span :class="{ muted: !row.description }">{{ row.description || "—" }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="160">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
        <template #empty>暂无项目，点击右上角「新建项目」添加。</template>
      </el-table>
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="editingId === null ? '新建项目' : '编辑项目'"
      width="560px"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="96px">
        <el-form-item label="项目名称" prop="name">
          <el-input v-model="form.name" placeholder="如 100米、4×100米接力" />
        </el-form-item>
        <div class="form-row">
          <el-form-item label="组别" prop="group_name" class="flex1">
            <el-select
              v-model="form.group_name"
              placeholder="选择组别"
              filterable
              allow-create
              default-first-option
              style="width: 100%"
            >
              <el-option v-for="g in GRADE_GROUPS" :key="g" :label="g" :value="g" />
            </el-select>
          </el-form-item>
          <el-form-item label="性别" prop="gender" class="flex1">
            <el-select v-model="form.gender" style="width: 100%">
              <el-option v-for="g in GENDERS" :key="g" :label="g" :value="g" />
            </el-select>
          </el-form-item>
        </div>
        <div class="form-row">
          <el-form-item label="项目类型" class="flex1">
            <el-radio-group v-model="form.is_team">
              <el-radio-button :value="false">个人</el-radio-button>
              <el-radio-button :value="true">团队</el-radio-button>
            </el-radio-group>
          </el-form-item>
        </div>
        <div class="form-row">
          <el-form-item label="决赛队伍" class="flex1">
            <el-input-number v-model="form.final_teams" :min="0" controls-position="right" />
            <span class="hint">报名队伍数低于此值直接决赛，否则增加预赛</span>
          </el-form-item>
        </div>
        <el-form-item label="项目介绍">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            placeholder="报名人数低于决赛队伍数则直接决赛，否则增加预赛"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 18px;
}
.mb {
  margin-bottom: 16px;
}
.table-card {
  padding: 16px;
}
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}
.count {
  margin-left: auto;
  font-size: 13px;
  color: var(--sfls-text-secondary);
}
.form-row {
  display: flex;
  gap: 16px;
}
.flex1 {
  flex: 1;
}
.hint {
  margin-left: 10px;
  font-size: 12px;
  color: var(--sfls-text-secondary);
}
.muted {
  color: var(--sfls-text-secondary);
}
/* 单元格内容超出列宽时换行显示，而非截断 */
.table-card :deep(.el-table .cell) {
  white-space: normal;
  word-break: break-word;
  line-height: 1.5;
}
</style>
