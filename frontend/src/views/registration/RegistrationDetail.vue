<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import {
  getClassDetail,
  getRegistrationConfig,
  saveRegistration,
  type ClassTeamDetail,
  type RegistrationAthleteInput,
  type RegistrationConfig,
} from "@/api/registration";
import type { Event } from "@/api/events";

const props = defineProps<{
  modelValue: boolean;
  classId: number | null;
  events: Event[];
}>();
const emit = defineEmits<{
  "update:modelValue": [v: boolean];
  saved: [];
}>();

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit("update:modelValue", v),
});

const detail = ref<ClassTeamDetail | null>(null);
const loading = ref(false);
const saving = ref(false);
const config = ref<RegistrationConfig>({
  hint: "每个项目限报2人，每位运动员限报1项，可兼报接力",
  max_per_event: 2,
  max_events_per_person: 1,
});

// 本地草稿：只有点击「保存」才会提交生效
interface DraftAthlete extends RegistrationAthleteInput {
  _key: number;
  number: number | null;
}
const draftAthletes = ref<DraftAthlete[]>([]);
const draftMale = ref(0);
const draftFemale = ref(0);
const selectedTeamEvents = ref<number[]>([]);
let keySeq = 1;

// 个人项目 / 团队项目 按年级过滤（组别 == 班级年级）
const personEvents = computed(() =>
  props.events.filter((e) => !e.is_team && e.group_name === detail.value?.grade),
);
// 按运动员性别过滤个人项目：男生看男子+混合，女生看女子+混合
function personEventsFor(gender: string) {
  return personEvents.value.filter((e) => e.gender === gender || e.gender === "混合");
}
const teamEvents = computed(() =>
  props.events.filter((e) => e.is_team && e.group_name === detail.value?.grade),
);

function isRelay(name: string): boolean {
  return name.includes("*") || name.includes("接力");
}

async function load() {
  if (props.classId === null) return;
  loading.value = true;
  try {
    const [d, cfg] = await Promise.all([
      getClassDetail(props.classId),
      getRegistrationConfig(),
    ]);
    detail.value = d;
    config.value = cfg;
    draftMale.value = d.male_count;
    draftFemale.value = d.female_count;
    selectedTeamEvents.value = [...d.team_event_ids];
    draftAthletes.value = d.athletes.map((a) => ({
      _key: keySeq++,
      id: a.id,
      name: a.name,
      gender: a.gender,
      event_ids: [...a.event_ids],
      number: a.number,
    }));
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "加载失败");
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

// ---- 草稿编辑 ----
function addRow() {
  draftAthletes.value.push({
    _key: keySeq++,
    id: null,
    name: "",
    gender: "男",
    event_ids: [],
    number: null,
  });
}

function removeRow(key: number) {
  draftAthletes.value = draftAthletes.value.filter((a) => a._key !== key);
}

// 切换性别后，清除不再匹配新性别的已选个人项目
function onGenderChange(row: DraftAthlete) {
  const allowed = new Set(personEventsFor(row.gender).map((e) => e.id));
  row.event_ids = row.event_ids.filter((id) => allowed.has(id));
}

// 客户端校验（与后端一致，配置驱动）。接力项目豁免。
function validate(): string | null {
  const maxPer = config.value.max_per_event;
  const maxEvents = config.value.max_events_per_person;
  const relayIds = new Set(personEvents.value.filter((e) => isRelay(e.name)).map((e) => e.id));
  const nameOf = new Map(personEvents.value.map((e) => [e.id, e.name] as const));

  const perEvent = new Map<number, number>();
  let maleInList = 0;
  let femaleInList = 0;
  for (const a of draftAthletes.value) {
    if (!a.name.trim()) return "存在未填写姓名的运动员";
    if (a.gender === "女") femaleInList += 1;
    else maleInList += 1;
    let nonRelay = 0;
    for (const eid of a.event_ids) {
      perEvent.set(eid, (perEvent.get(eid) || 0) + 1);
      if (!relayIds.has(eid)) nonRelay += 1;
    }
    if (nonRelay > maxEvents) {
      return `「${a.name}」报名了 ${nonRelay} 个个人项目，每位运动员限报 ${maxEvents} 项（接力除外）`;
    }
  }
  for (const [eid, cnt] of perEvent) {
    if (relayIds.has(eid)) continue;
    if (cnt > maxPer) {
      return `项目「${nameOf.get(eid) || eid}」报名了 ${cnt} 人，每个项目限报 ${maxPer} 人`;
    }
  }
  // 运动员名单中的男/女人数必须与上方填写的男/女生人数一致
  if (maleInList !== draftMale.value) {
    return `运动员名单中男生 ${maleInList} 人，与填写的男生人数 ${draftMale.value} 不一致`;
  }
  if (femaleInList !== draftFemale.value) {
    return `运动员名单中女生 ${femaleInList} 人，与填写的女生人数 ${draftFemale.value} 不一致`;
  }
  return null;
}

async function save() {
  if (props.classId === null) return;
  const err = validate();
  if (err) {
    ElMessage.error(err);
    return;
  }
  saving.value = true;
  try {
    const d = await saveRegistration(props.classId, {
      male_count: draftMale.value,
      female_count: draftFemale.value,
      athletes: draftAthletes.value.map((a) => ({
        id: a.id,
        name: a.name.trim(),
        gender: a.gender,
        event_ids: a.event_ids,
      })),
      team_event_ids: selectedTeamEvents.value,
    });
    detail.value = d;
    // 用返回结果刷新号码等
    draftAthletes.value = d.athletes.map((a) => ({
      _key: keySeq++,
      id: a.id,
      name: a.name,
      gender: a.gender,
      event_ids: [...a.event_ids],
      number: a.number,
    }));
    ElMessage.success("报名已保存");
    emit("saved");
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "保存失败");
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <el-drawer
    v-model="visible"
    size="60%"
    :title="detail ? `${detail.grade}${detail.class_name} · 报名详情` : '报名详情'"
  >
    <div v-loading="loading">
      <template v-if="detail">
        <div class="meta sfls-card">
          <span>领队：{{ detail.leader_name || "—" }}</span>
          <div class="count-item">
            <span>男生人数</span>
            <el-input-number v-model="draftMale" :min="0" :max="10" size="small" controls-position="right" />
          </div>
          <div class="count-item">
            <span>女生人数</span>
            <el-input-number v-model="draftFemale" :min="0" :max="10" size="small" controls-position="right" />
          </div>
        </div>

        <!-- 个人项目报名 -->
        <div class="section-head">
          <h3>个人项目报名</h3>
          <el-button type="primary" size="small" :icon="'Plus'" @click="addRow">添加运动员</el-button>
        </div>
        <el-table :data="draftAthletes" row-key="_key" stripe border>
          <el-table-column label="姓名" min-width="130">
            <template #default="{ row }">
              <el-input v-model="row.name" placeholder="姓名" size="small" />
            </template>
          </el-table-column>
          <el-table-column label="性别" min-width="130">
            <template #default="{ row }">
              <el-radio-group v-model="row.gender" size="small" @change="onGenderChange(row)">
                <el-radio-button value="男">男</el-radio-button>
                <el-radio-button value="女">女</el-radio-button>
              </el-radio-group>
            </template>
          </el-table-column>
          <el-table-column label="号码" min-width="80">
            <template #default="{ row }">
              <span v-if="row.number">{{ row.number }}</span>
              <span v-else class="muted">未生成</span>
            </template>
          </el-table-column>
          <el-table-column label="报名项目" min-width="240">
            <template #default="{ row }">
              <el-select v-model="row.event_ids" multiple filterable size="small" placeholder="选择个人项目" style="width: 100%">
                <el-option
                  v-for="e in personEventsFor(row.gender)"
                  :key="e.id"
                  :label="`${e.name}（${e.gender}）`"
                  :value="e.id"
                />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="操作" min-width="80">
            <template #default="{ row }">
              <el-button link type="danger" @click="removeRow(row._key)">删除</el-button>
            </template>
          </el-table-column>
          <template #empty>暂无个人报名，点击「添加运动员」。</template>
        </el-table>

        <!-- 团队项目报名 -->
        <div class="section-head">
          <h3>团队项目报名</h3>
        </div>
        <el-checkbox-group v-model="selectedTeamEvents" class="team-group">
          <el-checkbox v-for="e in teamEvents" :key="e.id" :value="e.id" border>
            {{ e.name }}（{{ e.gender }}）
          </el-checkbox>
        </el-checkbox-group>
        <el-empty v-if="!teamEvents.length" description="该年级暂无团队项目" :image-size="60" />

        <!-- 保存 -->
        <div class="save-bar">
          <p class="hint">{{ config.hint }}</p>
          <el-button type="primary" :loading="saving" @click="save">保存</el-button>
        </div>
      </template>
    </div>
  </el-drawer>
</template>

<style scoped>
.meta {
  display: flex;
  align-items: center;
  gap: 28px;
  padding: 14px 18px;
  margin-bottom: 20px;
  font-size: 14px;
}
.count-item {
  display: flex;
  align-items: center;
  gap: 8px;
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
.save-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-top: 28px;
  padding-top: 16px;
  border-top: 1px solid var(--sfls-border);
}
.save-bar .hint {
  margin: 0;
  color: #e11d48;
  font-weight: 600;
  font-size: 13px;
}
</style>
