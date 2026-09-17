<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from "element-plus";
import {
  createClass,
  deleteClass,
  generateNumbers,
  listClasses,
  updateClass,
  type ClassTeam,
  type ClassTeamInput,
} from "@/api/registration";
import { listEvents, type Event } from "@/api/events";
import { GRADE_GROUPS } from "@/config/constants";
import { compareGrade, naturalCompare } from "@/config/sort";
import { useAcademicYearStore } from "@/stores/academicYear";
import { useAuthStore } from "@/stores/auth";
import RegistrationDetail from "./registration/RegistrationDetail.vue";

const yearStore = useAcademicYearStore();
const auth = useAuthStore();
const isAdmin = computed(() => auth.isAdmin);
const classes = ref<ClassTeam[]>([]);
const events = ref<Event[]>([]);
const loading = ref(false);
const generating = ref(false);

// 搜索与筛选
const keyword = ref("");
const filterGroup = ref("");

const filteredClasses = computed(() =>
  classes.value.filter((c) => {
    const okKw = !keyword.value || (c.leader_name || "").includes(keyword.value);
    const okGroup = !filterGroup.value || c.grade === filterGroup.value;
    return okKw && okGroup;
  }),
);

const dialogVisible = ref(false);
const editingId = ref<number | null>(null);
const formRef = ref<FormInstance>();
const form = reactive<ClassTeamInput>({
  grade: "",
  class_name: "",
  leader_name: "",
  male_count: 0,
  female_count: 0,
  password: "",
});
const rules: FormRules = {
  grade: [{ required: true, message: "请选择年级", trigger: "change" }],
  class_name: [{ required: true, message: "请输入班级", trigger: "blur" }],
  leader_name: [{ required: true, message: "请输入领队姓名", trigger: "blur" }],
};

// 详情抽屉
const detailVisible = ref(false);
const detailClassId = ref<number | null>(null);

async function load() {
  loading.value = true;
  try {
    const data = await listClasses();
    // 默认按 年级 + 班级 排序
    data.sort(
      (a, b) => compareGrade(a.grade, b.grade) || naturalCompare(a.class_name, b.class_name),
    );
    classes.value = data;
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "加载失败");
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  if (!yearStore.loaded) await yearStore.refresh();
  events.value = await listEvents();
  await load();
});

function openCreate() {
  editingId.value = null;
  Object.assign(form, {
    grade: "",
    class_name: "",
    leader_name: "",
    male_count: 0,
    female_count: 0,
    password: "",
  });
  dialogVisible.value = true;
}

function openEdit(row: ClassTeam) {
  editingId.value = row.id;
  Object.assign(form, {
    grade: row.grade,
    class_name: row.class_name,
    leader_name: row.leader_name,
    male_count: row.male_count,
    female_count: row.female_count,
    password: row.password || "",
  });
  dialogVisible.value = true;
}

async function submit() {
  if (!formRef.value) return;
  await formRef.value.validate(async (valid) => {
    if (!valid) return;
    try {
      if (editingId.value === null) {
        await createClass({ ...form });
        ElMessage.success("已创建班级");
      } else {
        await updateClass(editingId.value, { ...form });
        ElMessage.success("已保存");
      }
      dialogVisible.value = false;
      await load();
    } catch (e: any) {
      ElMessage.error(e?.response?.data?.detail || "操作失败");
    }
  });
}

async function handleDelete(row: ClassTeam) {
  await ElMessageBox.confirm(
    `删除「${row.grade}${row.class_name}」将清除其全部报名数据，确定继续？`,
    "危险操作",
    { type: "warning", confirmButtonText: "删除" },
  );
  await deleteClass(row.id);
  ElMessage.success("已删除");
  await load();
}

function openDetail(row: ClassTeam) {
  detailClassId.value = row.id;
  detailVisible.value = true;
}

async function handleGenerate() {
  await ElMessageBox.confirm(
    "将对所有班级重新生成号码（号码从 301 起，每班连续 10+10）。确定继续？",
    "生成号码",
    { type: "info", confirmButtonText: "生成" },
  );
  generating.value = true;
  try {
    const res = await generateNumbers();
    ElMessage.success(`已为 ${res.assigned} 名学生生成号码`);
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "生成失败");
  } finally {
    generating.value = false;
  }
}
</script>

<template>
  <div>
    <div class="page-head">
      <div>
        <h2 class="sfls-page-title">报名</h2>
        <p class="sfls-page-subtitle">以班级为单位报名。男/女生人数各不超过 10 人。</p>
      </div>
      <div class="actions" v-if="isAdmin">
        <el-button
          :icon="'Postcard'"
          :loading="generating"
          :disabled="!yearStore.active"
          @click="handleGenerate"
        >
          生成号码
        </el-button>
        <el-button type="primary" :icon="'Plus'" :disabled="!yearStore.active" @click="openCreate">
          手动添加
        </el-button>
      </div>
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
          placeholder="搜索领队姓名"
          :prefix-icon="'Search'"
          clearable
          style="width: 220px"
        />
        <el-select v-model="filterGroup" placeholder="全部年级" clearable style="width: 160px">
          <el-option v-for="g in GRADE_GROUPS" :key="g" :label="g" :value="g" />
        </el-select>
        <span class="count">共 {{ filteredClasses.length }} 个班级</span>
      </div>

      <el-table :data="filteredClasses" v-loading="loading" stripe>
        <el-table-column
          label="年级"
          prop="grade"
          min-width="140"
          sortable
          :sort-method="(a: ClassTeam, b: ClassTeam) => compareGrade(a.grade, b.grade)"
        />
        <el-table-column
          label="班级"
          prop="class_name"
          min-width="140"
          sortable
          :sort-method="(a: ClassTeam, b: ClassTeam) => naturalCompare(a.class_name, b.class_name)"
        />
        <el-table-column label="领队姓名" prop="leader_name" min-width="140">
          <template #default="{ row }">
            <span :class="{ muted: !row.leader_name }">{{ row.leader_name || "—" }}</span>
          </template>
        </el-table-column>
        <el-table-column label="男生人数" prop="male_count" min-width="120" sortable />
        <el-table-column label="女生人数" prop="female_count" min-width="120" sortable />
        <el-table-column v-if="isAdmin" label="密码" prop="password" min-width="140">
          <template #default="{ row }">
            <span :class="{ muted: !row.password }">{{ row.password || "—" }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="200">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">查看详情</el-button>
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button v-if="isAdmin" link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
        <template #empty>暂无班级，点击右上角「手动添加」开始。</template>
      </el-table>
    </div>

    <!-- 班级新增/编辑 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingId === null ? '添加班级' : '编辑班级'"
      width="480px"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="88px">
        <div class="form-row">
          <el-form-item label="年级" prop="grade" class="flex1">
            <el-select
              v-model="form.grade"
              placeholder="选择年级"
              filterable
              allow-create
              default-first-option
              :disabled="!isAdmin"
              style="width: 100%"
            >
              <el-option v-for="g in GRADE_GROUPS" :key="g" :label="g" :value="g" />
            </el-select>
          </el-form-item>
          <el-form-item label="班级" prop="class_name" class="flex1">
            <el-input v-model="form.class_name" placeholder="如 1班" :disabled="!isAdmin" />
          </el-form-item>
        </div>
        <el-form-item label="领队姓名" prop="leader_name">
          <el-input v-model="form.leader_name" placeholder="领队姓名" :disabled="!isAdmin" />
        </el-form-item>
        <el-form-item v-if="isAdmin" label="登录密码">
          <el-input v-model="form.password" placeholder="留空则默认 admin_sfls" clearable />
        </el-form-item>
        <div class="form-row">
          <el-form-item label="男生人数" class="flex1">
            <el-input-number
              v-model="form.male_count"
              :min="0"
              :max="10"
              controls-position="right"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item label="女生人数" class="flex1">
            <el-input-number
              v-model="form.female_count"
              :min="0"
              :max="10"
              controls-position="right"
              style="width: 100%"
            />
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>

    <RegistrationDetail
      v-model="detailVisible"
      :class-id="detailClassId"
      :events="events"
      @saved="load"
    />
  </div>
</template>

<style scoped>
.page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 18px;
}
.actions {
  display: flex;
  gap: 10px;
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
  margin-bottom: 16px;
}
.toolbar .count {
  margin-left: auto;
  color: var(--sfls-text-secondary);
  font-size: 13px;
}
.form-row {
  display: flex;
  gap: 16px;
}
.flex1 {
  flex: 1;
}
.muted {
  color: var(--sfls-text-secondary);
}
.table-card :deep(.el-table .cell) {
  white-space: normal;
  word-break: break-word;
  line-height: 1.5;
}
</style>
