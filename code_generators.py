import tkinter as tk
from tkinter import scrolledtext


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
    
    def generate_code(self):
        """Generate code based on selected language."""
        if self.language.lower() == "python":
            return self._generate_python()
        elif self.language.lower() == "c":
            return self._generate_c()
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
        code.append("        \"\"\"Initialize the state machine with three state variables\"\"\"")
        
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
                
                # Convert comments to target language
                for key in sections:
                    sections[key] = self._convert_comments_to_language(sections[key])
                
                # Entry code - triggered when previous != current
                code.append(f"            # Entry: triggered when entering this state")
                code.append(f"            if self.previous_state != self.current_state:")
                if sections['entry'].strip():
                    for line in sections['entry'].split('\n'):
                        if line.strip():
                            code.append(f"                {line}")
                else:
                    code.append("                pass")
                code.append("")
                
                # During code
                code.append(f"            # During: executed every cycle")
                if sections['during'].strip():
                    for line in sections['during'].split('\n'):
                        if line.strip():
                            code.append(f"                {line}")
                else:
                    code.append("                pass")
                code.append("")
                
                # Transitions from this state
                code.append(f"            # Transitions from this state")
                transitions_list = []
                for (start_id, end_id), connections in self.logical_connections.items():
                    if start_id == node_id and end_id in state_ids:
                        for conn in connections:
                            condition = conn.get('condition', '')
                            if condition and not condition.startswith(('//','#')):
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
                if sections['exit'].strip():
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
        code.append(f"}} {struct_name};")
        code.append("")
        
        # Generate entry functions for each state
        code.append("// Entry functions - called when entering a state")
        for node_id, node_data in self.nodes.items():
            if node_data['type'] == 'state':
                state_name = state_ids_map.get(node_id)
                code.append(f"void entry_{state_name}({struct_name}* sm) {{")
                sections = self._parse_code_sections(node_data.get('code', ''), indent_level=1)
                if sections['entry'].strip():
                    code.append(sections['entry'])
                else:
                    code.append("    // Entry code here")
                code.append("}")
                code.append("")
        
        # Generate initialization function
        code.append(f"void {self.language.lower()}_state_machine_init({struct_name}* sm) {{")
        if self.default_state and self.default_state in self.nodes:
            initial_state = state_ids_map.get(self.default_state, f"STATE_{self.default_state}")
            code.append(f"    sm->current_state = {initial_state};")
            code.append(f"    sm->previous_state = {initial_state};")
        code.append("}")
        code.append("")
        
        # Generate state handlers
        for node_id, node_data in self.nodes.items():
            if node_data['type'] == 'state':
                state_name = state_ids_map.get(node_id)
                code.append(f"void handle_{state_name}({struct_name}* sm) {{")
                
                sections = self._parse_code_sections(node_data.get('code', ''), indent_level=1)
                
                # During code
                if sections['during'].strip():
                    code.append(sections['during'])
                else:
                    code.append("    // During code here")
                code.append("")
                
                # Transitions from this state
                for (start_id, end_id), connections in self.logical_connections.items():
                    if start_id == node_id and end_id in state_ids_map:
                        for conn in connections:
                            condition = conn.get('condition', '')
                            if condition and not condition.startswith(('//','/*')):
                                end_state_name = state_ids_map.get(end_id)
                                code.append(f"    // Transition condition: {condition}")
                                code.append(f"    if ({condition}) {{")
                                # Exit code needs extra indentation (level 2)
                                exit_sections = self._parse_code_sections(node_data.get('code', ''), indent_level=2)
                                if exit_sections['exit'].strip():
                                    code.append(exit_sections['exit'])
                                else:
                                    code.append("        // Exit code here")
                                code.append(f"        sm->current_state = {end_state_name};")
                                code.append("    }")
                code.append("}")
                code.append("")
        
        # Generate main update function
        code.append(f"void {self.language.lower()}_state_machine_update({struct_name}* sm) {{")
        code.append("    // Execute entry code if state changed")
        code.append("    if (sm->previous_state != sm->current_state) {")
        code.append("        switch(sm->current_state) {")
        
        for state_name in state_names:
            code.append(f"            case {state_name}:")
            code.append(f"                entry_{state_name}(sm);")
            code.append("                break;")
        
        code.append("        }")
        code.append("        sm->previous_state = sm->current_state;")
        code.append("    }")
        code.append("")
        code.append("    // Execute during code and check transitions")
        code.append("    switch(sm->current_state) {")
        
        for state_name in state_names:
            code.append(f"        case {state_name}:")
            code.append(f"            handle_{state_name}(sm);")
            code.append("            break;")
        
        code.append("    }")
        code.append("}")
        code.append("")
        
        # Generate main function
        code.append("int main() {")
        code.append(f"    {struct_name} sm;")
        code.append(f"    {self.language.lower()}_state_machine_init(&sm);")
        code.append("")
        code.append("    // Main loop")
        code.append("    while(1) {")
        code.append(f"        {self.language.lower()}_state_machine_update(&sm);")
        code.append("    }")
        code.append("")
        code.append("    return 0;")
        code.append("}")
        code.append("")
        
        return "\n".join(code)


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
        show_state_machine_tester(parent, nodes, edges, default_state, language, logical_connections, symbols)
    
    tk.Button(button_frame, text="Copy to Clipboard", command=copy_code).pack(side="left", padx=2)
    tk.Button(button_frame, text="Interactive Tester", command=open_tester).pack(side="left", padx=2)
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
    
    # Generate the state machine code
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
        
        # Display variables from namespace
        output_text.config(state="normal")
        output_text.delete("1.0", "end")
        
        # Add state variables
        output_text.insert("end", f"previous_state: {sm.previous_state.value if sm.previous_state else 'None'}\n")
        output_text.insert("end", f"current_state: {sm.current_state.value if sm.current_state else 'None'}\n")
        output_text.insert("end", f"next_state: {sm.next_state.value if sm.next_state else 'None'}\n")
        output_text.insert("end", "\nUser-defined variables:\n")
        
        # Display input/output symbols
        if symbols:
            output_symbols = {k: v for k, v in symbols.items() if v.get('type') in ('output', 'local')}
            if output_symbols:
                for sym_name in output_symbols:
                    val = namespace.get(sym_name, 'undefined')
                    output_text.insert("end", f"{sym_name}: {val}\n")
        
        output_text.config(state="disabled")
    
    def step():
        """Execute one state machine cycle"""
        # Update input variables in namespace
        for sym_name, entry in input_vars.items():
            try:
                val = entry.get()
                # Try to parse as boolean, int, or float
                if val.lower() in ('true', 'false'):
                    namespace[sym_name] = val.lower() == 'true'
                else:
                    try:
                        namespace[sym_name] = int(val)
                    except ValueError:
                        try:
                            namespace[sym_name] = float(val)
                        except ValueError:
                            namespace[sym_name] = val
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
