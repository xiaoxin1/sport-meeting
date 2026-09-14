-- 获取当前学年ID
SELECT @year_id := id FROM academic_years WHERE is_active = 1 LIMIT 1;

-- 为100米男子(一年级)创建决赛
INSERT INTO schedule_entries (academic_year_id, event_id, day_index, period, round_type, order_no, group_count, advance_count, start_time, end_time, venue)
VALUES (@year_id, 10, 1, '上午', '决赛', 100, 1, 0, '09:00', '09:10', '田径场');

SET @entry_id = LAST_INSERT_ID();

-- 创建一个组
INSERT INTO schedule_groups (entry_id, group_no) VALUES (@entry_id, 1);
SET @group_id = LAST_INSERT_ID();

-- 插入前6名运动员作为决赛选手，并设置成绩和排名
INSERT INTO schedule_lanes (group_id, lane_no, athlete_id, class_team_id, result, `rank`)
SELECT @group_id,
       @row_num := @row_num + 1,
       ae.athlete_id,
       a.class_team_id,
       CONCAT('1', FLOOR(1 + RAND() * 3), '.', LPAD(FLOOR(RAND() * 100), 2, '0')),
       @row_num
FROM athlete_events ae
JOIN athletes a ON ae.athlete_id = a.id
CROSS JOIN (SELECT @row_num := 0) r
WHERE ae.event_id = 10
ORDER BY RAND()
LIMIT 6;

-- 为100米女子(一年级)创建决赛
INSERT INTO schedule_entries (academic_year_id, event_id, day_index, period, round_type, order_no, group_count, advance_count, start_time, end_time, venue)
VALUES (@year_id, 11, 1, '上午', '决赛', 101, 1, 0, '09:15', '09:25', '田径场');

SET @entry_id = LAST_INSERT_ID();
INSERT INTO schedule_groups (entry_id, group_no) VALUES (@entry_id, 1);
SET @group_id = LAST_INSERT_ID();

INSERT INTO schedule_lanes (group_id, lane_no, athlete_id, class_team_id, result, `rank`)
SELECT @group_id,
       @row_num := @row_num + 1,
       ae.athlete_id,
       a.class_team_id,
       CONCAT('1', FLOOR(3 + RAND() * 2), '.', LPAD(FLOOR(RAND() * 100), 2, '0')),
       @row_num
FROM athlete_events ae
JOIN athletes a ON ae.athlete_id = a.id
CROSS JOIN (SELECT @row_num := 0) r
WHERE ae.event_id = 11
ORDER BY RAND()
LIMIT 6;

-- 为200米男子(一年级)创建决赛
INSERT INTO schedule_entries (academic_year_id, event_id, day_index, period, round_type, order_no, group_count, advance_count, start_time, end_time, venue)
VALUES (@year_id, 12, 1, '上午', '决赛', 102, 1, 0, '09:30', '09:40', '田径场');

SET @entry_id = LAST_INSERT_ID();
INSERT INTO schedule_groups (entry_id, group_no) VALUES (@entry_id, 1);
SET @group_id = LAST_INSERT_ID();

INSERT INTO schedule_lanes (group_id, lane_no, athlete_id, class_team_id, result, `rank`)
SELECT @group_id,
       @row_num := @row_num + 1,
       ae.athlete_id,
       a.class_team_id,
       CONCAT('2', FLOOR(5 + RAND() * 5), '.', LPAD(FLOOR(RAND() * 100), 2, '0')),
       @row_num
FROM athlete_events ae
JOIN athletes a ON ae.athlete_id = a.id
CROSS JOIN (SELECT @row_num := 0) r
WHERE ae.event_id = 12
ORDER BY RAND()
LIMIT 6;

SELECT 'Created individual event finals' as status;
