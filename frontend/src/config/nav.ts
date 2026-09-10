/** 侧边栏导航配置。功能模块按需求逐个开启，未实现的先标记 disabled。 */
export interface NavItem {
  index: string;
  title: string;
  icon: string;
  disabled?: boolean;
}

export const navItems: NavItem[] = [
  { index: "/academic-years", title: "学年设置", icon: "Calendar" },
  { index: "/events", title: "项目", icon: "Trophy" },
  { index: "/registration", title: "报名", icon: "User", disabled: true },
  { index: "/schedule", title: "竞赛日程", icon: "Clock", disabled: true },
  { index: "/groupings", title: "项目分组", icon: "Grid", disabled: true },
  { index: "/records", title: "最高记录", icon: "Medal", disabled: true },
  { index: "/handbook", title: "秩序册生成", icon: "Document", disabled: true },
  { index: "/results", title: "成绩统计", icon: "DataLine", disabled: true },
  { index: "/scores", title: "分数统计", icon: "Histogram", disabled: true },
];
