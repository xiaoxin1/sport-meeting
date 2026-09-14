-- 将 updated_year 字段重命名为 current_holder_name
ALTER TABLE records CHANGE COLUMN updated_year current_holder_name VARCHAR(64) NOT NULL DEFAULT '';
