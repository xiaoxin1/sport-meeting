-- 清空排名
UPDATE schedule_lanes SET `rank` = NULL;

-- 创建临时存储过程来设置排名
DELIMITER //

CREATE PROCEDURE set_finals_ranks()
BEGIN
    DECLARE done INT DEFAULT FALSE;
    DECLARE v_group_id INT;
    DECLARE v_lane_id INT;
    DECLARE v_rank INT;

    DECLARE group_cursor CURSOR FOR
        SELECT DISTINCT sg.id
        FROM schedule_groups sg
        JOIN schedule_entries se ON sg.entry_id = se.id
        WHERE se.round_type = '决赛';

    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;

    OPEN group_cursor;

    read_loop: LOOP
        FETCH group_cursor INTO v_group_id;
        IF done THEN
            LEAVE read_loop;
        END IF;

        -- 为当前小组的每条记录设置排名
        SET v_rank = 0;

        -- 使用子查询为每个小组排序并设置排名
        UPDATE schedule_lanes sl
        JOIN (
            SELECT id, (@rn := @rn + 1) as rn
            FROM schedule_lanes
            CROSS JOIN (SELECT @rn := 0) r
            WHERE group_id = v_group_id
            ORDER BY CAST(SUBSTRING_INDEX(result, ':', -1) AS DECIMAL(10,2))
        ) ranked ON sl.id = ranked.id
        SET sl.`rank` = ranked.rn
        WHERE sl.group_id = v_group_id;

    END LOOP;

    CLOSE group_cursor;
END//

DELIMITER ;

-- 执行存储过程
CALL set_finals_ranks();

-- 删除存储过程
DROP PROCEDURE set_finals_ranks;
