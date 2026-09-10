<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from "element-plus";
import {
  activateYear,
  createYear,
  deleteYear,
  listYears,
  updateYear,
  type AcademicYear,
} from "@/api/academicYears";
import { useAcademicYearStore } from "@/stores/academicYear";

const yearStore = useAcademicYearStore();
const years = ref<AcademicYear[]>([]);
const loading = ref(false);

const dialogVisible = ref(false);
const editingId = ref<number | null>(null);
const formRef = ref<FormInstance>();
const form = reactive({ name: "", dateRange: [] as string[] });

const rules: FormRules = {
  name: [
    { required: true, message: "请输入学年名称，如 2026~2027", trigger: "blur" },
    {
      pattern: /^\d{4}[~-]\d{4}$/,
      message: "格式应为 2026~2027",
      trigger: "blur",
    },
  ],
};

async function load() {
  loading.value = true;
  try {
    years.value = await listYears();
  } finally {
    loading.value = false;
  }
}

onMounted(load);

function openCreate() {
  editingId.value = null;
  form.name = "";
  form.dateRange = [];
  dialogVisible.value = true;
}

function openEdit(row: AcademicYear) {
  editingId.value = row.id;
  form.name = row.name;
  form.dateRange =
    row.meet_start_date && row.meet_end_date
      ? [row.meet_start_date, row.meet_end_date]
      : [];
  dialogVisible.value = true;
}

async function submit() {
  if (!formRef.value) return;
  await formRef.value.validate(async (valid) => {
    if (!valid) return;
    const payload = {
      name: form.name,
      meet_start_date: form.dateRange[0] ?? null,
      meet_end_date: form.dateRange[1] ?? null,
    };
    try {
      if (editingId.value === null) {
        await createYear(payload);
        ElMessage.success("已创建学年");
      } else {
        await updateYear(editingId.value, payload);
        ElMessage.success("已保存");
      }
      dialogVisible.value = false;
      await load();
      await yearStore.refresh();
    } catch (e: any) {
      ElMessage.error(e?.response?.data?.detail || "操作失败");
    }
  });
}

async function handleActivate(row: AcademicYear) {
  await activateYear(row.id);
  ElMessage.success(`已切换到 ${row.name}`);
  await load();
  await yearStore.refresh();
}

async function handleDelete(row: AcademicYear) {
  await ElMessageBox.confirm(
    `删除学年「${row.name}」将清除其下全部数据，确定继续？`,
    "危险操作",
    { type: "warning", confirmButtonText: "删除", confirmButtonClass: "el-button--danger" },
  );
  await deleteYear(row.id);
  ElMessage.success("已删除");
  await load();
  await yearStore.refresh();
}
</script>

<template>
  <div>
    <div class="page-head">
      <div>
        <h2 class="sfls-page-title">学年设置</h2>
        <p class="sfls-page-subtitle">每个学年是一套独立数据，切换学年即切换全站数据上下文。</p>
      </div>
      <el-button type="primary" :icon="'Plus'" @click="openCreate">新建学年</el-button>
    </div>

    <div class="sfls-card table-card">
      <el-table :data="years" v-loading="loading" stripe>
        <el-table-column label="学年" min-width="160">
          <template #default="{ row }">
            <span class="year-name">{{ row.name }}</span>
            <el-tag v-if="row.is_active" type="success" size="small" class="active-tag">
              当前学年
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="运动会时间" min-width="220">
          <template #default="{ row }">
            <span v-if="row.meet_start_date">
              {{ row.meet_start_date }} 至 {{ row.meet_end_date }}
            </span>
            <span v-else class="muted">未设置</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240" align="right">
          <template #default="{ row }">
            <el-button
              v-if="!row.is_active"
              link
              type="primary"
              @click="handleActivate(row)"
            >
              设为当前
            </el-button>
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
        <template #empty>暂无学年，点击右上角「新建学年」开始。</template>
      </el-table>
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="editingId === null ? '新建学年' : '编辑学年'"
      width="460px"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="96px">
        <el-form-item label="学年名称" prop="name">
          <el-input v-model="form.name" placeholder="如 2026~2027" />
        </el-form-item>
        <el-form-item label="运动会时间">
          <el-date-picker
            v-model="form.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 100%"
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
.table-card {
  padding: 8px 16px 16px;
}
.year-name {
  font-weight: 600;
}
.active-tag {
  margin-left: 8px;
}
.muted {
  color: var(--sfls-text-secondary);
}
</style>
