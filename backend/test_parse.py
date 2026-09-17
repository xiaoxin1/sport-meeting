import ast
import sys

try:
    with open('app/services/schedule_gen.py', 'r', encoding='utf-8') as f:
        code = f.read()

    tree = ast.parse(code, filename='schedule_gen.py')
    print("AST解析成功")
    print(f"发现 {len([n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)])} 个函数定义")

except SyntaxError as e:
    print(f"语法错误:")
    print(f"  行号: {e.lineno}")
    print(f"  列号: {e.offset}")
    print(f"  文本: {e.text}")
    print(f"  消息: {e.msg}")
    sys.exit(1)
except Exception as e:
    print(f"其他错误: {type(e).__name__}: {e}")
    sys.exit(1)
