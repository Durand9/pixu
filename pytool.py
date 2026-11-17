import ast
import subprocess
import sys

ALLOWED_NODES = (
    ast.Module, ast.Expr, ast.Assign, ast.AugAssign, ast.Name, ast.Load,
    ast.Store, ast.Constant, ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare,
    ast.IfExp, ast.If, ast.For, ast.While, ast.Break, ast.Continue, ast.Pass,
    ast.Call, ast.keyword, ast.List, ast.Tuple, ast.Dict, ast.Set,
    ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp,
    ast.comprehension, ast.Subscript, ast.Slice, ast.FunctionDef,
    ast.arguments, ast.arg, ast.Return, ast.Attribute, ast.JoinedStr,
    ast.FormattedValue, ast.alias, ast.operator, ast.unaryop, ast.boolop,
    ast.cmpop,
)

SAFE_CALLS = {
    "print", "range", "len", "sum", "min", "max", "abs", "round", "int",
    "float", "str", "sorted", "list", "set", "dict", "tuple", "enumerate",
    "zip", "pow", "divmod", "all", "any", "bool", "reversed",
}

SAFE_METHODS = {
    "append", "extend", "add", "pop", "sort", "keys", "values", "items", "count",
}


def check_code(code):
    """Raises ValueError if the code uses anything outside the allowed list."""
    tree = ast.parse(code)
    defined = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(a.name != "math" or a.asname for a in node.names):
                raise ValueError("only 'import math' is allowed")
            continue
        if not isinstance(node, ALLOWED_NODES):
            raise ValueError(f"not allowed: {type(node).__name__}")
        if isinstance(node, ast.Name) and node.id.startswith("__"):
            raise ValueError("names starting with __ are not allowed")
        if isinstance(node, ast.Attribute):
            is_math = isinstance(node.value, ast.Name) and node.value.id == "math"
            if node.attr.startswith("_") or not (is_math or node.attr in SAFE_METHODS):
                raise ValueError(f"attribute not allowed: {node.attr}")
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                if func.id not in SAFE_CALLS and func.id not in defined:
                    raise ValueError(f"function not allowed: {func.id}")
            elif not isinstance(func, ast.Attribute):
                raise ValueError("this kind of call is not allowed")


def run_python(code, timeout=10):
    """Checks the code, runs it in a separate process, returns what it printed."""
    check_code(code)
    result = subprocess.run(
        [sys.executable, "-I", "-c", code],
        capture_output=True,
        text=True,
        timeout=timeout,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip()[-300:])
    return result.stdout.strip()[:2000]