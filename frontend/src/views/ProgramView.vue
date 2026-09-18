<template>
  <div class="program-view">
    <div class="header">
      <h2 @dblclick="showDevTools">秩序册</h2>
      <div class="actions">
        <el-button
          v-if="devToolsVisible"
          type="warning"
          @click="generateResults"
          :loading="generatingResults"
        >
          🔧 生成成绩
        </el-button>
        <el-button type="primary" @click="loadPreview" :loading="loading">
          生成预览
        </el-button>
        <el-button type="success" @click="exportExcel" :disabled="!programData">
          导出 Excel
        </el-button>
        <el-button type="warning" @click="exportPdf" :disabled="!programData">
          导出 PDF
        </el-button>
      </div>
    </div>

    <div v-if="programData" class="content">
      <el-tabs v-model="activeTab" type="border-card">
        <!-- 1. 参赛队统计 -->
        <el-tab-pane label="参赛队统计" name="stats">
          <div class="section">
            <el-table :data="programData.team_stats.teams" border stripe>
              <el-table-column prop="index" label="序号" width="80" />
              <el-table-column prop="grade" label="年级" width="100" />
              <el-table-column prop="class_name" label="班级" width="100" />
              <el-table-column prop="male_range" label="男生号码范围" width="150" />
              <el-table-column prop="female_range" label="女生号码范围" width="150" />
              <el-table-column prop="male_count" label="男生人数" width="120" />
              <el-table-column prop="female_count" label="女生人数" width="120" />
            </el-table>

            <div class="grade-summary">
              <h4>年级汇总</h4>
              <el-table :data="gradeSummaryData" border stripe>
                <el-table-column prop="grade" label="年级" width="150" />
                <el-table-column prop="male" label="男生总数" width="150" />
                <el-table-column prop="female" label="女生总数" width="150" />
              </el-table>
            </div>
          </div>
        </el-tab-pane>

        <!-- 2. 代表队名单 -->
        <el-tab-pane label="代表队名单" name="rosters">
          <div class="section">
            <div v-for="roster in programData.team_rosters" :key="roster.index" class="roster-item">
              <h4>{{ roster.index }}. {{ roster.grade }} {{ roster.class_name }}</h4>
              <p><strong>领队：</strong>{{ roster.leader_name || '未设置' }}</p>
              <div class="athletes-grid">
                <div class="athletes-col">
                  <h5>男生</h5>
                  <div v-for="athlete in roster.male_athletes" :key="athlete.number" class="athlete-item">
                    {{ athlete.number }} - {{ athlete.name }}
                  </div>
                  <div v-if="roster.male_athletes.length === 0" class="empty">无</div>
                </div>
                <div class="athletes-col">
                  <h5>女生</h5>
                  <div v-for="athlete in roster.female_athletes" :key="athlete.number" class="athlete-item">
                    {{ athlete.number }} - {{ athlete.name }}
                  </div>
                  <div v-if="roster.female_athletes.length === 0" class="empty">无</div>
                </div>
              </div>
            </div>
          </div>
        </el-tab-pane>

        <!-- 3. 竞赛日程 -->
        <el-tab-pane label="竞赛日程" name="schedule">
          <div class="section">
            <div v-for="period in programData.schedule" :key="`${period.day}-${period.period}`" class="schedule-period">
              <h4>第{{ period.day }}天 {{ period.period }}</h4>
              <el-table :data="period.events" border stripe>
                <el-table-column prop="index" label="序号" width="80" />
                <el-table-column prop="group_name" label="年级" width="100" />
                <el-table-column prop="gender" label="性别" width="80" />
                <el-table-column prop="event_name" label="项目名称" min-width="150" />
                <el-table-column prop="round_type" label="赛次" width="100" />
                <el-table-column prop="participant_count" label="人数" width="80" />
                <el-table-column label="组数" width="120">
                  <template #default="{ row }">
                    {{ row.group_count }}组/取{{ row.advance_count }}名
                  </template>
                </el-table-column>
                <el-table-column prop="time" label="时间" width="150" />
              </el-table>
            </div>
          </div>
        </el-tab-pane>

        <!-- 4. 项目分组表 -->
        <el-tab-pane label="项目分组表" name="grouping">
          <div class="section">
            <div v-for="period in programData.grouping" :key="`grp-${period.day}-${period.period}`" class="grouping-period">
              <h4>第{{ period.day }}天 {{ period.period }}</h4>
              <div v-for="event in period.events" :key="event.index" class="event-grouping">
                <div class="event-header">
                  <strong>{{ event.index }}. {{ event.group_name }} {{ event.gender }} {{ event.event_name }} {{ event.round_type }}</strong>
                  <span class="event-meta">
                    人数：{{ event.participant_count }} |
                    {{ event.group_count }}组/取{{ event.advance_count }}名 |
                    时间：{{ event.time }}
                  </span>
                </div>
                <div v-for="group in event.groups" :key="group.group_index" class="group-detail">
                  <strong>第{{ group.group_index }}组：</strong>
                  <el-table :data="group.lanes" border stripe size="small">
                    <el-table-column prop="lane" label="道次" width="80" />
                    <el-table-column v-if="!event.is_team" prop="bib_number" label="号码" width="100" />
                    <el-table-column v-if="!event.is_team" prop="athlete_name" label="学生" width="120" />
                    <el-table-column prop="class_name" label="班级" width="120" />
                  </el-table>
                </div>
              </div>
            </div>
          </div>
        </el-tab-pane>

        <!-- 5. 最高记录 -->
        <el-tab-pane label="最高记录" name="records">
          <div class="section">
            <el-table :data="programData.records.rows" border stripe>
              <el-table-column label="项目" width="150">
                <template #default="{ row }">
                  {{ row.event_name }}
                </template>
              </el-table-column>
              <el-table-column label="性别" width="80">
                <template #default="{ row }">
                  {{ row.gender }}
                </template>
              </el-table-column>
              <el-table-column
                v-for="grade in programData.records.grades"
                :key="grade"
                :label="grade"
                min-width="200"
              >
                <el-table-column label="保持者" width="100">
                  <template #default="{ row }">
                    {{ row.records[grade]?.holder_name || '' }}
                  </template>
                </el-table-column>
                <el-table-column label="历史成绩" width="100">
                  <template #default="{ row }">
                    {{ row.records[grade]?.result || '' }}
                  </template>
                </el-table-column>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>
      </el-tabs>

      <!-- 打印专用布局：屏幕隐藏，打印/导出 PDF 时纵向平铺五个章节 -->
      <div class="print-layout">
        <h1 class="print-title">秩序册</h1>

        <!-- 1. 参赛队统计 -->
        <section class="print-section">
          <h2>参赛队统计</h2>
          <table class="print-table">
            <thead>
              <tr>
                <th>序号</th><th>年级</th><th>班级</th>
                <th>男生号码范围</th><th>女生号码范围</th>
                <th>男生人数</th><th>女生人数</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="t in programData.team_stats.teams" :key="t.index">
                <td>{{ t.index }}</td><td>{{ t.grade }}</td><td>{{ t.class_name }}</td>
                <td>{{ t.male_range }}</td><td>{{ t.female_range }}</td>
                <td>{{ t.male_count }}</td><td>{{ t.female_count }}</td>
              </tr>
            </tbody>
          </table>
          <h3>年级汇总</h3>
          <table class="print-table">
            <thead>
              <tr><th>年级</th><th>男生总数</th><th>女生总数</th></tr>
            </thead>
            <tbody>
              <tr v-for="s in gradeSummaryData" :key="s.grade">
                <td>{{ s.grade }}</td><td>{{ s.male }}</td><td>{{ s.female }}</td>
              </tr>
            </tbody>
          </table>
        </section>

        <!-- 2. 代表队名单 -->
        <section class="print-section">
          <h2>代表队名单</h2>
          <div v-for="roster in programData.team_rosters" :key="roster.index" class="print-roster">
            <h3>{{ roster.index }}. {{ roster.grade }} {{ roster.class_name }}</h3>
            <p><strong>领队：</strong>{{ roster.leader_name || '未设置' }}</p>
            <p><strong>男生：</strong>
              <span v-if="roster.male_athletes.length">
                {{ roster.male_athletes.map(a => `${a.number}-${a.name}`).join('、') }}
              </span>
              <span v-else>无</span>
            </p>
            <p><strong>女生：</strong>
              <span v-if="roster.female_athletes.length">
                {{ roster.female_athletes.map(a => `${a.number}-${a.name}`).join('、') }}
              </span>
              <span v-else>无</span>
            </p>
          </div>
        </section>

        <!-- 3. 竞赛日程 -->
        <section class="print-section">
          <h2>竞赛日程</h2>
          <div v-for="period in programData.schedule" :key="`p-${period.day}-${period.period}`">
            <h3>第{{ period.day }}天 {{ period.period }}</h3>
            <table class="print-table">
              <thead>
                <tr>
                  <th>序号</th><th>年级</th><th>性别</th><th>项目名称</th>
                  <th>赛次</th><th>人数</th><th>组数/取名</th><th>时间</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="event in period.events" :key="event.index">
                  <td>{{ event.index }}</td><td>{{ event.group_name }}</td>
                  <td>{{ event.gender }}</td><td>{{ event.event_name }}</td>
                  <td>{{ event.round_type }}</td><td>{{ event.participant_count }}</td>
                  <td>{{ event.group_count }}组/取{{ event.advance_count }}名</td>
                  <td>{{ event.time }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <!-- 4. 项目分组表 -->
        <section class="print-section">
          <h2>项目分组表</h2>
          <div v-for="period in programData.grouping" :key="`g-${period.day}-${period.period}`">
            <h3>第{{ period.day }}天 {{ period.period }}</h3>
            <div v-for="event in period.events" :key="event.index" class="print-event">
              <p class="print-event-title">
                <strong>{{ event.index }}. {{ event.group_name }} {{ event.gender }}
                {{ event.event_name }} {{ event.round_type }}</strong>
                （人数：{{ event.participant_count }}，{{ event.group_count }}组/取{{ event.advance_count }}名，{{ event.time }}）
              </p>
              <div v-for="group in event.groups" :key="group.group_index" class="print-group">
                <table class="print-table">
                  <thead>
                    <tr>
                      <th :colspan="event.is_team ? 2 : 4">第{{ group.group_index }}组</th>
                    </tr>
                    <tr>
                      <th>道次</th>
                      <th v-if="!event.is_team">号码</th>
                      <th v-if="!event.is_team">学生</th>
                      <th>班级</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="lane in group.lanes" :key="lane.lane">
                      <td>{{ lane.lane }}</td>
                      <td v-if="!event.is_team">{{ lane.bib_number }}</td>
                      <td v-if="!event.is_team">{{ lane.athlete_name }}</td>
                      <td>{{ lane.class_name }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </section>

        <!-- 5. 最高记录 -->
        <section class="print-section print-section--landscape">
          <h2>最高记录</h2>
          <table class="print-table">
            <thead>
              <tr>
                <th rowspan="2">项目</th>
                <th rowspan="2">性别</th>
                <th v-for="grade in programData.records.grades" :key="grade" colspan="2">{{ grade }}</th>
              </tr>
              <tr>
                <template v-for="grade in programData.records.grades" :key="`h-${grade}`">
                  <th>保持者</th>
                  <th>历史成绩</th>
                </template>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, i) in programData.records.rows" :key="i">
                <td>{{ row.event_name }}</td>
                <td>{{ row.gender }}</td>
                <template v-for="grade in programData.records.grades" :key="`c-${grade}`">
                  <td>{{ row.records[grade]?.holder_name || '' }}</td>
                  <td>{{ row.records[grade]?.result || '' }}</td>
                </template>
              </tr>
            </tbody>
          </table>
        </section>
      </div>
    </div>

    <el-empty v-else-if="!loading" description="点击「生成预览」查看秩序册内容" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import client from '@/api/client';
import * as XLSX from 'xlsx';

interface ProgramData {
  team_stats: {
    teams: Array<{
      index: number;
      grade: string;
      class_name: string;
      male_range: string;
      female_range: string;
      male_count: number;
      female_count: number;
    }>;
    grade_summary: Record<string, { male: number; female: number }>;
  };
  team_rosters: Array<{
    index: number;
    grade: string;
    class_name: string;
    leader_name: string;
    male_athletes: Array<{ number: string; name: string }>;
    female_athletes: Array<{ number: string; name: string }>;
  }>;
  schedule: Array<{
    day: number;
    period: string;
    events: Array<any>;
  }>;
  grouping: Array<{
    day: number;
    period: string;
    events: Array<any>;
  }>;
  records: {
    grades: string[];
    rows: Array<{
      event_name: string;
      gender: string;
      records: Record<string, { holder_name: string; result: string }>;
    }>;
  };
}

const loading = ref(false);
const programData = ref<ProgramData | null>(null);
const activeTab = ref('stats');
const devToolsVisible = ref(false);
const generatingResults = ref(false);

const gradeSummaryData = computed(() => {
  if (!programData.value) return [];
  const summary = programData.value.team_stats.grade_summary;
  return Object.keys(summary)
    .sort()
    .map(grade => ({
      grade,
      male: summary[grade].male,
      female: summary[grade].female,
    }));
});

async function loadPreview() {
  try {
    await ElMessageBox.confirm(
      '生成预览将加载全部秩序册数据，可能需要一些时间。确定继续吗？',
      '确认生成',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'info',
      }
    );
  } catch {
    return;
  }

  loading.value = true;
  try {
    const response = await client.get('/program/preview');
    programData.value = response.data;
    ElMessage.success('秩序册预览加载成功');
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '加载失败');
    console.error('加载秩序册失败:', error);
  } finally {
    loading.value = false;
  }
}

function exportExcel() {
  if (!programData.value) {
    ElMessage.warning('请先生成预览');
    return;
  }

  try {
    const wb = XLSX.utils.book_new();

    // 1. 参赛队统计
    const teamStatsSheet = XLSX.utils.json_to_sheet(
      programData.value.team_stats.teams.map(t => ({
        序号: t.index,
        年级: t.grade,
        班级: t.class_name,
        男生号码范围: t.male_range,
        女生号码范围: t.female_range,
        男生人数: t.male_count,
        女生人数: t.female_count,
      }))
    );

    // 添加年级汇总
    const summaryData = gradeSummaryData.value.map(s => ({
      年级: s.grade,
      男生总数: s.male,
      女生总数: s.female,
    }));
    XLSX.utils.sheet_add_json(teamStatsSheet, summaryData, {
      origin: -1,
      skipHeader: false,
    });

    XLSX.utils.book_append_sheet(wb, teamStatsSheet, '参赛队统计');

    // 2. 代表队名单
    const rostersData: any[] = [];
    programData.value.team_rosters.forEach(roster => {
      rostersData.push({
        序号: roster.index,
        年级: roster.grade,
        班级: roster.class_name,
        领队: roster.leader_name,
        男生: roster.male_athletes.map(a => `${a.number}-${a.name}`).join('、'),
        女生: roster.female_athletes.map(a => `${a.number}-${a.name}`).join('、'),
      });
    });
    const rostersSheet = XLSX.utils.json_to_sheet(rostersData);
    XLSX.utils.book_append_sheet(wb, rostersSheet, '代表队名单');

    // 3. 竞赛日程
    const scheduleData: any[] = [];
    programData.value.schedule.forEach(period => {
      period.events.forEach(event => {
        scheduleData.push({
          时段: `第${period.day}天${period.period}`,
          序号: event.index,
          年级: event.group_name,
          性别: event.gender,
          项目名称: event.event_name,
          赛次: event.round_type,
          人数: event.participant_count,
          组数信息: `${event.group_count}组/取${event.advance_count}名`,
          时间: event.time,
        });
      });
    });
    const scheduleSheet = XLSX.utils.json_to_sheet(scheduleData);
    XLSX.utils.book_append_sheet(wb, scheduleSheet, '竞赛日程');

    // 4. 项目分组表
    const groupingData: any[] = [];
    programData.value.grouping.forEach(period => {
      period.events.forEach(event => {
        event.groups.forEach((group: any) => {
          group.lanes.forEach((lane: any) => {
            groupingData.push({
              时段: `第${period.day}天${period.period}`,
              项目: `${event.group_name}${event.gender}${event.event_name}${event.round_type}`,
              组别: `第${group.group_index}组`,
              道次: lane.lane,
              号码: lane.bib_number || '',
              姓名: lane.athlete_name || '',
              班级: lane.class_name,
            });
          });
        });
      });
    });
    const groupingSheet = XLSX.utils.json_to_sheet(groupingData);
    XLSX.utils.book_append_sheet(wb, groupingSheet, '项目分组表');

    // 5. 最高记录
    const recordsData: any[] = [];
    programData.value.records.rows.forEach(row => {
      const recordRow: any = {
        项目: row.event_name,
        性别: row.gender,
      };
      programData.value!.records.grades.forEach(grade => {
        const record = row.records[grade];
        recordRow[grade] = record
          ? `${record.holder_name} ${record.result}`
          : '';
      });
      recordsData.push(recordRow);
    });
    const recordsSheet = XLSX.utils.json_to_sheet(recordsData);
    XLSX.utils.book_append_sheet(wb, recordsSheet, '最高记录');

    // 导出文件
    const timestamp = new Date().toISOString().slice(0, 19).replace(/[:-]/g, '').replace('T', '_');
    XLSX.writeFile(wb, `秩序册_${timestamp}.xlsx`);
    ElMessage.success('秩序册导出成功');
  } catch (error) {
    ElMessage.error('导出失败');
    console.error('导出秩序册失败:', error);
  }
}

function exportPdf() {
  if (!programData.value) {
    ElMessage.warning('请先生成预览');
    return;
  }
  // 打印布局在 @media print 下呈现为五个章节纵向平铺，
  // 用户在浏览器打印弹窗中选择「另存为 PDF」即可。
  window.print();
}

function showDevTools() {
  devToolsVisible.value = !devToolsVisible.value;
  if (devToolsVisible.value) {
    ElMessage.info('🔧 开发者工具已启用');
  }
}

async function generateResults() {
  try {
    await ElMessageBox.confirm(
      '此操作将为所有预赛和决赛生成随机成绩。确定继续吗？',
      '生成成绩',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    );
  } catch {
    return;
  }

  generatingResults.value = true;
  try {
    const response = await client.post('/program/generate-results');
    ElMessage.success(`成绩生成成功！已生成 ${response.data.results_count} 条成绩记录`);
    // 重新加载预览
    await loadPreview();
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '生成成绩失败');
    console.error('生成成绩失败:', error);
  } finally {
    generatingResults.value = false;
  }
}
</script>

<style scoped>
.program-view {
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header h2 {
  margin: 0;
}

.actions {
  display: flex;
  gap: 12px;
}

.content {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.section {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.section h3 {
  margin: 0 0 16px 0;
  color: #303133;
  font-size: 18px;
}

.grade-summary {
  margin-top: 24px;
}

.grade-summary h4 {
  margin: 0 0 12px 0;
  color: #606266;
  font-size: 16px;
}

.roster-item {
  margin-bottom: 24px;
  padding: 16px;
  border: 1px solid #EBEEF5;
  border-radius: 4px;
}

.roster-item h4 {
  margin: 0 0 8px 0;
  color: #303133;
}

.roster-item p {
  margin: 0 0 12px 0;
  color: #606266;
}

.athletes-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.athletes-col h5 {
  margin: 0 0 8px 0;
  color: #909399;
  font-size: 14px;
}

.athlete-item {
  padding: 4px 0;
  color: #606266;
  font-size: 14px;
}

.empty {
  color: #C0C4CC;
  font-style: italic;
}

.schedule-period,
.grouping-period {
  margin-bottom: 24px;
}

.schedule-period h4,
.grouping-period h4 {
  margin: 0 0 12px 0;
  padding: 8px 12px;
  background: #F5F7FA;
  border-left: 4px solid #409EFF;
  color: #303133;
  font-size: 16px;
}

.event-grouping {
  margin-bottom: 24px;
  padding: 12px;
  border: 1px solid #EBEEF5;
  border-radius: 4px;
}

.event-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #EBEEF5;
}

.event-meta {
  color: #909399;
  font-size: 14px;
  font-weight: normal;
}

.group-detail {
  margin-top: 12px;
}

.group-detail strong {
  display: block;
  margin-bottom: 8px;
  color: #606266;
}

.record-result {
  color: #909399;
  font-size: 12px;
}

.record-best {
  color: #f56c6c;
  font-weight: bold;
}

/* 打印布局默认在屏幕上隐藏 */
.print-layout {
  display: none;
}
</style>

<!-- 打印/导出 PDF 专用样式（非 scoped，需作用于整个文档） -->
<style>
@media print {
  /* 解除布局容器的固定高度/滚动限制，否则绝对定位内容会被裁剪成一屏 */
  html,
  body,
  #app,
  .layout,
  .el-container,
  .el-main {
    height: auto !important;
    max-height: none !important;
    overflow: visible !important;
  }

  /* 直接隐藏侧边栏、页头、操作按钮和屏幕版 tab（display:none 不占空间） */
  .sidebar,
  .header,
  .program-view > .header,
  .el-tabs {
    display: none !important;
  }

  .el-main {
    padding: 0 !important;
  }

  .print-layout {
    display: block !important;
    width: 100%;
    padding: 0;
    color: #000;
    font-size: 12px;
  }

  .print-title {
    text-align: center;
    font-size: 22px;
    margin: 0 0 16px;
  }

  /* 每个章节另起一页；用默认（竖版）页，避免标题与首章各占空白页 */
  .print-section {
    page-break-before: always;
    break-before: page;
  }

  /* 标题和第一章同页，不额外分页 */
  .print-title,
  .print-section:first-of-type {
    page-break-before: avoid;
    break-before: auto;
  }

  /* 最高记录列多，横屏打印，并撑满横版页宽（A4 横向 29.7cm - 左右各 1.5cm 边距） */
  .print-section--landscape {
    page: landscape;
    width: 26.7cm;
  }

  /* 最高记录列多，字号和内边距再调小，尽量放进一页 */
  .print-section--landscape .print-table th,
  .print-section--landscape .print-table td {
    padding: 1px 2px;
    font-size: 8px;
    line-height: 1.1;
  }

  .print-section > h2 {
    font-size: 16px;
    margin: 0 0 12px;
    padding-bottom: 4px;
    border-bottom: 2px solid #000;
    text-align: center;
  }

  .print-section h3 {
    font-size: 14px;
    margin: 14px 0 6px;
  }

  .print-table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 10px;
  }

  .print-table th,
  .print-table td {
    border: 1px solid #000;
    padding: 3px 6px;
    text-align: center;
    font-size: 11px;
  }

  .print-table thead {
    display: table-header-group;
  }

  /* 避免行、分组被跨页截断 */
  .print-table tr,
  .print-roster,
  .print-group {
    page-break-inside: avoid;
    break-inside: avoid;
  }

  .print-roster {
    margin-bottom: 10px;
  }

  .print-roster p,
  .print-event-title {
    margin: 2px 0;
    text-align: left;
  }

  .print-event {
    margin-bottom: 10px;
  }

  /* 默认页：竖版。标题+前四章都用它，不再命名，避免页名切换产生空白页 */
  @page {
    size: A4 portrait;
    margin: 1.5cm;
  }

  /* 仅最高记录用横版命名页 */
  @page landscape {
    size: A4 landscape;
    margin: 1.5cm;
  }
}
</style>
