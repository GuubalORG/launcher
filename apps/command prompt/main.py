from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTextEdit, QPushButton, QLabel, QSplitter)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import sys
import re


class Interpreter:
    """Parses the code into an Abstract Syntax Tree (AST)"""
    
    def __init__(self):
        self.variables = {}
    
    def parse(self, code):
        """Parse code into executable AST"""
        lines = code.strip().split('\n')
        return self.parse_block(lines, 0)[0]
    
    def parse_block(self, lines, start_idx):
        """Parse a block of code, returns (statements, next_line_idx)"""
        statements = []
        i = start_idx
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                i += 1
                continue
            
            # Calculate indentation
            indent = len(lines[i]) - len(lines[i].lstrip())
            
            # If we hit dedent, return
            if i > start_idx and indent < len(lines[start_idx]) - len(lines[start_idx].lstrip()):
                break
            
            # Parse different statement types
            if line.startswith('print ') or line == 'print':
                # Handle both "print variable" and "print" with no args
                expr = line[6:].strip() if len(line) > 6 else ''
                statements.append(('print', self.parse_expression(expr) if expr else ''))
                i += 1
                
            elif line.startswith('if '):
                condition = line[3:].rstrip(':')
                block, next_i = self.parse_block(lines, i + 1)
                statements.append(('if', condition, block))
                i = next_i
                
            elif line.startswith('while '):
                condition = line[6:].rstrip(':')
                block, next_i = self.parse_block(lines, i + 1)
                statements.append(('while', condition, block))
                i = next_i
                
            elif line.startswith('for '):
                # for i in range(10):
                match = re.match(r'for\s+(\w+)\s+in\s+range\((.+?)\):', line)
                if match:
                    var_name = match.group(1)
                    range_expr = match.group(2)
                    block, next_i = self.parse_block(lines, i + 1)
                    statements.append(('for', var_name, range_expr, block))
                    i = next_i
                else:
                    raise SyntaxError(f"Invalid for loop syntax: {line}")
                    
            elif '=' in line and not any(op in line.split('=')[0] for op in ['==', '!=', '<=', '>=']):
                # Variable assignment
                parts = line.split('=', 1)
                var_name = parts[0].strip()
                value = parts[1].strip()
                statements.append(('assign', var_name, self.parse_expression(value)))
                i += 1
            else:
                i += 1
        
        return statements, i
    
    def parse_expression(self, expr):
        """Parse an expression (for now, just return the string)"""
        return expr.strip()


class Executor:
    """Executes the parsed AST"""
    
    def __init__(self, output_callback):
        self.output_callback = output_callback
        self.variables = {}
    
    def execute(self, statements):
        """Execute a list of statements"""
        for stmt in statements:
            self.execute_statement(stmt)
    
    def execute_statement(self, stmt):
        """Execute a single statement"""
        stmt_type = stmt[0]
        
        if stmt_type == 'print':
            value = self.evaluate(stmt[1])
            self.output_callback(str(value))
            
        elif stmt_type == 'assign':
            var_name = stmt[1]
            value = self.evaluate(stmt[2])
            self.variables[var_name] = value
            
        elif stmt_type == 'if':
            condition = self.evaluate(stmt[1])
            if condition:
                self.execute(stmt[2])
                
        elif stmt_type == 'while':
            max_iterations = 10000  # Prevent infinite loops
            iterations = 0
            while self.evaluate(stmt[1]) and iterations < max_iterations:
                self.execute(stmt[2])
                iterations += 1
            if iterations >= max_iterations:
                raise RuntimeError("Maximum loop iterations exceeded")
                
        elif stmt_type == 'for':
            var_name = stmt[1]
            range_expr = stmt[2]
            block = stmt[3]
            
            # Evaluate range
            range_val = self.evaluate(f"range({range_expr})")
            for i in range_val:
                self.variables[var_name] = i
                self.execute(block)
    
    def evaluate(self, expr):
        """Evaluate an expression"""
        if not expr:
            return ''
            
        expr = expr.strip()
        
        # String literal
        if (expr.startswith('"') and expr.endswith('"')) or \
           (expr.startswith("'") and expr.endswith("'")):
            return expr[1:-1]
        
        # Check if it's just a variable name (no operators)
        if expr.isidentifier() and expr in self.variables:
            return self.variables[expr]
        
        # Number literal
        try:
            if '.' in expr:
                return float(expr)
            return int(expr)
        except ValueError:
            pass
        
        # Build a safe evaluation context with variables
        eval_context = {"__builtins__": {}}
        eval_context.update(self.variables)
        
        # Add allowed functions
        allowed_names = {
            'range': range,
            'len': len,
            'str': str,
            'int': int,
            'float': float,
        }
        eval_context.update(allowed_names)
        
        # Evaluate the expression safely
        try:
            return eval(expr, {"__builtins__": {}}, eval_context)
        except Exception as e:
            raise RuntimeError(f"Error evaluating expression '{expr}': {e}")


class CodeEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SimpleLang IDE")
        self.setGeometry(100, 100, 900, 600)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        layout = QVBoxLayout(central_widget)
        
        # Title
        title = QLabel("SimpleLang IDE")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Splitter for code editor and output
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Code editor
        editor_container = QWidget()
        editor_layout = QVBoxLayout(editor_container)
        editor_label = QLabel("Code Editor:")
        editor_layout.addWidget(editor_label)
        
        self.code_editor = QTextEdit()
        self.code_editor.setFont(QFont("Courier New", 10))
        self.code_editor.setPlaceholderText("Write your code here...\n\nExample:\n"
                                           "x = 5\nprint x\n\nfor i in range(3):\n    print i")
        editor_layout.addWidget(self.code_editor)
        splitter.addWidget(editor_container)
        
        # Output display
        output_container = QWidget()
        output_layout = QVBoxLayout(output_container)
        output_label = QLabel("Output:")
        output_layout.addWidget(output_label)
        
        self.output_display = QTextEdit()
        self.output_display.setFont(QFont("Courier New", 10))
        self.output_display.setReadOnly(True)
        output_layout.addWidget(self.output_display)
        splitter.addWidget(output_container)
        
        layout.addWidget(splitter)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        self.run_button = QPushButton("Run")
        self.run_button.clicked.connect(self.run_code)
        button_layout.addWidget(self.run_button)
        
        self.clear_button = QPushButton("Clear Output")
        self.clear_button.clicked.connect(self.clear_output)
        button_layout.addWidget(self.clear_button)
        
        self.example_button = QPushButton("Load Example")
        self.example_button.clicked.connect(self.load_example)
        button_layout.addWidget(self.example_button)
        
        layout.addLayout(button_layout)
        
        # Load example code by default
        self.load_example()
    
    def output(self, text):
        """Callback for printing output"""
        self.output_display.append(text)
    
    def run_code(self):
        """Run the code in the editor"""
        code = self.code_editor.toPlainText()
        self.output_display.clear()
        
        try:
            # Parse the code
            interpreter = Interpreter()
            ast = interpreter.parse(code)
            
            # Execute the code
            executor = Executor(self.output)
            executor.execute(ast)
            
            self.output("\n--- Execution complete ---")
        except Exception as e:
            self.output(f"ERROR: {str(e)}")
    
    def clear_output(self):
        """Clear the output display"""
        self.output_display.clear()
    
    def load_example(self):
        """Load example code"""
        example = """# SimpleLang Example Program

# Variables
x = 10
y = 5
name = "World"

# Print statement
print "Hello"
print name
print x

# Arithmetic
result = x + y
print result

# If statement
if x > y:
    print "x is greater than y"

# While loop
counter = 0
while counter < 3:
    print counter
    counter = counter + 1

# For loop
print "For loop:"
for i in range(5):
    print i

# Nested loops
print "Nested loops:"
for i in range(3):
    for j in range(2):
        value = i * 10 + j
        print value
"""
        self.code_editor.setPlainText(example)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CodeEditor()
    window.show()
    sys.exit(app.exec())
