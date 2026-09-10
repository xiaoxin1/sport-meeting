import { defineStore } from "pinia";
import { ref } from "vue";
import { getActiveYear, type AcademicYear } from "@/api/academicYears";

/** 当前激活学年：贯穿全站的数据上下文。 */
export const useAcademicYearStore = defineStore("academicYear", () => {
  const active = ref<AcademicYear | null>(null);
  const loaded = ref(false);

  async function refresh() {
    active.value = await getActiveYear();
    loaded.value = true;
  }

  return { active, loaded, refresh };
});
