import ast
from io import StringIO
from contextlib import redirect_stdout

from app.core.tool.decorator import tool


@tool(
    name="code_executor",
    description="Execute Python code in a sandbox and return the output. Only pure Python allowed.",
    parameters={
        "code": {"type": "string", "description": "Python code to execute", "required": True},
    },
)
async def code_executor(code: str) -> str:
    """Execute Python code in a restricted sandbox. Captures stdout."""
    blocked = ["import ", "open(", "__import__", "eval(", "exec(", "os.", "subprocess"]
    for kw in blocked:
        if kw in code:
            return f"Blocked: code contains '{kw}'"

    try:
        compiled = compile(code, "<sandbox>", "exec", flags=ast.PyCF_ONLY_AST)
    except SyntaxError as e:
        return f"Syntax error: {e}"

    local_ns: dict = {}
    output = StringIO()
    try:
        with redirect_stdout(output):
            exec(compile(compiled, "<sandbox>", "exec"), {"__builtins__": {}}, local_ns)
        result = output.getvalue()
        return result if result else "Code executed successfully (no output)"
    except Exception as e:
        return f"Execution error: {e}"
