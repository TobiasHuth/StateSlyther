#!/usr/bin/env python3
"""
Test the modified C interactive tester with:
- Only INPUT variables in spinboxes
- All variables as read-only numeric outputs
"""

import sys
sys.path.insert(0, r'c:\Users\User\Documents\AA_Projekte\StateSlyther')

from c_interactive_tester import CInteractiveTester

# Sample C code
sample_c_code = '''
typedef enum {
    STATE1, STATE2
} State;

typedef struct {
    State current_state;
    State previous_state;
    State next_state;
    int counter;
    int trigger;
    int result;
} CStateMachine;

void entry_STATE1(CStateMachine* sm) {
    sm->counter = 0;
}

void during_STATE1(CStateMachine* sm) {
    sm->counter++;
}

void check_transitions_STATE1(CStateMachine* sm) {
    if (sm->trigger) {
        sm->result = sm->counter * 2;
        sm->next_state = STATE2;
        return;
    }
    sm->next_state = sm->current_state;
}

void entry_STATE2(CStateMachine* sm) {
    sm->trigger = 0;
}

void during_STATE2(CStateMachine* sm) { }

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
    sm->result = 0;
}

void c_state_machine_update(CStateMachine* sm) {
    if (sm->previous_state != sm->current_state) {
        if (sm->current_state == STATE1) entry_STATE1(sm);
        else if (sm->current_state == STATE2) entry_STATE2(sm);
    }
    
    if (sm->current_state == STATE1) during_STATE1(sm);
    else if (sm->current_state == STATE2) during_STATE2(sm);
    
    if (sm->current_state == STATE1) check_transitions_STATE1(sm);
    else if (sm->current_state == STATE2) check_transitions_STATE2(sm);
    
    sm->previous_state = sm->current_state;
    sm->current_state = sm->next_state;
}
'''

symbols = {
    'trigger': {'type': 'input', 'description': 'Transition trigger'},
    'counter': {'type': 'local', 'description': 'Internal counter'},
    'result': {'type': 'output', 'description': 'Computation result'},
}

print("=" * 80)
print("C INTERACTIVE TESTER - MODIFIED VERSION")
print("=" * 80)
print("\nChanges:")
print("1. Only INPUT variables shown in spinboxes for user to set:")
print(f"   - trigger (type: input)")
print("\n2. All variables displayed as read-only numeric outputs:")
print(f"   - [IN]  trigger (input variable)")
print(f"   - [LOC] counter (local variable)")
print(f"   - [OUT] result  (output variable)")
print("\n3. Variable values update after each step execution")
print("\nLaunching interactive GUI...")
print("=" * 80)

# Create and compile tester
tester = CInteractiveTester(sample_c_code, symbols=symbols)

if not tester.compiler:
    print("Error: No C compiler found")
    sys.exit(1)

print(f"Found compiler: {tester.compiler}")

success, msg = tester.compile()
print(f"Compilation: {msg}")

if not success:
    sys.exit(1)

print("\nLaunching interactive tester GUI...")
print("(The GUI window should appear shortly)")
tester.run_interactive()
