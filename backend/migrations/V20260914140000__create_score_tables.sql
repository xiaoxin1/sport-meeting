-- 班级得分统计表
CREATE TABLE class_scores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    academic_year_id INT NOT NULL,
    class_team_id INT NOT NULL,
    grade VARCHAR(32) NOT NULL COMMENT '年级',
    class_name VARCHAR(32) NOT NULL COMMENT '班级名称',
    total_score FLOAT NOT NULL DEFAULT 0.0 COMMENT '总分',
    rank_in_grade INT NOT NULL DEFAULT 0 COMMENT '年级内排名',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (academic_year_id) REFERENCES academic_years(id) ON DELETE CASCADE,
    FOREIGN KEY (class_team_id) REFERENCES class_teams(id) ON DELETE CASCADE,
    INDEX idx_academic_year (academic_year_id),
    INDEX idx_class_team (class_team_id),
    INDEX idx_grade (grade)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='班级得分统计';

-- 个人得分统计表
CREATE TABLE athlete_scores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    academic_year_id INT NOT NULL,
    athlete_id INT NOT NULL,
    class_team_id INT NOT NULL,
    grade VARCHAR(32) NOT NULL COMMENT '年级',
    athlete_name VARCHAR(32) NOT NULL COMMENT '运动员姓名',
    total_score FLOAT NOT NULL DEFAULT 0.0 COMMENT '总分',
    rank_in_grade INT NOT NULL DEFAULT 0 COMMENT '年级内排名',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (academic_year_id) REFERENCES academic_years(id) ON DELETE CASCADE,
    FOREIGN KEY (athlete_id) REFERENCES athletes(id) ON DELETE CASCADE,
    FOREIGN KEY (class_team_id) REFERENCES class_teams(id) ON DELETE CASCADE,
    INDEX idx_academic_year (academic_year_id),
    INDEX idx_athlete (athlete_id),
    INDEX idx_class_team (class_team_id),
    INDEX idx_grade (grade)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='个人得分统计';

-- 得分明细表
CREATE TABLE score_details (
    id INT AUTO_INCREMENT PRIMARY KEY,
    academic_year_id INT NOT NULL,
    schedule_lane_id INT NOT NULL,
    event_name VARCHAR(64) NOT NULL COMMENT '项目名称',
    group_name VARCHAR(32) NOT NULL COMMENT '年级',
    gender VARCHAR(8) NOT NULL COMMENT '性别',
    is_team_event BOOLEAN NOT NULL DEFAULT FALSE COMMENT '是否团队项目',
    class_team_id INT NOT NULL,
    athlete_id INT NULL,
    `rank` INT NOT NULL COMMENT '名次',
    result VARCHAR(32) NOT NULL COMMENT '成绩',
    base_score FLOAT NOT NULL COMMENT '基础分',
    is_record_broken BOOLEAN NOT NULL DEFAULT FALSE COMMENT '是否打破记录',
    final_score FLOAT NOT NULL COMMENT '最终得分',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (academic_year_id) REFERENCES academic_years(id) ON DELETE CASCADE,
    FOREIGN KEY (schedule_lane_id) REFERENCES schedule_lanes(id) ON DELETE CASCADE,
    FOREIGN KEY (class_team_id) REFERENCES class_teams(id) ON DELETE CASCADE,
    FOREIGN KEY (athlete_id) REFERENCES athletes(id) ON DELETE CASCADE,
    INDEX idx_academic_year (academic_year_id),
    INDEX idx_schedule_lane (schedule_lane_id),
    INDEX idx_class_team (class_team_id),
    INDEX idx_athlete (athlete_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='得分明细';
