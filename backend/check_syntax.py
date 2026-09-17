import sys

try:
    with open('app/services/schedule_gen.py', 'r', encoding='utf-8') as f:
        code = f.read()
    compile(code, 'app/services/schedule_gen.py', 'exec')
    print("语法检查通过")
except SyntaxError as e:
    print(f"语法错误在第 {e.lineno} 行:")
    print(f"  {e.text}")
    print(f"  {' ' * (e.offset - 1)}^")
    print(f"错误信息: {e.msg}")
    sys.exit(1)
