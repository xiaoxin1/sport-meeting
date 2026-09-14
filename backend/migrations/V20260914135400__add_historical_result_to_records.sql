-- 添加历史成绩字段到 records 表
ALTER TABLE records ADD COLUMN historical_result VARCHAR(32) NOT NULL DEFAULT '' COMMENT '历史成绩';
