-- 修改records表：删除achieved_year字段，添加sort_order字段
ALTER TABLE records DROP COLUMN achieved_year;
ALTER TABLE records ADD COLUMN sort_order INT NOT NULL DEFAULT 0 COMMENT '排序' AFTER record_type;
