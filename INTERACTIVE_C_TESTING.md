# Enhanced C Code Testing Guide - Interactive Compiled Testing

## Overview

This guide covers the **new interactive compiled C testing system** that allows you to test your generated state machine code with actual C compilation and execution.

---

## Quick Start: Interactive Testing

### Step 1: Generate C Code
1. Open your state diagram in StateSlyther
2. Go to **Code → Set Language → C**
3. Go to **Code → Update/Show Code**
4. Click **Test C Code (Interactive)** button

### Step 2: Automatic Compilation
- The system automatically detects your C compiler (gcc, clang, etc.)
- Code is compiled with optimizations and safety checks
- Any compilation errors are shown with details

### Step 3: Interactive Testing Window
The testing interface provides:
- **Real-time state display** - See current/previous/next states
- **Symbol manipulation** - Set input variables with spinboxes
- **Step execution** - Execute one state machine cycle at a time
- **Output monitoring** - Watch all symbol values change

---

## Features

### ✅ Compiler Detection
Automatically detects:
- **Windows**: gcc, clang-cl, Visual Studio cl
- **Linux/Mac**: gcc, clang, cc

If no compiler found, suggests online alternatives.

### ✅ Test Harness Generation
Automatically generates a complete C program with:
- Main function with interactive menu
- Symbol value display and manipulation
- State machine state tracking
- Command-based interaction: `step`, `set`, `state`, `symbols`, `exit`

### ✅ Interactive GUI Tester
Shows:
1. **State Machine Output**
   - Current State
   - Previous State
   - Next State

2. **Symbol Controls**
   - Spinbox for each input/local variable
   - Set values before stepping
   - View changes in output

3. **Action Buttons**
   - **Execute Step** - Run one cycle with current symbol values
   - **Reset** - Clear all values and output

### ✅ Real Compilation & Execution
- Actual C compilation (not just syntax checking)
- Tests the compiled binary with real behavior
- Catch runtime errors and undefined behavior

---

## Usage Examples

### Example 1: Simple Counter State Machine

**State Diagram:**
- STATE1 (Initial): Increment counter
- STATE2: Wait for reset
- Transition: counter > 5 → STATE2
- Transition: reset_flag == 1 → STATE1

**Testing Process:**
1. Click **Execute Step** → counter increments
2. Click **Execute Step** → counter increments again
3. Set `reset_flag` spinbox to `1`
4. Click **Execute Step** → transitions to STATE2
5. Watch the output display state changes

### Example 2: Traffic Light with Input

**Symbols:**
- `sensor`: input (1 = car detected)
- `timer`: local counter
- `light_state`: output (0=red, 1=yellow, 2=green)

**Testing:**
1. Set `sensor` = 0, execute multiple steps
2. Set `sensor` = 1, execute to trigger changes
3. Observe `light_state` output changes

---

## Troubleshooting

### Issue: "No C compiler found"

**Solutions:**
1. **Windows:**
   ```bash
   # Install MinGW or use Windows Subsystem for Linux
   choco install mingw  # via Chocolatey
   # or use MSVC from Visual Studio
   ```

2. **Linux/Mac:**
   ```bash
   sudo apt-get install gcc          # Ubuntu/Debian
   brew install gcc                  # macOS
   ```

3. **Alternative - Online Compilers:**
   - Copy the generated C code
   - Paste into [OnlineGDB](https://www.onlinegdb.com/)
   - Modify test input as needed

### Issue: Compilation Errors

Common causes:
- **Symbol type mismatch**: Ensure symbols are declared correctly in diagram
- **Syntax in code blocks**: Check Python syntax is valid (generator converts to C)
- **Missing header files**: System-specific headers may need adjustment

**Solution:**
1. Check error message carefully
2. Modify state diagram code blocks
3. Look for Python-style syntax (e.g., `print()` instead of `printf()`)

### Issue: Tester window won't respond

**Solutions:**
- Check system has TkInter installed (usually included with Python)
- Ensure compiled binary can execute (permissions, dependencies)
- Try simpler state machine first

---

## Advanced Testing Scenarios

### Scenario 1: Conditional State Transitions

```
Initial: STATE1, counter = 0
Set: trigger = 0
Step 5x: counter increments
Set: trigger = 1  
Step: Transitions to STATE2
```

### Scenario 2: Multiple Inputs

```
State machine with inputs: a, b, c
Test all combinations:
- a=1, b=0, c=0 → observe transitions
- a=0, b=1, c=0 → observe transitions
- a=1, b=1, c=1 → observe transitions
```

### Scenario 3: State Entry/Exit Code

```
STATE1 entry: counter = 0
STATE1 during: counter++
STATE2 entry: message = "In state 2"
STATE2 during: counter--
STATE2 exit: trigger_flag = 0

Test flow:
Entry → counter = 0
During → counter increments
Transition → Exit code executes
```

---

## Tester Output Interpretation

### State Machine Display
```
=== Current State Machine ===
Current State: 1        (current enum value)
Previous State: 0       (previous state enum)
Next State: 1           (queued next state)
```

### Symbol Values
```
=== Symbol Values ===
counter: 5
trigger: 0
sensor: 1
```

---

## Integration with Code Generation

The testing system integrates with the code generator through:
1. **C code extraction** - Automatically parses generated code
2. **Symbol detection** - Identifies input/output/local variables
3. **Struct parsing** - Determines state machine structure
4. **Test harness generation** - Creates complete main() function

---

## Command Reference (Interactive Console Mode)

If running in console (not GUI):

```
> step              # Execute one state machine cycle
> set <var> <val>   # Set symbol variable value
> state             # Print current state
> symbols           # Print all symbol values
> help              # Show command menu
> quit              # Exit tester
```

---

## Best Practices

1. **Test incrementally**
   - Don't set too many variables at once
   - Step through state changes one at a time

2. **Verify initial state**
   - Always check init state is correct
   - View initial symbol values

3. **Test edge cases**
   - Set variables to min/max values
   - Test transition boundaries

4. **Monitor output**
   - Watch for unexpected state transitions
   - Verify entry/during/exit code executes

5. **Compare with Python**
   - Generate both Python and C versions
   - Compare behavior for consistency

---

## Technical Details

### Generated Test Harness Structure
```c
#include <stdio.h>      // I/O
#include <string.h>     // String ops
#include <stdlib.h>     // Utilities

[Generated C Code Here]

// Interactive functions
void print_state_machine(...)
void print_symbols(...)
void print_menu()

int main() {
    // Init state machine
    // Interactive loop:
    //   - Read commands
    //   - Execute state machine
    //   - Print output
    //   - Loop until quit
}
```

### Compilation Command
```bash
gcc state_machine_test.c -o state_machine_test -Wall -Wexact
```

Flags:
- `-Wall` - Enable all common warnings
- `-Wextra` - Extra warning checks
- `-o` - Output executable name

---

## Limitations & Notes

1. **Data Types**: Currently assumes `int` for all variables
   - Can be enhanced for `float`, `double`, `char`, etc.

2. **Complex Logic**: 
   - Works best with simple state machines
   - Very large machines may need optimization

3. **Platform Specific**:
   - Windows `.exe` vs Linux/Mac binary paths
   - Some compiler features may vary

4. **Floating Point**:
   - Use spinbox with decimals for float testing
   - May require special handling in harness

---

## See Also
- [C_GENERATION_SUMMARY.md](C_GENERATION_SUMMARY.md) - Generation details
- [C_TESTING_GUIDE.md](C_TESTING_GUIDE.md) - Original testing guide
- [IMPLEMENTATION_SUMMARY.txt](IMPLEMENTATION_SUMMARY.txt) - Full architecture
