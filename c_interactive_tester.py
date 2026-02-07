"""
Interactive C Code Tester
Compiles and tests generated C state machine code with an interactive interface.
"""

import subprocess
import sys
import os
import re
import tempfile
import platform
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox


class CInteractiveTester:
    """Handles compilation and interactive testing of generated C code."""
    
    def __init__(self, c_code: str, symbols: Dict = None, nodes: Dict = None):
        """
        Initialize the C tester.
        
        Args:
            c_code: Generated C code as string
            symbols: Dictionary of symbols {name: {'type': 'input'/'output'/'local', 'description': str}}
            nodes: Dictionary of nodes for state names
        """
        self.c_code = c_code
        self.symbols = symbols or {}
        self.nodes = nodes or {}
        self.compiled = False
        self.executable_path = None
        self.temp_dir = None
        self.compiler = self._find_compiler()
        
    def _find_compiler(self) -> Optional[str]:
        """Find available C compiler on system."""
        compilers = ['gcc', 'clang', 'cc']
        if platform.system() == 'Windows':
            compilers = ['gcc', 'clang-cl', 'cl']
        
        for compiler in compilers:
            try:
                result = subprocess.run(
                    [compiler, '--version'],
                    capture_output=True,
                    timeout=2
                )
                if result.returncode == 0:
                    return compiler
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        
        return None
    
    def _generate_test_harness(self) -> str:
        """Generate a complete test harness with persistent state machine object."""
        # Extract the struct name and states from generated code
        struct_match = re.search(r'typedef\s+struct\s*\{[^}]*\}\s*(\w*StateMachine)\s*;', self.c_code, re.DOTALL)
        struct_name = struct_match.group(1) if struct_match else 'CStateMachine'
        
        # Extract state names from nodes (same logic as code_generators.py)
        state_names = []
        if self.nodes:
            for node_id, node_data in self.nodes.items():
                if node_data.get('type') == 'state':
                    # Get state name - handle different naming conventions
                    state_name = node_data.get('name', '').strip()
                    if not state_name:
                        state_name = f"STATE_{node_id}"
                    # Convert to C-style uppercase with underscores
                    state_name = state_name.upper().replace(' ', '_').replace('-', '_')
                    state_names.append(state_name)
        
        # If no states found, try to extract from enum in c_code
        if not state_names:
            enum_match = re.search(r'typedef\s+enum\s*\{([^}]+)\}\s*State', self.c_code, re.DOTALL)
            if enum_match:
                enum_content = enum_match.group(1)
                state_names = [name.strip().rstrip(',') for name in enum_content.split('\n') if name.strip() and not name.strip().startswith('//')]
        
        # Create test harness with persistent state machine
        test_harness = '''
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

''' + self.c_code + '''

// ============================================================================
// INTERACTIVE STATE MACHINE TESTER - Persistent State Machine Object
// ============================================================================

const char* state_to_string(State state) {
    switch (state) {
'''
        
        # Add state name mappings
        for i, state_name in enumerate(state_names):
            test_harness += f'        case {state_name}: return "{state_name}";\n'
        
        test_harness += '''        default: return "UNKNOWN";
    }
}

void print_state_machine(''' + struct_name + '''* sm) {
    printf("[STATE] current=%s previous=%s next=%s\\n", 
           state_to_string(sm->current_state), 
           state_to_string(sm->previous_state), 
           state_to_string(sm->next_state));
}

void print_symbols(''' + struct_name + '''* sm) {
    printf("[SYMBOLS]\\n");
'''
        
        # Add symbol printing
        for sym_name in self.symbols.keys():
            test_harness += f'    printf("{sym_name}: %d\\n", sm->{sym_name});\n'
        
        test_harness += '''    printf("[END_SYMBOLS]\\n");
}

int main() {
    ''' + struct_name + ''' *sm = (''' + struct_name + '''*)malloc(sizeof(''' + struct_name + '''));
    char buffer[512];
    char command[256];
    char var_name[256];
    int var_value;
    
    // Initialize persistent state machine object
    c_state_machine_init(sm);
    
    printf("[READY]\\n");
    print_state_machine(sm);
    print_symbols(sm);
    fflush(stdout);
    
    // Main input/output loop - persistent state machine
    while (fgets(buffer, sizeof(buffer), stdin) != NULL) {
        // Remove newline
        buffer[strcspn(buffer, "\\n")] = 0;
        
        if (strlen(buffer) == 0) {
            continue;
        }
        
        // Parse command
        int parsed = sscanf(buffer, "%255s %255s %d", command, var_name, &var_value);
        
        if (strcmp(command, "step") == 0) {
            // Execute one update cycle on persistent state machine
            c_state_machine_update(sm);
            printf("[STEP] executed\\n");
            print_state_machine(sm);
            
        } else if (strcmp(command, "set") == 0 && parsed >= 3) {
            // Set symbol on persistent state machine
            int found = 0;
'''
        
        # Add symbol setting code (only for input variables)
        for sym_name, sym_info in self.symbols.items():
            if sym_info.get('type') == 'input':
                test_harness += f'''            if (strcmp(var_name, "{sym_name}") == 0) {{
                sm->{sym_name} = var_value;
                printf("[SET] {sym_name}=%d\\n", var_value);
                found = 1;
            }}
'''
        
        test_harness += '''            if (!found) {
                printf("[ERROR] symbol not found: %s\\n", var_name);
            }
            
        } else if (strcmp(command, "state") == 0) {
            print_state_machine(sm);
            
        } else if (strcmp(command, "symbols") == 0) {
            print_symbols(sm);
            
        } else if (strcmp(command, "exit") == 0 || strcmp(command, "quit") == 0) {
            printf("[EXIT]\\n");
            break;
            
        } else {
            printf("[ERROR] unknown command: %s\\n", command);
        }
        
        fflush(stdout);
    }
    
    free(sm);
    return 0;
}
'''
        return test_harness
    
    def compile(self) -> Tuple[bool, str]:
        """
        Compile the C code.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        if not self.compiler:
            return False, "No C compiler found on system. Install gcc, clang, or use an online compiler."
        
        try:
            # Create temp directory
            self.temp_dir = tempfile.mkdtemp(prefix='c_tester_')
            
            # Write test harness to file
            test_code = self._generate_test_harness()
            c_file = os.path.join(self.temp_dir, 'state_machine_test.c')
            
            with open(c_file, 'w') as f:
                f.write(test_code)
            
            # Determine executable name
            if platform.system() == 'Windows':
                self.executable_path = os.path.join(self.temp_dir, 'state_machine_test.exe')
            else:
                self.executable_path = os.path.join(self.temp_dir, 'state_machine_test')
            
            # Compile
            compile_cmd = [self.compiler, c_file, '-o', self.executable_path, '-Wall', '-Wextra']
            result = subprocess.run(compile_cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                self.compiled = True
                return True, f"Successfully compiled using {self.compiler}"
            else:
                error_msg = result.stderr + result.stdout
                return False, f"Compilation failed:\\n{error_msg}"
                
        except subprocess.TimeoutExpired:
            return False, "Compilation timed out"
        except Exception as e:
            return False, f"Compilation error: {str(e)}"
    
    def run_interactive(self) -> Tuple[bool, str]:
        """Run the compiled executable interactively in a GUI."""
        if not self.compiled:
            return False, "Code not compiled. Compile first."
        
        if not os.path.exists(self.executable_path):
            return False, "Executable not found"
        
        # Launch GUI tester window
        self._launch_gui_tester()
        return True, "Interactive tester launched"
    
    def _launch_gui_tester(self):
        """Launch the interactive GUI tester with persistent state machine."""
        root = tk.Tk()
        root.title("C State Machine Interactive Tester")
        root.geometry("900x700")
        
        # Start persistent state machine process
        try:
            proc = subprocess.Popen(
                [self.executable_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1  # Line buffered
            )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start process: {str(e)}")
            return
        
        # Top: State and output display
        output_frame = ttk.LabelFrame(root, text="State Machine Output")
        output_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        output_text = scrolledtext.ScrolledText(output_frame, height=12, width=80)
        output_text.pack(fill="both", expand=True)
        
        # Control panel
        control_frame = ttk.LabelFrame(root, text="Controls")
        control_frame.pack(fill="x", padx=5, pady=5)
        
        # Input variable controls (spinboxes - only for input variables)
        symbols_frame = ttk.LabelFrame(control_frame, text="Set Input Variables")
        symbols_frame.pack(fill="x", padx=5, pady=5)
        
        symbol_controls = {}
        for sym_name, sym_info in sorted(self.symbols.items()):
            # Only show input variables in spinboxes
            if sym_info.get('type') == 'input':
                row_frame = ttk.Frame(symbols_frame)
                row_frame.pack(fill="x", padx=5, pady=2)
                
                label = ttk.Label(row_frame, text=f"{sym_name}:", width=15)
                label.pack(side="left", padx=5)
                
                spinbox = ttk.Spinbox(row_frame, from_=-1000, to=1000, width=10)
                spinbox.set(0)
                spinbox.pack(side="left", padx=5)
                
                symbol_controls[sym_name] = spinbox
        
        # Action buttons
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill="x", padx=5, pady=5)
        
        def parse_state_machine_output(output: str):
            """Parse output from persistent state machine process."""
            lines = output.split('\n')
            print(f"[DEBUG] Raw output received ({len(output)} chars):")
            print(f"[DEBUG] Output: {repr(output[:200])}")
            
            # Parse state from [STATE] line
            for line in lines:
                if '[STATE]' in line:
                    print(f"[DEBUG] Found [STATE] marker: {line}")
                    # Parse: [STATE] current=STATE_NAME previous=STATE_NAME next=STATE_NAME
                    state_match = re.search(r'\[STATE\]\s+current=(\S+)\s+previous=(\S+)\s+next=(\S+)', line)
                    if state_match:
                        print(f"[DEBUG] Parsed states: current={state_match.group(1)}, previous={state_match.group(2)}, next={state_match.group(3)}")
                    break
            
            # Parse symbols from [SYMBOLS]...[END_SYMBOLS] block
            in_symbols = False
            symbol_count = 0
            for line in lines:
                stripped = line.strip()
                if '[SYMBOLS]' in stripped:
                    in_symbols = True
                    print(f"[DEBUG] Found [SYMBOLS] marker")
                    continue
                if '[END_SYMBOLS]' in stripped:
                    in_symbols = False
                    print(f"[DEBUG] Found [END_SYMBOLS] marker, parsed {symbol_count} symbols")
                    continue
                if in_symbols and ':' in stripped and not stripped.startswith('['):
                    # Split on first colon only
                    parts = stripped.split(':', 1)
                    if len(parts) == 2:
                        var_name = parts[0].strip()
                        var_value = parts[1].strip()
                        symbol_count += 1
                        print(f"[DEBUG] Parsed {var_name} = {var_value}")
                    else:
                        print(f"[DEBUG] Failed to parse line: {repr(stripped)}")


        
        def execute_step():
            """Execute one step on the persistent state machine."""
            try:
                # Send set commands for ALL input variables
                for sym_name, spinbox in symbol_controls.items():
                    val = spinbox.get()
                    # Always send the value, even if it's 0
                    proc.stdin.write(f"set {sym_name} {val}\n")
                    print(f"[DEBUG] Sent: set {sym_name} {val}")
                    proc.stdin.flush()
                
                # Execute one step
                proc.stdin.write("step\n")
                print(f"[DEBUG] Sent: step")
                proc.stdin.write("symbols\n")
                print(f"[DEBUG] Sent: symbols")
                proc.stdin.flush()
                
                # Read output
                output_lines = []
                while True:
                    try:
                        line = proc.stdout.readline()
                        if not line:
                            print(f"[DEBUG] Got EOF from stdout")
                            break
                        line_clean = line.rstrip('\n')
                        output_lines.append(line_clean)
                        print(f"[DEBUG] Received: {repr(line_clean)}")
                        if '[END_SYMBOLS]' in line:
                            break
                    except Exception as read_error:
                        print(f"[DEBUG] Read error: {read_error}")
                        break
                
                # CLEAR output and display only latest step
                output = '\n'.join(output_lines)
                print(f"[DEBUG] Total output lines: {len(output_lines)}")
                print(f"[DEBUG] Combined output:\n{output}")
                output_text.delete('1.0', tk.END)  # Clear all previous output
                output_text.insert(tk.END, output + '\n')
                output_text.see(tk.END)  # Scroll to bottom
                
                # Parse and display variable values
                parse_state_machine_output(output)
                    
            except Exception as e:
                print(f"[DEBUG] Exception in execute_step: {e}")
                output_text.delete('1.0', tk.END)
                output_text.insert(tk.END, f"Error: {str(e)}\n")
        
        # Continuous mode tracking
        continuous_mode = [False]  # Use list to allow modification in nested function
        continuous_after_id = [None]  # Track scheduled callback
        
        def continuous_execute():
            """Automatically execute steps continuously."""
            if continuous_mode[0]:
                try:
                    execute_step()
                    # Schedule next step (500ms interval)
                    continuous_after_id[0] = root.after(500, continuous_execute)
                except Exception as e:
                    output_text.delete('1.0', tk.END)
                    output_text.insert(tk.END, f"Continuous mode error: {str(e)}\n")
                    continuous_mode[0] = False
                    start_continuous_btn.config(state="normal")
                    stop_continuous_btn.config(state="disabled")
        
        def start_continuous():
            """Start continuous execution mode."""
            continuous_mode[0] = True
            start_continuous_btn.config(state="disabled")
            stop_continuous_btn.config(state="normal")
            step_btn.config(state="disabled")
            output_text.delete('1.0', tk.END)
            output_text.insert(tk.END, "Continuous mode STARTED...\n")
            continuous_execute()
        
        def stop_continuous():
            """Stop continuous execution mode."""
            continuous_mode[0] = False
            if continuous_after_id[0]:
                root.after_cancel(continuous_after_id[0])
                continuous_after_id[0] = None
            start_continuous_btn.config(state="normal")
            stop_continuous_btn.config(state="disabled")
            step_btn.config(state="normal")
            output_text.insert(tk.END, "\nContinuous mode STOPPED.\n")
        
        def reset():
            """Reset state machine."""
            try:
                # Terminate existing process
                proc.terminate()
                try:
                    proc.wait(timeout=2)
                except:
                    proc.kill()
                
                # Start new process
                new_proc = subprocess.Popen(
                    [self.executable_path],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1
                )
                
                # Update the proc reference
                proc.__dict__.update(new_proc.__dict__)
                
                # Clear UI
                for spinbox in symbol_controls.values():
                    spinbox.set(0)
                output_text.delete('1.0', tk.END)
                output_text.insert(tk.END, "State machine reset.\n")
                
                # Initialize new state
                init_display()
            except Exception as e:
                output_text.insert(tk.END, f"Reset failed: {str(e)}\n")
        
        step_btn = ttk.Button(button_frame, text="Execute Step", command=execute_step)
        step_btn.pack(side="left", padx=5)
        
        start_continuous_btn = ttk.Button(button_frame, text="Start Continuous", command=start_continuous)
        start_continuous_btn.pack(side="left", padx=5)
        
        stop_continuous_btn = ttk.Button(button_frame, text="Stop Continuous", command=stop_continuous, state="disabled")
        stop_continuous_btn.pack(side="left", padx=5)
        
        reset_btn = ttk.Button(button_frame, text="Reset", command=reset)
        reset_btn.pack(side="left", padx=5)
        
        # Status
        status_var = tk.StringVar(value=f"Persistent state machine running (Compiler: {self.compiler})")
        status_label = ttk.Label(control_frame, textvariable=status_var)
        status_label.pack(fill="x", padx=5, pady=5)
        
        # Initialize display
        def init_display():
            try:
                # Clear output first
                output_text.delete('1.0', tk.END)
                
                proc.stdin.write("state\n")
                print(f"[DEBUG] Init sent: state")
                proc.stdin.write("symbols\n")
                print(f"[DEBUG] Init sent: symbols")
                proc.stdin.flush()
                
                output_lines = []
                while True:
                    try:
                        line = proc.stdout.readline()
                        if not line:
                            print(f"[DEBUG] Init got EOF from stdout")
                            break
                        line_clean = line.rstrip('\n')
                        output_lines.append(line_clean)
                        output_text.insert(tk.END, line)
                        print(f"[DEBUG] Init received: {repr(line_clean)}")
                        if '[END_SYMBOLS]' in line:
                            break
                    except Exception as read_error:
                        print(f"[DEBUG] Init read error: {read_error}")
                        break
                
                output = '\n'.join(output_lines)
                print(f"[DEBUG] Init total output lines: {len(output_lines)}")
                parse_state_machine_output(output)
            except Exception as init_error:
                print(f"[DEBUG] Init display exception: {init_error}")
        
        root.after(100, init_display)
        
        def on_closing():
            try:
                proc.stdin.write("exit\n")
                proc.stdin.flush()
                proc.terminate()
                try:
                    proc.wait(timeout=2)
                except:
                    proc.kill()
            except:
                pass
            root.destroy()
        
        root.protocol("WM_DELETE_WINDOW", on_closing)
        root.mainloop()


def test_c_code_interactive(c_code: str, symbols: Dict = None, nodes: Dict = None) -> bool:
    """
    Main entry point for interactive C testing.
    
    Args:
        c_code: Generated C code
        symbols: Symbol dictionary
        nodes: Nodes dictionary
        
    Returns:
        bool: Success status
    """
    tester = CInteractiveTester(c_code, symbols, nodes)
    
    # Check for compiler
    if not tester.compiler:
        print("\\nNo C compiler found. Options:")
        print("1. Install gcc/clang on your system")
        print("2. Use online compilers like:")
        print("   - OnlineGDB: https://www.onlinegdb.com/")
        print("   - Godbolt: https://godbolt.org/")
        print("   - Repl.it: https://repl.it/")
        return False
    
    print(f"Found compiler: {tester.compiler}")
    
    # Compile
    success, message = tester.compile()
    print(f"Compilation: {message}")
    
    if not success:
        return False
    
    # Run interactive tester
    success, message = tester.run_interactive()
    print(f"Tester: {message}")
    
    return success


if __name__ == "__main__":
    # Example usage
    example_c_code = '''
typedef enum {
    STATE1, STATE2
} State;

typedef struct {
    State current_state;
    State previous_state;
    State next_state;
    int counter;
    int trigger;
} CStateMachine;

void entry_STATE1(CStateMachine* sm) {
    sm->counter = 0;
}

void during_STATE1(CStateMachine* sm) {
    sm->counter++;
}

void check_transitions_STATE1(CStateMachine* sm) {
    if (sm->trigger) {
        sm->next_state = STATE2;
        return;
    }
    sm->next_state = sm->current_state;
}

void entry_STATE2(CStateMachine* sm) {
    sm->trigger = 0;
}

void during_STATE2(CStateMachine* sm) {
    // In STATE2
}

void check_transitions_STATE2(CStateMachine* sm) {
    if (sm->counter > 5) {
        sm->next_state = STATE1;
        return;
    }
    sm->next_state = sm->current_state;
}

void c_state_machine_init(CStateMachine* sm) {
    sm->current_state = STATE1;
    sm->previous_state = STATE1;
    sm->next_state = STATE1;
    sm->counter = 0;
    sm->trigger = 0;
}

void c_state_machine_update(CStateMachine* sm) {
    entry_STATE1(sm);
    during_STATE1(sm);
    check_transitions_STATE1(sm);
    
    if (sm->next_state != sm->current_state) {
        sm->previous_state = sm->current_state;
        sm->current_state = sm->next_state;
    }
}
'''
    
    symbols = {
        'counter': {'type': 'local', 'description': 'Internal counter'},
        'trigger': {'type': 'input', 'description': 'Transition trigger'}
    }
    
    test_c_code_interactive(example_c_code, symbols)
