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
  { index: "/registration", title: "报名", icon: "User" },
  { index: "/schedule", title: "竞赛日程", icon: "Clock" },
  { index: "/records", title: "最高记录", icon: "Medal" },
  { index: "/program", title: "秩序册", icon: "Document" },
  { index: "/scores", title: "分数统计", icon: "Histogram" },
  { index: "/settings", title: "系统设置", icon: "Tools" },
];
