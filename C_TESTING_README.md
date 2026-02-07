# Enhanced Interactive C Code Testing System

## Overview

The StateSlyther C code generator now supports **interactive compiled C code testing** with automatic compilation, GUI-based variable manipulation, and real-time state monitoring. This allows you to test your generated state machine in actual compiled C code, not just syntax validation.

---

## Key Features

### ✅ Automatic Compiler Detection
- Automatically finds gcc, clang, or MSVC on your system
- Works on Windows, Linux, and macOS
- Graceful fallback with suggestions if no compiler found

### ✅ One-Click Testing
- Generate C code → Click "Test C Code (Compile)" → Interactive tester launches
- Automatic test harness generation
- Complete compilation pipeline

### ✅ Interactive GUI Tester
- **Real-time state display** - Monitor current/previous/next states
- **Symbol controls** - Spinboxes to set input variables before each step
- **Step-by-step execution** - Execute one state machine cycle at a time
- **Live monitoring** - Watch all variables change in real-time

### ✅ Test Harness Generation
Automatically generates a complete C program with:
- Structure definitions and state enums
- All entry, during, and transition functions
- Interactive main() loop with command support
- Symbol manipulation and display

---

## Quick Start

### 1. Verify C Compiler Setup

**Windows:**
```batch
setup_c_tester.bat
```

**Linux/Mac:**
```bash
bash setup_c_tester.sh
```

### 2. Generate & Test C Code

1. Create your state diagram in StateSlyther
2. Go to **Code → Set Language → C**
3. Go to **Code → Update/Show Code**
4. Click **"Test C Code (Compile)"** button
5. Click **"Compile & Test"** in the status window
6. Use the interactive tester GUI

### 3. Use the Interactive Tester

**Symbol Controls:**
```
counter: [spinbox: 0]    Value of the counter variable
trigger: [spinbox: 0]    Input trigger flag
output:  [spinbox: 0]    Output variable
```

**Action Buttons:**
- **Execute Step** - Run one state machine cycle with current values
- **Reset** - Clear all settings and output

**Output Display:**
Shows current/previous/next states and all variable values after each step.

---

## Installation & Setup

### Windows

**Option 1: MinGW (Recommended)**
```
1. Download: https://www.mingw-w64.org/
2. Run installer, add to PATH
3. Verify: gcc --version
```

**Option 2: Chocolatey**
```powershell
choco install mingw
```

**Option 3: Visual Studio Community**
```
1. Download: https://visualstudio.microsoft.com/
2. Select "Desktop development with C++"
3. Install MSVC compiler
```

### Linux

**Ubuntu/Debian:**
```bash
sudo apt-get install build-essential python3-tk
```

**Fedora/CentOS:**
```bash
sudo dnf groupinstall "Development Tools"
sudo dnf install python3-tkinter
```

### macOS

```bash
brew install gcc
# Python and Tkinter usually included
```

---

## How It Works

### 1. Code Generation
```
State Diagram → C Code Generator → Complete .c program
```

### 2. Test Harness Creation
```
Generated C Code → Wraps in main() → Adds interactive functions
```

### 3. Compilation
```
C Harness → GCC/Clang → Executable binary
```

### 4. Interactive Testing
```
Binary executable → GUI controls → Variable manipulation → State monitoring
```

### 5. Execution Flow
```
User sets inputs → Click Step → Machine executes → Display updates
```

---

## File Structure

```
StateSlyther/
├── code_generators.py              # Main code generation (updated)
├── c_interactive_tester.py         # NEW: C testing system
├── graphical_master.py             # GUI (uses code_generators)
├── INTERACTIVE_C_TESTING.md        # Usage guide
├── setup_c_tester.bat              # Windows setup
├── setup_c_tester.sh               # Linux/Mac setup
└── C_TESTING_README.md             # This file
```

---

## Generated Test Harness Example

### Original Generated Code
```c
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
```

### Enhanced With Test Harness
```c
// Original code above...

// Interactive functions
void print_state_machine(CStateMachine* sm) {
    printf("Current State: %d\n", sm->current_state);
    // ...
}

int main() {
    CStateMachine sm;
    c_state_machine_init(&sm);
    
    while(1) {
        printf("> ");
        // Parse commands: step, set, state, symbols, quit
        // Execute state machine
        // Display results
    }
    return 0;
}
```

---

## Testing Workflow

### Workflow 1: Verify State Transitions

```
1. Start: Initial state displayed
2. Click "Execute Step" 5 times
3. Set input variable: "trigger" = 1
4. Click "Execute Step"
5. Observe: State changes in output
```

### Workflow 2: Test Entry/During/Exit Code

```
1. Enter STATE1 → entry code executes (counter = 0)
2. Click "Execute Step" → during code executes (counter++)
3. Set "trigger" = 1
4. Click "Execute Step" → exit code executes, transition to STATE2
5. Enter STATE2 → new entry code executes
```

### Workflow 3: Test Multiple Inputs

```
1. Set: input_a = 1
2. Step: execute
3. Set: input_b = 1
4. Step: execute
5. Observe compound condition results
```

---

## Troubleshooting

### Issue: "No C compiler found"

**Solution 1: Install Compiler**
- Windows: Run `setup_c_tester.bat`
- Linux: Follow distro-specific instructions above
- macOS: Run `brew install gcc`

**Solution 2: Use Online Compiler**
- Copy generated C code
- Visit [OnlineGDB](https://www.onlinegdb.com/)
- Paste code and test there

**Solution 3: Verify PATH**
```bash
# Check if gcc is in PATH
gcc --version

# Add to PATH if needed
# Windows: System Properties → Environment Variables → PATH
# Linux/Mac: Edit ~/.bashrc or ~/.zshrc
```

### Issue: Compilation Errors

**Common causes:**
1. Python syntax in code blocks (e.g., `print()` instead of `printf()`)
2. Invalid variable names (must match symbols)
3. Symbol type mismatch
4. Missing semicolons

**Solution:**
- Read compiler error messages carefully
- Edit state diagram code blocks to fix issues
- Regenerate and test again

### Issue: Tester window doesn't open

**Solutions:**
1. Ensure Tkinter is installed
   ```bash
   python3 -c "import tkinter; print('OK')"
   ```

2. Check Python version (3.6+)
   ```bash
   python --version
   ```

3. Try running setup script first
   - Windows: `setup_c_tester.bat`
   - Linux/Mac: `bash setup_c_tester.sh`

---

## Advanced Usage

### Manual Compilation (Command Line)

```bash
# Compile the test harness
gcc state_machine_test.c -o state_machine_test -Wall -Wextra

# Run interactively
./state_machine_test

# Example commands
step
set counter 5
state
symbols
quit
```

### Custom Test Harness

Modify `c_interactive_tester.py` to:
- Add custom print functions
- Include debugging output
- Add performance monitoring
- Extend command set

### Batch Testing

```python
from c_interactive_tester import CInteractiveTester

tester = CInteractiveTester(c_code, symbols, nodes)
tester.compile()

# Run multiple test scenarios
for scenario in test_scenarios:
    # Set variables
    # Execute
    # Verify output
```

---

## Performance Considerations

### Compilation Time
- **Small machines**: < 1 second
- **Medium machines**: < 2 seconds
- **Large machines**: < 5 seconds

### Execution
- Each step is instant (no delay)
- GUI updates in real-time
- No memory leaks (temporary files cleaned up)

### Optimization
```bash
# Add optimization flags if needed
gcc file.c -o executable -O2 -Wall -Wextra
```

---

## Platform-Specific Notes

### Windows
- Executables saved as `.exe`
- Paths use backslashes internally
- MinGW gcc recommended for consistency

### Linux
- Executables have no extension
- Standard gcc/clang available
- Build-essential package needed

### macOS
- Clang is default compiler
- gcc available via Homebrew
- Tkinter included with Python

---

## Limitations & Future Enhancements

### Current Limitations
1. Variables assumed to be `int` type (future: `float`, `double`, `char`)
2. Single-step execution only (future: breakpoints, batch mode)
3. No memory debugging (future: valgrind integration)
4. Console I/O only (future: graphical visualization)

### Planned Enhancements
- [ ] Support for `float` and `double` types
- [ ] State transition visualization
- [ ] Performance profiling
- [ ] Breakpoints and watches
- [ ] Record/playback test sequences
- [ ] Export test results to HTML

---

## See Also

- [INTERACTIVE_C_TESTING.md](INTERACTIVE_C_TESTING.md) - Detailed usage guide
- [C_GENERATION_SUMMARY.md](C_GENERATION_SUMMARY.md) - Code generation details
- [C_TESTING_GUIDE.md](C_TESTING_GUIDE.md) - Validation guide
- [IMPLEMENTATION_SUMMARY.txt](IMPLEMENTATION_SUMMARY.txt) - Architecture overview

---

## Support & Feedback

For issues or feature requests:
1. Check troubleshooting section above
2. Verify compiler installation
3. Test with simple example first
4. Check generated C code syntax

---

**Happy Testing! 🚀**
