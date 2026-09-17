#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试语法是否正确"""

try:
    import sys
    sys.path.insert(0, '.')

    print("正在检查 schedule_gen.py...")
    from app.services import schedule_gen
    print("✓ schedule_gen.py 语法正确")

    print("\n正在检查 schedule_ai.py...")
    from app.services import schedule_ai
    print("✓ schedule_ai.py 语法正确")

    print("\n正在检查 schedule_rules.py...")
    from app.services import schedule_rules
    print("✓ schedule_rules.py 语法正确")

    print("\n所有文件语法检查通过！")

except SyntaxError as e:
    print(f"✗ 语法错误: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
except ImportError as e:
    print(f"✗ 导入错误: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"✗ 其他错误: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
