-- 重建records表：删除旧表，创建新表结构
DROP TABLE IF EXISTS records;

CREATE TABLE records (
  id INT NOT NULL AUTO_INCREMENT,
  academic_year_id INT NOT NULL,
  event_name VARCHAR(64) NOT NULL,
  group_name VARCHAR(32) NOT NULL,
  gender VARCHAR(8) NOT NULL,
  sort_order INT NOT NULL DEFAULT 0 COMMENT '排序',
  holder_name VARCHAR(64) NOT NULL DEFAULT '',
  result VARCHAR(32) NOT NULL DEFAULT '',
  updated_year VARCHAR(32) NOT NULL DEFAULT '' COMMENT '更新学年',
  created_at DATETIME NOT NULL DEFAULT NOW(),
  PRIMARY KEY (id),
  UNIQUE KEY uq_record_key (academic_year_id, event_name, group_name, gender),
  KEY ix_records_academic_year_id (academic_year_id),
  CONSTRAINT records_ibfk_1 FOREIGN KEY (academic_year_id) REFERENCES academic_years (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
