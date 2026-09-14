<template>
  <div class="record-view">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>最高记录</span>
          <el-button type="primary" @click="showCreateDialog">新增项目</el-button>
        </div>
      </template>

      <div class="toolbar">
        <el-input
          v-model="keyword"
          placeholder="搜索项目名称"
          :prefix-icon="'Search'"
          clearable
          style="width: 220px"
        />
        <el-select v-model="filterGroup" placeholder="全部年级" clearable style="width: 160px">
          <el-option v-for="g in GRADE_GROUPS" :key="g" :label="g" :value="g" />
        </el-select>
        <span class="count">共 {{ filteredRecords.length }} 条记录</span>
      </div>

      <el-table :data="paginatedRecords" border stripe row-key="id">
        <el-table-column type="index" label="序号" width="60" />
        <el-table-column prop="event_name" label="项目名称" width="120" />
        <el-table-column prop="group_name" label="年级" width="100" />
        <el-table-column prop="gender" label="性别" width="80" />
        <el-table-column prop="historical_result" label="历史成绩" width="120">
          <template #default="{ row }">
            {{ row.historical_result || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="holder_name" label="历史记录保持者" width="150" />
        <el-table-column prop="result" label="当前成绩" width="120">
          <template #default="{ row }">
            {{ row.result || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="current_holder_name" label="当前成绩创造者" width="150">
          <template #default="{ row }">
            {{ row.current_holder_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" link @click="showEditDialog(row)">
              编辑
            </el-button>
            <el-button type="danger" size="small" link @click="handleDelete(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100, 1000]"
        :total="filteredRecords.length"
        layout="total, sizes, prev, pager, next, jumper"
        style="margin-top: 16px; justify-content: flex-end"
      />
    </el-card>

    <!-- 新增项目对话框 -->
    <el-dialog v-model="createDialogVisible" title="新增项目" width="500px">
      <el-form :model="createForm" label-width="100px">
        <el-form-item label="项目名称" required>
          <el-input v-model="createForm.event_name" placeholder="例如：100米" />
        </el-form-item>
        <el-form-item label="年级" required>
          <el-select v-model="createForm.group_name" placeholder="请选择">
            <el-option label="一年级" value="一年级" />
            <el-option label="二年级" value="二年级" />
            <el-option label="三年级" value="三年级" />
            <el-option label="四年级" value="四年级" />
            <el-option label="五年级" value="五年级" />
            <el-option label="六年级" value="六年级" />
            <el-option label="初一" value="初一" />
            <el-option label="初二" value="初二" />
            <el-option label="初三" value="初三" />
            <el-option label="高一" value="高一" />
            <el-option label="高二" value="高二" />
            <el-option label="高三" value="高三" />
          </el-select>
        </el-form-item>
        <el-form-item label="性别" required>
          <el-select v-model="createForm.gender" placeholder="请选择">
            <el-option label="男" value="男" />
            <el-option label="女" value="女" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleCreate">确定</el-button>
      </template>
    </el-dialog>

    <!-- 编辑记录对话框 -->
    <el-dialog v-model="editDialogVisible" title="编辑记录" width="600px">
      <el-form v-if="editForm" :model="editForm" label-width="150px">
        <el-form-item label="项目名称">
          <el-input v-model="editForm.event_name" disabled />
        </el-form-item>
        <el-form-item label="年级">
          <el-input v-model="editForm.group_name" disabled />
        </el-form-item>
        <el-form-item label="性别">
          <el-input v-model="editForm.gender" disabled />
        </el-form-item>
        <el-form-item label="历史成绩">
          <el-input v-model="editForm.historical_result" placeholder="例如：12.50" />
        </el-form-item>
        <el-form-item label="历史记录保持者">
          <el-input v-model="editForm.holder_name" placeholder="姓名" />
        </el-form-item>
        <el-form-item label="当前成绩">
          <el-input v-model="editForm.result" placeholder="例如：12.35" />
        </el-form-item>
        <el-form-item label="当前成绩创造者">
          <el-input v-model="editForm.current_holder_name" placeholder="姓名" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleUpdate">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import type { Record, RecordCreate } from "@/api/record";
import { getRecords, createRecord, updateRecord, deleteRecord } from "@/api/record";
import { getActiveYear, listYears } from "@/api/academicYears";
import type { AcademicYear } from "@/api/academicYears";
import { GRADE_GROUPS } from "@/config/constants";

const records = ref<Record[]>([]);
const currentYearName = ref("");
const academicYears = ref<AcademicYear[]>([]);
const createDialogVisible = ref(false);
const editDialogVisible = ref(false);

// 搜索与筛选
const keyword = ref("");
const filterGroup = ref("");

const filteredRecords = computed(() =>
  records.value.filter((r) => {
    const okKw = !keyword.value || r.event_name.includes(keyword.value);
    const okGroup = !filterGroup.value || r.group_name === filterGroup.value;
    return okKw && okGroup;
  }),
);

// 分页
const currentPage = ref(1);
const pageSize = ref(10);
const paginatedRecords = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  const end = start + pageSize.value;
  return filteredRecords.value.slice(start, end);
});

const createForm = ref<RecordCreate>({
  event_name: "",
  group_name: "",
  gender: "",
});

const editForm = ref<Record | null>(null);

async function fetchRecords() {
  try {
    records.value = await getRecords();
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || "加载记录失败");
  }
}

async function fetchCurrentYear() {
  try {
    const year = await getActiveYear();
    if (year) {
      currentYearName.value = year.name;
    }
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || "加载学年失败");
  }
}

async function fetchAcademicYears() {
  try {
    academicYears.value = await listYears();
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || "加载学年列表失败");
  }
}

function showCreateDialog() {
  createForm.value = {
    event_name: "",
    group_name: "",
    gender: "",
  };
  createDialogVisible.value = true;
}

async function handleCreate() {
  if (!createForm.value.event_name || !createForm.value.group_name || !createForm.value.gender) {
    ElMessage.warning("请填写所有必填项");
    return;
  }

  try {
    await createRecord(createForm.value);
    ElMessage.success("新增成功");
    createDialogVisible.value = false;
    await fetchRecords();
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || "新增失败");
  }
}

function showEditDialog(row: Record) {
  editForm.value = { ...row };
  editDialogVisible.value = true;
}

async function handleUpdate() {
  if (!editForm.value) return;

  try {
    await updateRecord(editForm.value.id, {
      holder_name: editForm.value.holder_name,
      result: editForm.value.result,
      current_holder_name: editForm.value.current_holder_name,
      historical_result: editForm.value.historical_result,
    });
    ElMessage.success("更新成功");
    editDialogVisible.value = false;
    await fetchRecords();
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || "更新失败");
  }
}

async function handleDelete(row: Record) {
  try {
    await ElMessageBox.confirm(
      `确定删除 ${row.event_name} ${row.group_name} ${row.gender} 吗？`,
      "提示",
      { type: "warning" }
    );
    await deleteRecord(row.id);
    ElMessage.success("删除成功");
    await fetchRecords();
  } catch (error: any) {
    if (error !== "cancel") {
      ElMessage.error(error.response?.data?.detail || "删除失败");
    }
  }
}

onMounted(async () => {
  await fetchCurrentYear();
  await fetchAcademicYears();
  await fetchRecords();
});
</script>

<style scoped>
.record-view {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
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

.record-best {
  color: #f56c6c;
  font-weight: bold;
}
</style>
