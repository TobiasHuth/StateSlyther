import tkinter as tk
from tkinter import scrolledtext, messagebox
import sys
from pathlib import Path


class CodeGenerator:
    """Generates code from state diagram in different languages."""
    
    def __init__(self, nodes, edges, default_state, language="python", logical_connections=None, symbols=None):
        """
        Initialize code generator.
        
        Args:
            nodes: Dictionary of nodes with their properties
            edges: Dictionary of edges with their properties
            default_state: The default/initial state ID
            language: Programming language ('python' or 'C')
            logical_connections: Dictionary of logical connections between states
            symbols: Dictionary of symbols used in the state machine
        """
        self.nodes = nodes
        self.edges = edges
        self.default_state = default_state
        self.language = language
        self.logical_connections = logical_connections or {}
        self.symbols = symbols or {}
        
    def _parse_code_sections(self, code_text, indent_level=0):
        """Parse code text into entry, during, and exit sections."""
        sections = {'entry': '', 'during': '', 'exit': ''}
        
        if not code_text:
            return sections
        
        lines = code_text.split('\n')
        current_section = None
        section_lines = []
        indent = "    " * indent_level
        
        for line in lines:
            stripped = line.strip()
            if stripped == 'entry:':
                if current_section and section_lines:
                    sections[current_section] = '\n'.join(section_lines).strip()
                current_section = 'entry'
                section_lines = []
            elif stripped == 'during:':
                if current_section and section_lines:
                    sections[current_section] = '\n'.join(section_lines).strip()
                current_section = 'during'
                section_lines = []
            elif stripped == 'exit:':
                if current_section and section_lines:
                    sections[current_section] = '\n'.join(section_lines).strip()
                current_section = 'exit'
                section_lines = []
            elif current_section and not stripped.startswith(('entry:', 'during:', 'exit:')):
                # Skip comment lines for markers
                if not stripped.startswith(('// code executed', 'cyclic execution', 'code executed when')):
                    section_lines.append(line)
        
        # Save the last section
        if current_section and section_lines:
            sections[current_section] = '\n'.join(section_lines).strip()
        
        # Add proper indentation to all sections
        for key in sections:
            if sections[key]:
                indented_lines = [indent + l if l.strip() else l for l in sections[key].split('\n')]
                sections[key] = '\n'.join(indented_lines)
        
        return sections
    
    def _get_state_name(self, node_id):
        """Get standardized state name for a given node ID."""
        if node_id not in self.nodes:
            return f"STATE_{node_id}"
        return self.nodes[node_id]['name'].upper().replace(" ", "_") or f"STATE_{node_id}"
    
    def _prefix_variables_with_self(self, code_text):
        """Prefix symbol variables with 'self.' in generated code."""
        if not code_text or not self.symbols:
            return code_text
        
        # Get all symbol names
        symbol_names = list(self.symbols.keys())
        
        # Replace symbol names with self.symbol_name
        # Use word boundaries to avoid partial replacements
        import re
        for sym_name in symbol_names:
            # Match symbol name as a whole word (not part of another word)
            pattern = r'\b' + re.escape(sym_name) + r'\b'
            replacement = f'self.{sym_name}'
            code_text = re.sub(pattern, replacement, code_text)
        
        return code_text
    
    def _convert_comments_to_language(self, code_text):
        """
        Convert comments in code to the appropriate syntax for the target language.
        
        Handles:
        - Python: uses #
        - C/C++: uses //
        - Others: tries to convert appropriately
        """
        if not code_text:
            return code_text
        
        lines = code_text.split('\n')
        converted_lines = []
        
        for line in lines:
            # Determine comment type based on language
            if self.language.lower() == "python":
                # Convert // comments to # for Python
                if '//' in line:
                    # Find the position of //
                    idx = line.find('//')
                    # Preserve indentation and content before //
                    before = line[:idx]
                    after = line[idx+2:].lstrip()  # Remove the // and any spaces
                    line = before + '# ' + after if after else before.rstrip()
            elif self.language.lower() == "c":
                # Convert # comments to // for C (if needed)
                # Only convert # at the start of comment (not in strings)
                if '#' in line and not line.strip().startswith('//'):
                    # This is tricky, so we'll be conservative
                    if line.strip().startswith('#') and not any(x in line for x in ['#define', '#include', '#ifndef', '#ifdef']):
                        idx = line.find('#')
                        before = line[:idx]
                        after = line[idx+1:].lstrip()
                        line = before + '// ' + after if after else before.rstrip()
            
            converted_lines.append(line)
        
        return '\n'.join(converted_lines)
    
    def _convert_operators_to_language(self, code_text):
        """
        Convert logical operators between Python and C syntax.
        
        Python -> C:
        - 'and' -> '&&'
        - 'or' -> '||'
        - 'not ' -> '!'
        
        C -> Python:
        - '&&' -> 'and'
        - '||' -> 'or'
        - '!' -> 'not '
        """
        if not code_text:
            return code_text
        
        import re
        
        if self.language.lower() == "c":
            # Convert Python operators to C operators
            # Use word boundaries to avoid partial matches
            code_text = re.sub(r'\band\b', '&&', code_text)
            code_text = re.sub(r'\bor\b', '||', code_text)
            code_text = re.sub(r'\bnot\s+', '!', code_text)
        elif self.language.lower() == "python":
            # Convert C operators to Python operators
            code_text = code_text.replace('&&', 'and')
            code_text = code_text.replace('||', 'or')
            # Be careful with '!' conversion due to negation contexts
            code_text = re.sub(r'!\s*\(', 'not (', code_text)
            code_text = re.sub(r'!\s*([a-zA-Z_])', r'not \1', code_text)
        
        return code_text
    
    def _add_c_semicolons(self, code_text):
        """
        Add missing semicolons to C code lines that need them.
        This converts Python-style code (no semicolons) to C-style code with semicolons.
        """
        if not code_text or self.language.lower() != "c":
            return code_text
        
        lines = code_text.split('\n')
        fixed_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            # Skip empty lines, comment lines, and lines that don't need semicolons
            if not stripped or stripped.startswith('//') or stripped.startswith('#'):
                fixed_lines.append(line)
                continue
            
            # Skip control structures and braces
            if stripped in ('{', '}') or stripped.endswith('{') or stripped.startswith('case ') or stripped.startswith('default:'):
                fixed_lines.append(line)
                continue
            
            # Skip lines that already have semicolon or colon
            if stripped.endswith(';') or stripped.endswith(':'):
                fixed_lines.append(line)
                continue
            
            # Skip lines that end with opening brace or condition continuation
            if stripped.endswith('(') or stripped.endswith(','):
                fixed_lines.append(line)
                continue
            
            # Handle return statements (with or without values)
            if stripped.startswith('return'):
                if not stripped.endswith(';'):
                    line = line.rstrip() + ';'
                fixed_lines.append(line)
                continue
            
            # Handle break and continue statements
            if stripped in ('break', 'continue'):
                if not stripped.endswith(';'):
                    line = line.rstrip() + ';'
                fixed_lines.append(line)
                continue
            
            # Check if this is an assignment statement (has = but not ==, !=, <=, >=)
            # Assignment statements need semicolons even if they end with )
            is_assignment = ('=' in stripped and 
                           not any(op in stripped for op in ['==', '!=', '<=', '>=']) and
                           not any(kw in stripped for kw in ['if', 'else', 'for', 'while', 'switch']))
            
            if is_assignment:
                # This is definitely an assignment that needs a semicolon
                if not stripped.endswith(';'):
                    line = line.rstrip() + ';'
                fixed_lines.append(line)
                continue
            
            # Add semicolon to other statements that need them
            needs_semicolon = any(op in stripped for op in ['=', '++', '--', '(', '[', 'return', 'break', 'continue'])
            
            if needs_semicolon and not stripped.endswith(('{', '}', ':', '(')):
                # This looks like a statement that needs a semicolon (but may end with ))
                if not stripped.endswith(';'):
                    line = line.rstrip() + ';'
            elif not any(kw in stripped for kw in ['if', 'else', 'for', 'while', 'switch', 'do', 'case', 'default', 'break', 'continue']):
                # Other statements that likely need semicolons (variable accesses, function calls, etc.)
                if not stripped.startswith(('if', 'else', 'for', 'while', 'switch', '{', '}')) and not stripped.endswith(('{', '}')):
                    if not stripped.endswith(';') and stripped and (stripped[0].isalnum() or stripped[0] in ('_', 'sm', '*')):
                        # Likely needs a semicolon
                        line = line.rstrip() + ';'
            
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    def _has_executable_code(self, code_text):
        """Check if a code section contains actual executable code (not just comments)."""
        if not code_text or not code_text.strip():
            return False
        
        lines = code_text.split('\n')
        for line in lines:
            stripped = line.strip()
            # Skip empty lines and comment-only lines
            if not stripped or stripped.startswith('#') or stripped.startswith('//'):
                continue
            # Found non-comment, non-empty line
            return True
        
        return False
    
    def _is_intentionally_empty(self, code_text):
        """Check if code section is marked as intentionally empty (e.g., '// nix' or '# nix')."""
        if not code_text or not code_text.strip():
            return False
        
        lines = code_text.split('\n')
        for line in lines:
            stripped = line.strip()
            # Look for "nix" in comment lines
            if stripped.startswith('//') and 'nix' in stripped.lower():
                return True
            if stripped.startswith('#') and 'nix' in stripped.lower():
                return True
        
        return False
    
    def _get_python_type_hint(self, data_type):
        """Map data type to Python type hint."""
        if not data_type:
            return "Any"
        data_type = data_type.lower()
        if 'int' in data_type or 'uint' in data_type:
            return "int"
        elif 'float' in data_type:
            return "float"
        elif 'bool' in data_type:
            return "bool"
        elif 'string' in data_type or 'str' in data_type:
            return "str"
        else:
            return "Any"
    
    def _get_python_default_value(self, data_type):
        """Get appropriate default value for Python based on data type."""
        if not data_type:
            return "None"
        data_type = data_type.lower()
        if 'int' in data_type or 'uint' in data_type:
            return "0"
        elif 'float' in data_type:
            return "0.0"
        elif 'bool' in data_type:
            return "False"
        elif 'string' in data_type or 'str' in data_type:
            return '""'
        else:
            return "None"
    
    def _get_c_type(self, data_type):
        """Map data type to C type."""
        if not data_type:
            return "int"
        data_type = data_type.lower()
        if data_type == 'int8':
            return "int8_t"
        elif data_type == 'int16':
            return "int16_t"
        elif data_type == 'int32':
            return "int32_t"
        elif data_type == 'int64':
            return "int64_t"
        elif data_type == 'uint8':
            return "uint8_t"
        elif data_type == 'uint16':
            return "uint16_t"
        elif data_type == 'uint32':
            return "uint32_t"
        elif data_type == 'uint64':
            return "uint64_t"
        elif 'float32' in data_type:
            return "float"
        elif 'float64' in data_type or 'double' in data_type:
            return "double"
        elif 'bool' in data_type:
            return "bool"
        elif 'string' in data_type or 'str' in data_type:
            return "char*"
        else:
            return "int"
    
    def _get_c_default_value(self, data_type):
        """Get appropriate default value for C based on data type."""
        if not data_type:
            return "0"
        data_type = data_type.lower()
        if 'int' in data_type or 'uint' in data_type:
            return "0"
        elif 'float32' in data_type:
            return "0.0f"
        elif 'float64' in data_type or 'double' in data_type:
            return "0.0"
        elif 'bool' in data_type:
            return "false"
        elif 'string' in data_type or 'str' in data_type:
            return "NULL"
        else:
            return "0"
    
    def generate_code(self):
        """Generate code based on selected language."""
        if self.language.lower() == "python":
            return self._generate_python()
        elif self.language.lower() == "c":
            return self._generate_c()
        elif self.language.lower() == "st":
            return self._generate_st()
        else:
            return "# Unsupported language"
    
    def _generate_python(self):
        """Generate Python code from state diagram."""
        code = []
        code.append("# State Machine Generated Code")
        code.append("# Language: Python")
        code.append("")
        code.append("from enum import Enum")
        code.append("")
        
        # Generate State Enum
        code.append("class State(Enum):")
        state_ids = {}
        for node_id, node_data in self.nodes.items():
            if node_data['type'] == 'state':
                state_name = self._get_state_name(node_id)
                state_ids[node_id] = state_name
                code.append(f"    {state_name} = '{node_data['name']}'")
        code.append("")
        
        # Generate State Machine Class with language prefix
        class_name = f"{self.language.capitalize()}StateMachine"
        code.append(f"class {class_name}:")
        code.append("    def __init__(self):")
        code.append("        \"\"\"Initialize the state machine with state variables and symbols\"\"\"")
        
        # Set initial states
        if self.default_state and self.default_state in self.nodes:
            initial_state = state_ids.get(self.default_state, f"STATE_{self.default_state}")
            code.append(f"        self.previous_state = None")
            code.append(f"        self.current_state = State.{initial_state}")
            code.append(f"        self.next_state = State.{initial_state}")
        else:
            code.append("        self.previous_state = None")
            code.append("        self.current_state = None")
            code.append("        self.next_state = None")
        code.append("")
        
        # Initialize input, local, and output variables as class members
        if self.symbols:
            code.append("        # Initialize input variables")
            input_symbols = {k: v for k, v in self.symbols.items() if v.get('type') == 'input'}
            for sym_name, sym_data in input_symbols.items():
                data_type = sym_data.get('data_type', 'bool')
                default_value = self._get_python_default_value(data_type)
                code.append(f"        self.{sym_name} = {default_value}")
            
            code.append("")
            code.append("        # Initialize local variables")
            local_symbols = {k: v for k, v in self.symbols.items() if v.get('type') == 'local'}
            for sym_name, sym_data in local_symbols.items():
                data_type = sym_data.get('data_type', 'int32')
                default_value = self._get_python_default_value(data_type)
                code.append(f"        self.{sym_name} = {default_value}")
            
            code.append("")
            code.append("        # Initialize output variables")
            output_symbols = {k: v for k, v in self.symbols.items() if v.get('type') == 'output'}
            for sym_name, sym_data in output_symbols.items():
                data_type = sym_data.get('data_type', 'int32')
                default_value = self._get_python_default_value(data_type)
                code.append(f"        self.{sym_name} = {default_value}")
            
            code.append("")
        code.append("        # Symbol documentation")
        for sym_name, sym_data in self.symbols.items():
            sym_type = sym_data.get('type', 'local')
            data_type = sym_data.get('data_type', 'unknown')
            description = sym_data.get('description', '')
            code.append(f"        # {sym_name}: {sym_type} ({data_type})")
            if description:
                code.append(f"        #    Description: {description}")
        code.append("")
        
        # Generate update method
        code.append("    def update(self):")
        code.append("        \"\"\"Update state machine - call this in your main loop\"\"\"")
        code.append("        if self.current_state is None:")
        code.append("            return")
        code.append("")
        
        # For each state, generate the state logic
        for node_id, node_data in self.nodes.items():
            if node_data['type'] == 'state':
                state_name = state_ids.get(node_id)
                code.append(f"        # State: {node_data['name']}")
                code.append(f"        if self.current_state == State.{state_name}:")
                
                sections = self._parse_code_sections(node_data.get('code', ''), indent_level=0)
                
                # Prefix variables with self.
                for key in sections:
                    sections[key] = self._prefix_variables_with_self(sections[key])
                
                # Convert comments to target language
                for key in sections:
                    sections[key] = self._convert_comments_to_language(sections[key])
                
                # Entry code - triggered when previous != current
                code.append(f"            # Entry: triggered when entering this state")
                code.append(f"            if self.previous_state != self.current_state:")
                if self._has_executable_code(sections['entry']):
                    for line in sections['entry'].split('\n'):
                        if line.strip():
                            code.append(f"                {line}")
                else:
                    code.append("                pass")
                code.append("")
                
                # During code - executed unconditionally every cycle
                code.append(f"            # During: executed every cycle")
                if self._has_executable_code(sections['during']):
                    for line in sections['during'].split('\n'):
                        if line.strip():
                            code.append(f"            {line}")
                else:
                    code.append("            pass")
                code.append("")
                
                # Transitions from this state
                code.append(f"            # Transitions from this state")
                transitions_list = []
                for (start_id, end_id), connections in self.logical_connections.items():
                    if start_id == node_id and end_id in state_ids:
                        for conn in connections:
                            condition = conn.get('condition', '')
                            if condition and not condition.startswith(('//','#')):
                                # Prefix variables in condition
                                condition = self._prefix_variables_with_self(condition)
                                end_state_name = state_ids.get(end_id)
                                transitions_list.append((condition, end_state_name))
                
                if transitions_list:
                    # First transition uses 'if', rest use 'elif'
                    for idx, (condition, end_state_name) in enumerate(transitions_list):
                        if idx == 0:
                            code.append(f"            if {condition}:")
                        else:
                            code.append(f"            elif {condition}:")
                        code.append(f"                self.next_state = State.{end_state_name}")
                    # Add else to keep current state
                    code.append(f"            else:")
                    code.append(f"                self.next_state = self.current_state")
                else:
                    # No transitions defined
                    code.append(f"            self.next_state = self.current_state")
                code.append("")
                
                # Exit code - triggered when transitioning out (current != next)
                code.append(f"            # Exit: triggered when leaving this state")
                code.append(f"            if self.current_state != self.next_state:")
                if self._has_executable_code(sections['exit']):
                    for line in sections['exit'].split('\n'):
                        if line.strip():
                            code.append(f"                {line}")
                else:
                    code.append("                pass")
                code.append("")
        
        # Update state variables at the end of cycle
        code.append("        # Update state variables for next cycle")
        code.append("        self.previous_state = self.current_state")
        code.append("        self.current_state = self.next_state")
        code.append("")
        
        code.append("# Main execution")
        code.append(f"if __name__ == '__main__':")
        code.append(f"    sm = {class_name}()")
        code.append("    while True:")
        code.append("        sm.update()")
        code.append("")
        
        return "\n".join(code)
    
    def _generate_c(self):
        """Generate C code from state diagram."""
        code = []
        code.append("// State Machine Generated Code")
        code.append("// Language: C")
        code.append("")
        code.append("#include <stdio.h>")
        code.append("#include <stdbool.h>")
        code.append("#include <stdint.h>")
        code.append("")
        
        # Generate State Enum
        code.append("typedef enum {")
        state_names = []
        state_ids_map = {}
        for node_id, node_data in self.nodes.items():
            if node_data['type'] == 'state':
                state_name = self._get_state_name(node_id)
                state_names.append(state_name)
                state_ids_map[node_id] = state_name
                code.append(f"    {state_name},")
        code.append("} State;")
        code.append("")
        
        # Generate State Machine Struct with language prefix
        struct_name = f"{self.language.capitalize()}StateMachine"
        code.append(f"typedef struct {{")
        code.append("    State current_state;")
        code.append("    State previous_state;")
        code.append("    State next_state;")
        code.append("")
        
        # Add symbols to struct
        if self.symbols:
            code.append("    // Input variables")
            input_symbols = {k: v for k, v in self.symbols.items() if v.get('type') == 'input'}
            for sym_name, sym_data in input_symbols.items():
                c_type = self._get_c_type(sym_data.get('data_type', 'bool'))
                description = sym_data.get('description', '')
                code.append(f"    {c_type} {sym_name};  // {description}" if description else f"    {c_type} {sym_name};")
            
            code.append("    // Local variables")
            local_symbols = {k: v for k, v in self.symbols.items() if v.get('type') == 'local'}
            for sym_name, sym_data in local_symbols.items():
                c_type = self._get_c_type(sym_data.get('data_type', 'int32'))
                description = sym_data.get('description', '')
                code.append(f"    {c_type} {sym_name};  // {description}" if description else f"    {c_type} {sym_name};")
            
            code.append("    // Output variables")
            output_symbols = {k: v for k, v in self.symbols.items() if v.get('type') == 'output'}
            for sym_name, sym_data in output_symbols.items():
                c_type = self._get_c_type(sym_data.get('data_type', 'int32'))
                description = sym_data.get('description', '')
                code.append(f"    {c_type} {sym_name};  // {description}" if description else f"    {c_type} {sym_name};")
        
        code.append("} " + struct_name + ";")
        code.append("")
        
        # Forward declarations for state functions
        for state_name in state_names:
            code.append(f"void entry_{state_name}({struct_name}* sm);")
            code.append(f"void during_{state_name}({struct_name}* sm);")
            code.append(f"void check_transitions_{state_name}({struct_name}* sm);")
        code.append("")
        
        # Generate entry functions for each state
        code.append("// Entry functions - called when entering a state")
        for node_id, node_data in self.nodes.items():
            if node_data['type'] == 'state':
                state_name = state_ids_map.get(node_id)
                code.append(f"void entry_{state_name}({struct_name}* sm) {{")
                sections = self._parse_code_sections(node_data.get('code', ''), indent_level=1)
                # Prefix variables with sm->
                for key in sections:
                    sections[key] = self._prefix_variables_with_self(sections[key]).replace('self.', 'sm->')
                # Convert comments to language
                for key in sections:
                    sections[key] = self._convert_comments_to_language(sections[key])
                # Add C semicolons if needed
                for key in sections:
                    sections[key] = self._add_c_semicolons(sections[key])
                
                if self._has_executable_code(sections['entry']):
                    code.append(sections['entry'])
                elif self._is_intentionally_empty(sections['entry']):
                    # If marked as 'nix', preserve the intent with minimal comment
                    code.append("    // (no code)")
                else:
                    code.append("    // Entry code here")
                code.append("}")
                code.append("")
        
        # Generate during functions for each state
        code.append("// During functions - executed every cycle")
        for node_id, node_data in self.nodes.items():
            if node_data['type'] == 'state':
                state_name = state_ids_map.get(node_id)
                code.append(f"void during_{state_name}({struct_name}* sm) {{")
                sections = self._parse_code_sections(node_data.get('code', ''), indent_level=1)
                # Prefix variables with sm->
                for key in sections:
                    sections[key] = self._prefix_variables_with_self(sections[key]).replace('self.', 'sm->')
                # Convert comments to language
                for key in sections:
                    sections[key] = self._convert_comments_to_language(sections[key])
                # Add C semicolons if needed
                for key in sections:
                    sections[key] = self._add_c_semicolons(sections[key])
                
                if self._has_executable_code(sections['during']):
                    code.append(sections['during'])
                elif self._is_intentionally_empty(sections['during']):
                    # If marked as 'nix', preserve the intent with minimal comment
                    code.append("    // (no code)")
                else:
                    code.append("    // During code here")
                code.append("}")
                code.append("")
        
        # Generate transition check functions for each state
        code.append("// Transition check functions - evaluate conditions and perform exit code")
        for node_id, node_data in self.nodes.items():
            if node_data['type'] == 'state':
                state_name = state_ids_map.get(node_id)
                code.append(f"void check_transitions_{state_name}({struct_name}* sm) {{")
                
                sections = self._parse_code_sections(node_data.get('code', ''), indent_level=0)
                # Prefix variables with sm->
                for key in sections:
                    sections[key] = self._prefix_variables_with_self(sections[key]).replace('self.', 'sm->')
                
                # Check for transitions from this state
                has_transition = False
                for (start_id, end_id), connections in self.logical_connections.items():
                    if start_id == node_id and end_id in state_ids_map:
                        for conn in connections:
                            condition = conn.get('condition', '')
                            if condition and not condition.startswith(('//','/*')):
                                has_transition = True
                                end_state_name = state_ids_map.get(end_id)
                                # Prefix variables in condition and convert to C style
                                condition = self._prefix_variables_with_self(condition).replace('self.', 'sm->')
                                # Convert Python operators to C operators
                                condition = self._convert_operators_to_language(condition)
                                code.append(f"    if ({condition}) {{")
                                # Exit code
                                exit_sections = self._parse_code_sections(node_data.get('code', ''), indent_level=2)
                                # Prefix and convert exit code
                                exit_sections['exit'] = self._prefix_variables_with_self(exit_sections['exit']).replace('self.', 'sm->')
                                exit_sections['exit'] = self._convert_comments_to_language(exit_sections['exit'])
                                # Add C semicolons if needed (multiple passes to ensure all statements are fixed)
                                exit_sections['exit'] = self._add_c_semicolons(exit_sections['exit'])
                                exit_sections['exit'] = self._add_c_semicolons(exit_sections['exit'])  # Extra pass to catch any missed statements
                                
                                if self._has_executable_code(exit_sections['exit']):
                                    code.append(exit_sections['exit'])
                                elif self._is_intentionally_empty(exit_sections['exit']):
                                    # If marked as 'nix', preserve the intent with minimal comment
                                    code.append("        // (no code)")
                                else:
                                    code.append("        // Exit code here")
                                code.append(f"        sm->next_state = {end_state_name};")
                                code.append("        return;")
                                code.append("    }")
                
                if not has_transition:
                    code.append("    // No transitions defined")
                code.append("    sm->next_state = sm->current_state;")
                code.append("}")
                code.append("")
        
        # Generate initialization function
        code.append(f"void {self.language.lower()}_state_machine_init({struct_name}* sm) {{")
        if self.default_state and self.default_state in self.nodes:
            initial_state = state_ids_map.get(self.default_state, f"STATE_{self.default_state}")
            code.append(f"    sm->current_state = {initial_state};")
            code.append(f"    sm->previous_state = {initial_state};")
            code.append(f"    sm->next_state = {initial_state};")
        
        # Initialize symbols
        if self.symbols:
            code.append("    // Initialize input variables")
            input_symbols = {k: v for k, v in self.symbols.items() if v.get('type') == 'input'}
            for sym_name, sym_data in input_symbols.items():
                default_value = self._get_c_default_value(sym_data.get('data_type', 'bool'))
                code.append(f"    sm->{sym_name} = {default_value};")
            
            code.append("    // Initialize local variables")
            local_symbols = {k: v for k, v in self.symbols.items() if v.get('type') == 'local'}
            for sym_name, sym_data in local_symbols.items():
                default_value = self._get_c_default_value(sym_data.get('data_type', 'int32'))
                code.append(f"    sm->{sym_name} = {default_value};")
            
            code.append("    // Initialize output variables")
            output_symbols = {k: v for k, v in self.symbols.items() if v.get('type') == 'output'}
            for sym_name, sym_data in output_symbols.items():
                default_value = self._get_c_default_value(sym_data.get('data_type', 'int32'))
                code.append(f"    sm->{sym_name} = {default_value};")
        
        code.append("}")
        code.append("")
        
        # Generate main update function
        code.append(f"void {self.language.lower()}_state_machine_update({struct_name}* sm) {{")
        code.append("    // Entry: execute when state changes")
        code.append("    if (sm->previous_state != sm->current_state) {")
        code.append("        switch (sm->current_state) {")
        
        for state_name in state_names:
            code.append(f"            case {state_name}:")
            code.append(f"                entry_{state_name}(sm);")
            code.append("                break;")
        
        code.append("        }")
        code.append("    }")
        code.append("")
        code.append("    // During: execute unconditionally")
        code.append("    switch (sm->current_state) {")
        
        for state_name in state_names:
            code.append(f"        case {state_name}:")
            code.append(f"            during_{state_name}(sm);")
            code.append("            break;")
        
        code.append("    }")
        code.append("")
        code.append("    // Transitions: check conditions for state changes")
        code.append("    switch (sm->current_state) {")
        
        for state_name in state_names:
            code.append(f"        case {state_name}:")
            code.append(f"            check_transitions_{state_name}(sm);")
            code.append("            break;")
        
        code.append("    }")
        code.append("")
        code.append("    // Update state at end of cycle")
        code.append("    sm->previous_state = sm->current_state;")
        code.append("    sm->current_state = sm->next_state;")
        code.append("}")
        code.append("")
        
        # Generate main function with example usage
        code.append("// Example main function - uncomment to use")
        code.append("/*")
        code.append("int main() {")
        code.append(f"    {struct_name} sm;")
        code.append(f"    {self.language.lower()}_state_machine_init(&sm);")
        code.append("")
        code.append("    printf(\"State Machine initialized.\\\\n\");")
        code.append("")
        code.append("    // Main loop - update 10 times as example")
        code.append("    for (int i = 0; i < 10; i++) {")
        code.append(f"        {self.language.lower()}_state_machine_update(&sm);")
        code.append("        printf(\"Cycle %d: current_state = %d\\\\n\", i, sm.current_state);")
        code.append("    }")
        code.append("")
        code.append("    return 0;")
        code.append("}")
        code.append("*/")
        code.append("")
        
        return "\n".join(code)
    
    def _generate_st(self):
        """Generate Structured Text (IEC 61131-3) code from state diagram."""
        code = []
        code.append("(* State Machine Generated Code *)")
        code.append("(* Language: Structured Text (IEC 61131-3) *)")
        code.append("")
        code.append("PROGRAM StateMachine")
        code.append("    (* State enumeration *)")
        
        # Generate state constants
        state_counter = 0
        state_ids = {}
        for node_id, node_data in self.nodes.items():
            if node_data['type'] == 'state':
                state_name = self._get_state_name(node_id)
                state_ids[node_id] = state_name
                code.append(f"    {state_name} : DINT := {state_counter};")
                state_counter += 1
        code.append("")
        
        # Declare variables
        code.append("    (* State variables *)")
        code.append("    current_state : DINT;")
        code.append("    previous_state : DINT;")
        code.append("    next_state : DINT;")
        code.append("")
        
        # Declare input, local, and output symbols
        if self.symbols:
            code.append("    (* Input variables *)")
            input_symbols = {k: v for k, v in self.symbols.items() if v.get('type') == 'input'}
            for sym_name, sym_data in input_symbols.items():
                st_type = self._get_st_type(sym_data.get('data_type', 'BOOL'))
                description = sym_data.get('description', '')
                code.append(f"    {sym_name} : {st_type};  (* {description} *)" if description else f"    {sym_name} : {st_type};")
            
            code.append("")
            code.append("    (* Local variables *)")
            local_symbols = {k: v for k, v in self.symbols.items() if v.get('type') == 'local'}
            for sym_name, sym_data in local_symbols.items():
                st_type = self._get_st_type(sym_data.get('data_type', 'DINT'))
                description = sym_data.get('description', '')
                code.append(f"    {sym_name} : {st_type};  (* {description} *)" if description else f"    {sym_name} : {st_type};")
            
            code.append("")
            code.append("    (* Output variables *)")
            output_symbols = {k: v for k, v in self.symbols.items() if v.get('type') == 'output'}
            for sym_name, sym_data in output_symbols.items():
                st_type = self._get_st_type(sym_data.get('data_type', 'DINT'))
                description = sym_data.get('description', '')
                code.append(f"    {sym_name} : {st_type};  (* {description} *)" if description else f"    {sym_name} : {st_type};")
            code.append("")
        
        code.append("END_VAR")
        code.append("")
        code.append("    (* Initialize state machine *)")
        if self.default_state and self.default_state in self.nodes:
            initial_state = state_ids.get(self.default_state, f"STATE_{self.default_state}")
            code.append(f"    current_state := {initial_state};")
            code.append(f"    next_state := {initial_state};")
        code.append("")
        
        # Main state machine logic
        code.append("    (* State machine cycle *)")
        code.append("    CASE current_state OF")
        
        for node_id, node_data in self.nodes.items():
            if node_data['type'] == 'state':
                state_name = state_ids.get(node_id)
                code.append(f"    {state_name}:")
                
                sections = self._parse_code_sections(node_data.get('code', ''), indent_level=0)
                
                # Prefix variables with self references
                for key in sections:
                    sections[key] = self._prefix_variables_with_self(sections[key])
                
                # Convert comments to ST syntax
                for key in sections:
                    sections[key] = self._convert_comments_to_language(sections[key])
                
                code.append(f"        (* Entry code *)")
                code.append(f"        IF previous_state <> current_state THEN")
                if self._has_executable_code(sections['entry']):
                    for line in sections['entry'].split('\n'):
                        if line.strip():
                            code.append(f"            {line}")
                else:
                    code.append("            (* Entry code here *)")
                code.append(f"        END_IF;")
                code.append("")
                
                code.append(f"        (* During code *)")
                if self._has_executable_code(sections['during']):
                    for line in sections['during'].split('\n'):
                        if line.strip():
                            code.append(f"        {line}")
                else:
                    code.append("        (* During code here *)")
                code.append("")
                
                # Transitions
                code.append(f"        (* Transitions *)")
                transitions_list = []
                for (start_id, end_id), connections in self.logical_connections.items():
                    if start_id == node_id and end_id in state_ids:
                        for conn in connections:
                            condition = conn.get('condition', '')
                            if condition and not condition.startswith(('//','(*')):
                                condition = self._prefix_variables_with_self(condition)
                                end_state_name = state_ids.get(end_id)
                                transitions_list.append((condition, end_state_name))
                
                if transitions_list:
                    for idx, (condition, end_state_name) in enumerate(transitions_list):
                        if idx == 0:
                            code.append(f"        IF {condition} THEN")
                        else:
                            code.append(f"        ELSIF {condition} THEN")
                        code.append(f"            (* Exit code *)")
                        exit_sections = self._parse_code_sections(node_data.get('code', ''), indent_level=2)
                        exit_sections['exit'] = self._prefix_variables_with_self(exit_sections['exit'])
                        exit_sections['exit'] = self._convert_comments_to_language(exit_sections['exit'])
                        if self._has_executable_code(exit_sections['exit']):
                            for line in exit_sections['exit'].split('\n'):
                                if line.strip():
                                    code.append(f"            {line}")
                        else:
                            code.append("            (* Exit code here *)")
                        code.append(f"            next_state := {end_state_name};")
                    code.append(f"        ELSE")
                    code.append(f"            next_state := current_state;")
                    code.append(f"        END_IF;")
                else:
                    code.append(f"        next_state := current_state;")
                code.append("")
        
        code.append("    END_CASE;")
        code.append("")
        code.append("    (* Update state variables for next cycle *)")
        code.append("    previous_state := current_state;")
        code.append("    current_state := next_state;")
        code.append("")
        code.append("END_PROGRAM")
        
        return "\n".join(code)
    
    def _get_st_type(self, data_type):
        """Map data type to IEC 61131-3 Structured Text type."""
        if not data_type:
            return "DINT"
        data_type = data_type.lower()
        if data_type == 'int8':
            return "SINT"
        elif data_type == 'int16':
            return "INT"
        elif data_type == 'int32':
            return "DINT"
        elif data_type == 'int64':
            return "LINT"
        elif data_type == 'uint8':
            return "USINT"
        elif data_type == 'uint16':
            return "UINT"
        elif data_type == 'uint32':
            return "UDINT"
        elif data_type == 'uint64':
            return "ULINT"
        elif 'float32' in data_type:
            return "REAL"
        elif 'float64' in data_type or 'double' in data_type:
            return "LREAL"
        elif 'bool' in data_type:
            return "BOOL"
        elif 'string' in data_type or 'str' in data_type:
            return "STRING"
        else:
            return "DINT"


def show_code_editor(parent, nodes, edges, default_state, language, logical_connections=None, symbols=None, on_close_callback=None):
    """
    Open a code editor window showing generated code.
    
    Args:
        parent: Parent window
        nodes: Dictionary of nodes
        edges: Dictionary of edges
        default_state: Default state ID
        language: Programming language
        logical_connections: Dictionary of logical connections between states
        symbols: Dictionary of symbols
        on_close_callback: Optional callback when window closes
    """
    code_window = tk.Toplevel(parent)
    code_window.title("Generated Code")
    code_window.geometry("800x600")
    
    # Create toolbar
    toolbar = tk.Frame(code_window)
    toolbar.pack(side="top", fill="x", padx=5, pady=5)
    
    language_label = tk.Label(toolbar, text=f"Language: {language.capitalize()}", font=("Arial", 10, "bold"))
    language_label.pack(side="left", padx=5)
    
    # Create text widget with scrollbar
    text_widget = scrolledtext.ScrolledText(code_window, font=("Courier", 10), wrap="word")
    text_widget.pack(fill="both", expand=True, padx=5, pady=5)
    
    # Generate and display code
    generator = CodeGenerator(nodes, edges, default_state, language, logical_connections, symbols)
    generated_code = generator.generate_code()
    text_widget.insert("1.0", generated_code)
    text_widget.config(state="disabled")  # Make read-only
    
    # Create button frame
    button_frame = tk.Frame(code_window)
    button_frame.pack(side="bottom", fill="x", padx=5, pady=5)
    
    def copy_code():
        """Copy code to clipboard"""
        code_window.clipboard_clear()
        code_window.clipboard_append(generated_code)
        code_window.update()
    
    def open_tester():
        """Open interactive tester"""
        if language.lower() == "c":
            open_c_interactive_tester(parent, generated_code, symbols, nodes)
        else:
            show_state_machine_tester(parent, nodes, edges, default_state, language, logical_connections, symbols)
    
    def test_c_code():
        """Test C code with interactive tester"""
        open_c_interactive_tester(parent, generated_code, symbols, nodes)
    
    tk.Button(button_frame, text="Copy to Clipboard", command=copy_code).pack(side="left", padx=2)
    
    # Only show interactive tester button for Python
    if language.lower() == "python":
        tk.Button(button_frame, text="Interactive Tester", command=open_tester).pack(side="left", padx=2)
    else:
        # For C code, show test button
        tk.Button(button_frame, text="Test C Code (Compile)", command=test_c_code).pack(side="left", padx=2)
    
    tk.Button(button_frame, text="Close", command=code_window.destroy).pack(side="left", padx=2)
    
    if on_close_callback:
        code_window.protocol("WM_DELETE_WINDOW", lambda: (on_close_callback(), code_window.destroy()))


def show_state_machine_tester(parent, nodes, edges, default_state, language, logical_connections=None, symbols=None):
    """
    Open an interactive state machine tester window.
    
    Args:
        parent: Parent window
        nodes: Dictionary of nodes
        edges: Dictionary of edges
        default_state: Default state ID
        language: Programming language
        logical_connections: Dictionary of logical connections
        symbols: Dictionary of symbols
    """
    tester_window = tk.Toplevel(parent)
    tester_window.title("State Machine Tester")
    tester_window.geometry("600x700")
    
    # Check if language is C - cannot test C code interactively without compiler
    if language.lower() == "c":
        # Create info message
        info_frame = tk.Frame(tester_window)
        info_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        title_label = tk.Label(info_frame, text="C Code Testing", font=("Arial", 14, "bold"), fg="blue")
        title_label.pack(pady=10)
        
        message = """C code cannot be tested interactively in this application.

To test your generated C code, you have several options:

1. COMPILE LOCALLY (Windows/Linux/Mac):
   • Install a C compiler (gcc, clang, or MSVC)
   • Copy the generated .c file to your project
   • Compile: gcc generated_file.c -o state_machine
   • Run the compiled executable

2. ONLINE COMPILER (No installation needed):
   • Visit: https://www.onlinegdb.com/
   • Copy the generated C code here
   • Click "Compile" and "Run"

3. OTHER ONLINE TOOLS:
   • Repl.it - https://repl.it
   • Godbolt - https://godbolt.org
   • Compiler Explorer

The generated C code includes:
   ✓ Proper struct definition
   ✓ State machine functions
   ✓ Example main() function (commented out)
   ✓ All symbol handling
   ✓ Standard C libraries included"""
        
        message_label = tk.Label(info_frame, text=message, justify="left", font=("Courier", 10), wraplength=500)
        message_label.pack(pady=10)
        
        # Button to close
        close_btn = tk.Button(info_frame, text="Close", command=tester_window.destroy)
        close_btn.pack(padx=5, pady=10)
        
        return
    
    # Generate the state machine code (Python only at this point)
    generator = CodeGenerator(nodes, edges, default_state, language, logical_connections, symbols)
    generated_code = generator.generate_code()
    
    # Execute the code in a namespace
    namespace = {}
    try:
        exec(generated_code, namespace)
    except Exception as e:
        error_label = tk.Label(tester_window, text=f"Error generating code: {str(e)}", fg="red")
        error_label.pack(padx=10, pady=10)
        return
    
    # Get the state machine class and enum
    class_name = f"{language.capitalize()}StateMachine"
    if class_name not in namespace:
        error_label = tk.Label(tester_window, text=f"Could not find {class_name} in generated code", fg="red")
        error_label.pack(padx=10, pady=10)
        return
    
    StateMachine = namespace[class_name]
    State = namespace.get('State')
    
    # Create state machine instance
    sm = StateMachine()
    
    # Create UI sections
    # Current State Display
    state_frame = tk.LabelFrame(tester_window, text="Current State", padx=10, pady=10)
    state_frame.pack(fill="x", padx=10, pady=5)
    
    state_label = tk.Label(state_frame, text="Initializing...", font=("Arial", 14, "bold"), fg="blue")
    state_label.pack()
    
    # Input Controls
    input_frame = tk.LabelFrame(tester_window, text="Input Symbols", padx=10, pady=10)
    input_frame.pack(fill="both", expand=False, padx=10, pady=5)
    
    input_vars = {}
    input_widgets = {}
    
    # Get input symbols from symbols dict
    if symbols:
        input_symbols = {k: v for k, v in symbols.items() if v.get('type') == 'input'}
        
        if input_symbols:
            for sym_name, sym_data in input_symbols.items():
                sym_frame = tk.Frame(input_frame)
                sym_frame.pack(fill="x", pady=5)
                
                label = tk.Label(sym_frame, text=f"{sym_name}:", width=15, anchor="w")
                label.pack(side="left", padx=5)
                
                # Try to determine if it's boolean or numeric
                entry = tk.Entry(sym_frame, width=20)
                entry.insert(0, "False")
                entry.pack(side="left", padx=5, fill="x", expand=True)
                
                input_vars[sym_name] = entry
                input_widgets[sym_name] = entry
        else:
            no_inputs_label = tk.Label(input_frame, text="No input symbols defined", fg="gray")
            no_inputs_label.pack()
    else:
        no_inputs_label = tk.Label(input_frame, text="No input symbols defined", fg="gray")
        no_inputs_label.pack()
    
    # Output/Local Variables Display
    output_frame = tk.LabelFrame(tester_window, text="Output & Local Variables", padx=10, pady=10)
    output_frame.pack(fill="both", expand=True, padx=10, pady=5)
    
    output_text = scrolledtext.ScrolledText(output_frame, font=("Courier", 9), height=10)
    output_text.pack(fill="both", expand=True)
    output_text.config(state="disabled")
    
    def update_display():
        """Update the state machine display"""
        state_label.config(text=f"Current State: {sm.current_state.value if sm.current_state else 'None'}")
        
        # Display variables from the state machine object
        output_text.config(state="normal")
        output_text.delete("1.0", "end")
        
        # Add state variables
        output_text.insert("end", f"previous_state: {sm.previous_state.value if sm.previous_state else 'None'}\n")
        output_text.insert("end", f"current_state: {sm.current_state.value if sm.current_state else 'None'}\n")
        output_text.insert("end", f"next_state: {sm.next_state.value if sm.next_state else 'None'}\n")
        output_text.insert("end", "\nUser-defined variables:\n")
        
        # Display input/output symbols from the state machine object
        if symbols:
            output_symbols = {k: v for k, v in symbols.items() if v.get('type') in ('output', 'local')}
            if output_symbols:
                for sym_name in output_symbols:
                    val = getattr(sm, sym_name, 'undefined')
                    output_text.insert("end", f"{sym_name}: {val}\n")
        
        output_text.config(state="disabled")
    
    def step():
        """Execute one state machine cycle"""
        # Update input variables on the state machine object
        for sym_name, entry in input_vars.items():
            try:
                val = entry.get()
                # Try to parse as boolean, int, or float
                if val.lower() in ('true', 'false'):
                    setattr(sm, sym_name, val.lower() == 'true')
                else:
                    try:
                        setattr(sm, sym_name, int(val))
                    except ValueError:
                        try:
                            setattr(sm, sym_name, float(val))
                        except ValueError:
                            setattr(sm, sym_name, val)
            except Exception as e:
                pass
        
        # Execute one update cycle
        try:
            sm.update()
            update_display()
        except Exception as e:
            output_text.config(state="normal")
            output_text.delete("1.0", "end")
            output_text.insert("end", f"Error during update: {str(e)}")
            output_text.config(state="disabled")
    
    running = [False]  # Use list to allow modification in nested function
    
    def toggle_run():
        """Toggle continuous run"""
        running[0] = not running[0]
        run_button.config(text="Stop" if running[0] else "Start Continuous")
        if running[0]:
            continuous_cycle()
    
    def continuous_cycle():
        """Run continuous cycles"""
        if running[0]:
            step()
            tester_window.after(500, continuous_cycle)  # 500ms between cycles
    
    # Control Buttons
    button_frame = tk.Frame(tester_window)
    button_frame.pack(fill="x", padx=10, pady=10)
    
    step_button = tk.Button(button_frame, text="Step Once", command=step, width=15)
    step_button.pack(side="left", padx=5)
    
    run_button = tk.Button(button_frame, text="Start Continuous", command=toggle_run, width=15)
    run_button.pack(side="left", padx=5)
    
    reset_button = tk.Button(button_frame, text="Reset", command=lambda: (sm.__init__(), update_display()), width=15)
    reset_button.pack(side="left", padx=5)
    
    # Initial display
    update_display()


def open_c_interactive_tester(parent, c_code, symbols=None, nodes=None):
    """
    Open an interactive C code tester with compilation support.
    
    Args:
        parent: Parent window
        c_code: Generated C code string
        symbols: Dictionary of symbols
        nodes: Dictionary of nodes
    """
    try:
        from c_interactive_tester import CInteractiveTester
    except ImportError:
        messagebox.showerror(
            "Import Error",
            "Could not import C interactive tester.\n"
            "Make sure c_interactive_tester.py is in the same directory."
        )
        return
    
    # Create tester instance
    tester = CInteractiveTester(c_code, symbols, nodes)
    
    # Check for compiler
    if not tester.compiler:
        messagebox.showwarning(
            "No C Compiler Found",
            "No C compiler detected on your system.\n\n"
            "To test C code, install one of:\n"
            "• gcc (MinGW on Windows, apt on Linux, brew on Mac)\n"
            "• clang\n"
            "• MSVC (Visual Studio)\n\n"
            "Or use an online compiler:\n"
            "• OnlineGDB: https://www.onlinegdb.com/\n"
            "• Godbolt: https://godbolt.org/\n"
            "• Repl.it: https://repl.it/"
        )
        return
    
    # Show status window
    status_window = tk.Toplevel(parent)
    status_window.title("C Code Compiler & Tester")
    status_window.geometry("600x400")
    
    status_text = scrolledtext.ScrolledText(status_window, font=("Courier", 10))
    status_text.pack(fill="both", expand=True, padx=5, pady=5)
    
    def log_message(msg):
        """Log message to status window"""
        status_text.config(state="normal")
        status_text.insert("end", msg + "\n")
        status_text.see("end")
        status_text.config(state="disabled")
        status_window.update()
    
    def compile_and_test():
        """Compile and run the C code"""
        log_message("=" * 60)
        log_message("C Code Compilation & Testing")
        log_message("=" * 60)
        log_message(f"Compiler detected: {tester.compiler}\n")
        
        log_message("Step 1: Generating test harness...")
        try:
            harness = tester._generate_test_harness()
            log_message(f"✓ Test harness generated ({len(harness)} bytes)\n")
        except Exception as e:
            log_message(f"✗ Error generating harness: {str(e)}\n")
            return
        
        log_message("Step 2: Compiling C code...")
        success, message = tester.compile()
        log_message(f"{'✓' if success else '✗'} {message}\n")
        
        if not success:
            log_message("\nCompilation failed. Check the code for:")
            log_message("• Python syntax in code blocks (convert to C)")
            log_message("• Invalid variable references")
            log_message("• Missing semicolons")
            return
        
        log_message("Step 3: Launching interactive tester...\n")
        log_message("=" * 60)
        log_message("INTERACTIVE TESTER READY")
        log_message("=" * 60)
        log_message("A new window will open for interactive testing.")
        log_message("Use the controls to:")
        log_message("  • Set input variable values")
        log_message("  • Execute state machine steps")
        log_message("  • Monitor state and variable changes\n")
        
        # Launch GUI tester
        status_window.after(1000, lambda: tester._launch_gui_tester())
    
    # Compile and test button
    ctrl_frame = tk.Frame(status_window)
    ctrl_frame.pack(fill="x", padx=5, pady=5)
    
    tk.Button(ctrl_frame, text="Compile & Test", command=compile_and_test, bg="green", fg="white", width=20).pack(side="left", padx=5)
    tk.Button(ctrl_frame, text="Close", command=status_window.destroy, width=20).pack(side="left", padx=5)
    
    # Start compilation automatically
    status_window.after(500, compile_and_test)

