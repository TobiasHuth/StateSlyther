import tkinter as tk
from tkinter import scrolledtext


class CodeGenerator:
    """Generates code from state diagram in different languages."""
    
    def __init__(self, nodes, edges, default_state, language="python"):
        """
        Initialize code generator.
        
        Args:
            nodes: Dictionary of nodes with their properties
            edges: Dictionary of edges with their properties
            default_state: The default/initial state ID
            language: Programming language ('python' or 'C')
        """
        self.nodes = nodes
        self.edges = edges
        self.default_state = default_state
        self.language = language
    
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
        for node_id, node_data in self.nodes.items():
            if node_data['type'] == 'state':
                state_name = node_data['name'].upper().replace(" ", "_") or f"STATE_{node_id}"
                code.append(f"    {state_name} = '{node_data['name']}'")
        code.append("")
        
        # Generate State Machine Class
        code.append("class StateMachine:")
        code.append("    def __init__(self):")
        
        # Set initial state
        if self.default_state and self.default_state in self.nodes:
            initial_state = self.nodes[self.default_state]['name'].upper().replace(" ", "_") or f"STATE_{self.default_state}"
            code.append(f"        self.current_state = State.{initial_state}")
        else:
            code.append("        self.current_state = None")
        code.append("")
        
        # Generate state handlers
        code.append("    def update(self):")
        code.append("        \"\"\"Update state machine - call this in your main loop\"\"\"")
        code.append("        if self.current_state is None:")
        code.append("            return")
        code.append("")
        
        for node_id, node_data in self.nodes.items():
            if node_data['type'] == 'state':
                state_name = node_data['name'].upper().replace(" ", "_") or f"STATE_{node_id}"
                code.append(f"        if self.current_state == State.{state_name}:")
                code.append(f"            self._handle_{state_name}()")
        code.append("")
        
        # Generate individual state handlers
        for node_id, node_data in self.nodes.items():
            if node_data['type'] == 'state':
                state_name = node_data['name'].upper().replace(" ", "_") or f"STATE_{node_id}"
                code.append(f"    def _handle_{state_name}(self):")
                
                # Parse code sections
                state_code = node_data.get('code', '')
                code.append("        # State execution code")
                code.append("        pass  # Add your state logic here")
                code.append("")
        
        # Generate transitions
        code.append("    def transition(self, new_state):")
        code.append("        \"\"\"Change to a new state\"\"\"")
        code.append("        self.current_state = new_state")
        code.append("")
        
        code.append("# Main execution")
        code.append("if __name__ == '__main__':")
        code.append("    sm = StateMachine()")
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
        for node_id, node_data in self.nodes.items():
            if node_data['type'] == 'state':
                state_name = node_data['name'].upper().replace(" ", "_") or f"STATE_{node_id}"
                state_names.append(state_name)
                code.append(f"    {state_name},")
        code.append("} State;")
        code.append("")
        
        # Generate State Machine Struct
        code.append("typedef struct {")
        code.append("    State current_state;")
        code.append("} StateMachine;")
        code.append("")
        
        # Generate initialization function
        code.append("void state_machine_init(StateMachine* sm) {")
        if self.default_state and self.default_state in self.nodes:
            initial_state = self.nodes[self.default_state]['name'].upper().replace(" ", "_") or f"STATE_{self.default_state}"
            code.append(f"    sm->current_state = {initial_state};")
        code.append("}")
        code.append("")
        
        # Generate state handlers
        for node_id, node_data in self.nodes.items():
            if node_data['type'] == 'state':
                state_name = node_data['name'].upper().replace(" ", "_") or f"STATE_{node_id}"
                code.append(f"void handle_{state_name}(StateMachine* sm) {{")
                code.append("    // State execution code")
                code.append("    // Add your state logic here")
                code.append("}")
                code.append("")
        
        # Generate main update function
        code.append("void state_machine_update(StateMachine* sm) {")
        code.append("    switch(sm->current_state) {")
        
        for state_name in state_names:
            code.append(f"        case {state_name}:")
            code.append(f"            handle_{state_name}(sm);")
            code.append("            break;")
        
        code.append("    }")
        code.append("}")
        code.append("")
        
        # Generate transition function
        code.append("void state_machine_transition(StateMachine* sm, State new_state) {")
        code.append("    sm->current_state = new_state;")
        code.append("}")
        code.append("")
        
        # Generate main function
        code.append("int main() {")
        code.append("    StateMachine sm;")
        code.append("    state_machine_init(&sm);")
        code.append("")
        code.append("    // Main loop")
        code.append("    while(1) {")
        code.append("        state_machine_update(&sm);")
        code.append("    }")
        code.append("")
        code.append("    return 0;")
        code.append("}")
        code.append("")
        
        return "\n".join(code)


def show_code_editor(parent, nodes, edges, default_state, language, on_close_callback=None):
    """
    Open a code editor window showing generated code.
    
    Args:
        parent: Parent window
        nodes: Dictionary of nodes
        edges: Dictionary of edges
        default_state: Default state ID
        language: Programming language
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
    generator = CodeGenerator(nodes, edges, default_state, language)
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
    
    tk.Button(button_frame, text="Copy to Clipboard", command=copy_code).pack(side="left", padx=2)
    tk.Button(button_frame, text="Close", command=code_window.destroy).pack(side="left", padx=2)
    
    if on_close_callback:
        code_window.protocol("WM_DELETE_WINDOW", lambda: (on_close_callback(), code_window.destroy()))
