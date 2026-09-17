<template>
  <div class="scores-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>分数统计</span>
          <el-button type="primary" @click="handleCalculate" :loading="calculating">
            一键统计
          </el-button>
        </div>
      </template>

      <el-tabs v-model="activeTab">
        <!-- 班级统计 -->
        <el-tab-pane label="班级统计" name="class">
          <div class="filter-bar">
            <el-select
              v-model="classGradeFilter"
              placeholder="选择年级"
              clearable
              @change="fetchClassScores"
              style="width: 200px"
            >
              <el-option
                v-for="grade in grades"
                :key="grade"
                :label="grade"
                :value="grade"
              />
            </el-select>
          </div>

          <el-table :data="classScores" border style="width: 100%; margin-top: 16px">
            <el-table-column prop="rank_in_grade" label="排名" width="80" />
            <el-table-column prop="grade" label="年级" width="120" />
            <el-table-column prop="class_name" label="班级" width="120" />
            <el-table-column prop="total_score" label="总分" width="100">
              <template #default="{ row }">
                {{ row.total_score }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120">
              <template #default="{ row }">
                <el-button link type="primary" @click="showClassDetails(row)">
                  查看详情
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- 个人统计 -->
        <el-tab-pane label="个人统计" name="athlete">
          <div class="filter-bar">
            <el-select
              v-model="athleteGradeFilter"
              placeholder="选择年级"
              clearable
              @change="fetchAthleteScores"
              style="width: 200px"
            >
              <el-option
                v-for="grade in grades"
                :key="grade"
                :label="grade"
                :value="grade"
              />
            </el-select>
          </div>

          <el-table :data="athleteScores" border style="width: 100%; margin-top: 16px">
            <el-table-column prop="rank_in_grade" label="排名" width="80" />
            <el-table-column prop="grade" label="年级" width="120" />
            <el-table-column prop="athlete_name" label="姓名" width="120" />
            <el-table-column prop="class_name" label="班级" width="120" />
            <el-table-column prop="total_score" label="总分" width="100">
              <template #default="{ row }">
                {{ row.total_score }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120">
              <template #default="{ row }">
                <el-button link type="primary" @click="showAthleteDetails(row)">
                  查看详情
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 班级得分详情弹窗 -->
    <el-dialog
      v-model="classDetailVisible"
      :title="`${currentClass?.grade} ${currentClass?.class_name} - 得分详情`"
      width="80%"
    >
      <el-table :data="classDetails" border>
        <el-table-column prop="event_name" label="项目" width="150" />
        <el-table-column prop="gender" label="性别" width="80" />
        <el-table-column label="类型" width="100">
          <template #default="{ row }">
            {{ row.is_team_event ? '团队' : '个人' }}
          </template>
        </el-table-column>
        <el-table-column prop="athlete_name" label="运动员" width="120">
          <template #default="{ row }">
            {{ row.athlete_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="rank" label="名次" width="80" />
        <el-table-column prop="result" label="成绩" width="100" />
        <el-table-column prop="base_score" label="基础分" width="100" />
        <el-table-column label="破记录" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.is_record_broken" type="success" size="small">是</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="final_score" label="最终得分" width="100">
          <template #default="{ row }">
            <span :style="{ color: row.is_record_broken ? '#67C23A' : '' }">
              {{ row.final_score }}
            </span>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- 个人得分详情弹窗 -->
    <el-dialog
      v-model="athleteDetailVisible"
      :title="`${currentAthlete?.athlete_name} - 得分详情`"
      width="80%"
    >
      <el-table :data="athleteDetails" border>
        <el-table-column prop="event_name" label="项目" width="150" />
        <el-table-column prop="gender" label="性别" width="80" />
        <el-table-column prop="rank" label="名次" width="80" />
        <el-table-column prop="result" label="成绩" width="100" />
        <el-table-column prop="base_score" label="基础分" width="100" />
        <el-table-column label="破记录" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.is_record_broken" type="success" size="small">是</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="final_score" label="最终得分" width="100">
          <template #default="{ row }">
            <span :style="{ color: row.is_record_broken ? '#67C23A' : '' }">
              {{ row.final_score }}
            </span>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import {
  calculateScores,
  listClassScores,
  listAthleteScores,
  getClassDetails,
  getAthleteDetails,
  type ClassScore,
  type AthleteScore,
  type ScoreDetail,
} from '@/api/score';

const activeTab = ref('class');
const calculating = ref(false);

// 年级列表（固定从一年级到高三）
const grades = ref<string[]>([
  '一年级', '二年级', '三年级', '四年级', '五年级', '六年级',
  '初一', '初二', '初三',
  '高一', '高二', '高三'
]);

// 班级统计
const classScores = ref<ClassScore[]>([]);
const classGradeFilter = ref<string>();
const classDetailVisible = ref(false);
const currentClass = ref<ClassScore>();
const classDetails = ref<ScoreDetail[]>([]);

// 个人统计
const athleteScores = ref<AthleteScore[]>([]);
const athleteGradeFilter = ref<string>();
const athleteDetailVisible = ref(false);
const currentAthlete = ref<AthleteScore>();
const athleteDetails = ref<ScoreDetail[]>([]);

onMounted(async () => {
  await fetchClassScores();
  await fetchAthleteScores();
});

async function handleCalculate() {
  calculating.value = true;
  try {
    const summary = await calculateScores();
    ElMessage.success(
      `统计完成！共 ${summary.total_details} 条得分记录，` +
      `${summary.total_athletes} 名运动员，${summary.total_classes} 个班级`
    );
    await fetchClassScores();
    await fetchAthleteScores();
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '统计失败');
  } finally {
    calculating.value = false;
  }
}

async function fetchClassScores() {
  try {
    classScores.value = await listClassScores(classGradeFilter.value);
  } catch (error: any) {
    ElMessage.error('加载班级得分失败');
  }
}

async function fetchAthleteScores() {
  try {
    athleteScores.value = await listAthleteScores(athleteGradeFilter.value);
  } catch (error: any) {
    ElMessage.error('加载个人得分失败');
  }
}

async function showClassDetails(row: ClassScore) {
  currentClass.value = row;
  try {
    classDetails.value = await getClassDetails(row.class_team_id);
    classDetailVisible.value = true;
  } catch (error: any) {
    ElMessage.error('加载得分详情失败');
  }
}

async function showAthleteDetails(row: AthleteScore) {
  currentAthlete.value = row;
  try {
    athleteDetails.value = await getAthleteDetails(row.athlete_id);
    athleteDetailVisible.value = true;
  } catch (error: any) {
    ElMessage.error('加载得分详情失败');
  }
}
</script>

<style scoped>
.scores-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-bar {
  display: flex;
  gap: 16px;
}
</style>
