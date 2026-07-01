import ast

MAX_CODE_SIZE = 50 * 1024  # 50 KB

ALLOWED_IMPORTS = {'numpy', 'requests', 'sia', 'collections', 'math'}

FORBIDDEN_NAMES = {
    'eval', 'exec', 'open', '__import__', 'getattr', 'setattr', 
    'delattr', 'compile', 'globals', 'locals', 'input', 'dir', 
    'vars', 'help', 'breakpoint'
}

class SecurityVisitor(ast.NodeVisitor):
    def visit_Import(self, node):
        for alias in node.names:
            root_module = alias.name.split('.')[0]
            if root_module not in ALLOWED_IMPORTS:
                raise ValueError(f"Import not allowed: {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if not node.module:
            raise ValueError("Relative imports are not allowed")
        root_module = node.module.split('.')[0]
        if root_module not in ALLOWED_IMPORTS:
            raise ValueError(f"Import not allowed: {node.module}")
        self.generic_visit(node)

    def visit_Name(self, node):
        if node.id in FORBIDDEN_NAMES:
            raise ValueError(f"Use of '{node.id}' is forbidden")
        if node.id.startswith('__') and node.id != '__name__':
            raise ValueError(f"Identifiers starting with '__' are forbidden: {node.id}")
        self.generic_visit(node)

    def visit_Attribute(self, node):
        if node.attr.startswith('__'):
            raise ValueError(f"Access to private/dunder attribute '{node.attr}' is forbidden")
        self.generic_visit(node)

def validate_code(code: str) -> None:
    # 1. Size check
    if len(code.encode('utf-8')) > MAX_CODE_SIZE:
        raise ValueError("Code size exceeds the maximum limit of 50 KB")
    
    # 2. Syntax validation and AST traversal
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise ValueError(f"Syntax Error: {e.msg} (line {e.lineno}, column {e.offset})")
    except Exception as e:
        raise ValueError(f"Failed to parse code: {str(e)}")
    
    # 3. Security AST check
    visitor = SecurityVisitor()
    visitor.visit(tree)
