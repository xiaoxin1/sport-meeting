-- 创建最高记录表
CREATE TABLE records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    academic_year_id INT NOT NULL,
    event_name VARCHAR(64) NOT NULL COMMENT '项目名称',
    group_name VARCHAR(32) NOT NULL COMMENT '年级组',
    gender VARCHAR(8) NOT NULL COMMENT '性别',
    record_type VARCHAR(16) NOT NULL COMMENT '记录类型：历史记录/本年记录',
    holder_name VARCHAR(64) NOT NULL DEFAULT '' COMMENT '保持者姓名',
    result VARCHAR(32) NOT NULL DEFAULT '' COMMENT '成绩',
    achieved_year VARCHAR(32) NOT NULL DEFAULT '' COMMENT '创建年份',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_records_academic_year FOREIGN KEY (academic_year_id)
        REFERENCES academic_years(id) ON DELETE CASCADE,
    CONSTRAINT uq_record_key UNIQUE (academic_year_id, event_name, group_name, gender, record_type),
    INDEX idx_records_year (academic_year_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='项目最高记录';
