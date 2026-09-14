-- 为决赛填充模拟成绩和排名

-- 更新 4x100米接力成绩（时间类项目，越小越好）
UPDATE schedule_lanes sl
JOIN schedule_groups sg ON sl.group_id = sg.id
JOIN schedule_entries se ON sg.entry_id = se.id
JOIN events e ON se.event_id = e.id
SET
    sl.result = CONCAT(
        FLOOR(50 + RAND() * 20),
        '.',
        LPAD(FLOOR(RAND() * 100), 2, '0')
    )
WHERE se.round_type = '决赛'
    AND e.name = '4x100米接力'
    AND (sl.result = '' OR sl.result IS NULL);

-- 更新 4x400米接力成绩（时间类项目）
UPDATE schedule_lanes sl
JOIN schedule_groups sg ON sl.group_id = sg.id
JOIN schedule_entries se ON sg.entry_id = se.id
JOIN events e ON se.event_id = e.id
SET
    sl.result = CONCAT(
        FLOOR(3 + RAND() * 2),
        ':',
        LPAD(FLOOR(20 + RAND() * 40), 2, '0'),
        '.',
        LPAD(FLOOR(RAND() * 100), 2, '0')
    )
WHERE se.round_type = '决赛'
    AND e.name = '4x400米接力'
    AND (sl.result = '' OR sl.result IS NULL);

-- 为每个决赛赛次的每个小组计算排名
-- 由于 MySQL 不支持窗口函数的 RANK，我们用变量模拟
SET @rank = 0;
SET @prev_group = 0;

CREATE TEMPORARY TABLE temp_lane_ranks AS
SELECT
    sl.id,
    sl.group_id,
    sl.result,
    e.name as event_name,
    e.is_team,
    @rank := IF(@prev_group = sl.group_id, @rank + 1, 1) as new_rank,
    @prev_group := sl.group_id as temp_group
FROM schedule_lanes sl
JOIN schedule_groups sg ON sl.group_id = sg.id
JOIN schedule_entries se ON sg.entry_id = se.id
JOIN events e ON se.event_id = e.id
WHERE se.round_type = '决赛'
    AND sl.result IS NOT NULL
    AND sl.result != ''
ORDER BY sl.group_id,
    CASE
        WHEN e.name LIKE '%米%' OR e.name LIKE '%接力%' THEN sl.result
        ELSE CAST(sl.result AS DECIMAL(10,2))
    END;

-- 更新排名到原表
UPDATE schedule_lanes sl
JOIN temp_lane_ranks tlr ON sl.id = tlr.id
SET sl.rank = tlr.new_rank;

DROP TEMPORARY TABLE temp_lane_ranks;
