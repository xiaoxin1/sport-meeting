"""为决赛成绩设置排名"""
import pymysql

# 连接数据库
conn = pymysql.connect(
    host='localhost',
    port=3306,
    user='root',
    password='sfls_root_pwd_change_me',
    database='sfls_meeting',
    charset='utf8mb4'
)

cursor = conn.cursor()

# 查询所有决赛的小组和成绩
query = """
SELECT sg.id as group_id, sl.id as lane_id, sl.result, e.name as event_name
FROM schedule_lanes sl
JOIN schedule_groups sg ON sl.group_id = sg.id
JOIN schedule_entries se ON sg.entry_id = se.id
JOIN events e ON se.event_id = e.id
WHERE se.round_type = '决赛'
    AND sl.result IS NOT NULL
    AND sl.result != ''
ORDER BY sg.id, sl.result
"""

cursor.execute(query)
rows = cursor.fetchall()

# 按小组分组
from collections import defaultdict
groups = defaultdict(list)
for row in rows:
    group_id, lane_id, result, event_name = row
    groups[group_id].append((lane_id, result, event_name))

# 为每个小组设置排名
update_count = 0
for group_id, lanes in groups.items():
    # 按成绩排序（时间类越小越好，已经在查询中排序了）
    for rank, (lane_id, result, event_name) in enumerate(lanes, 1):
        cursor.execute(
            "UPDATE schedule_lanes SET rank = %s WHERE id = %s",
            (rank, lane_id)
        )
        update_count += 1

conn.commit()
print(f"已更新 {update_count} 条决赛成绩排名")

cursor.close()
conn.close()
