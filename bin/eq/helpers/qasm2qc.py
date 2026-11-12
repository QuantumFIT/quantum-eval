#!/usr/bin/env python3
"""Convert an OpenQASM 2 circuit to Feynman's .qc format (for feynver).

Usage: qasm2qc.py <input.qasm> <output.qc>

All qubits are declared as inputs (.i), so feynver checks full equivalence.
Qubits are named q0..q(n-1) by position (register names differ between files,
and feynver requires both circuits to have the same input names).
Only exactly representable gates are supported; anything else is an error.
"""
import re
import sys

SKIP = ("OPENQASM", "include", "creg", "barrier", "measure", "//")
LINE = re.compile(r"^([a-z][a-z0-9_]*)(\([^)]*\))?\s+(.+);$")
QUBIT = re.compile(r"(\w+)\[(\d+)\]")

# gate (with normalized parameter) -> list of (qc gate, operand indices)
GATES = {
    "x": [("X", (0,))], "y": [("Y", (0,))], "z": [("Z", (0,))], "h": [("H", (0,))],
    "s": [("S", (0,))], "sdg": [("S*", (0,))], "t": [("T", (0,))], "tdg": [("T*", (0,))],
    "cx": [("tof", (0, 1))], "cz": [("Z", (0, 1))], "ccx": [("tof", (0, 1, 2))],
    "swap": [("swap", (0, 1))],
    # equal up to a global phase (feynver runs with -ignore-global-phase)
    "rx(pi/2)": [("H", (0,)), ("S", (0,)), ("H", (0,))],
    "rx(-pi/2)": [("H", (0,)), ("S*", (0,)), ("H", (0,))],
    # exactly equal
    "ry(pi/2)": [("Z", (0,)), ("H", (0,))],
    "ry(-pi/2)": [("H", (0,)), ("Z", (0,))],
}


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    names, body, offset = [], [], {}
    for raw in open(sys.argv[1]):
        s = raw.split("//")[0].strip()
        if not s or s.startswith(SKIP):
            continue
        m = re.fullmatch(r"qreg\s+(\w+)\[(\d+)\];", s)
        if m:
            offset[m.group(1)] = len(names)
            names += [f"q{len(names) + i}" for i in range(int(m.group(2)))]
            continue
        m = LINE.match(s)
        if not m:
            sys.exit(f"cannot parse: {s}")
        key = m.group(1) + (m.group(2) or "").replace(" ", "")
        if key not in GATES:
            sys.exit(f"unsupported gate: {s}")
        qubits = [f"q{offset[r] + int(i)}" for r, i in QUBIT.findall(m.group(3))]
        for gate, idx in GATES[key]:
            body.append(gate + " " + " ".join(qubits[i] for i in idx))
    with open(sys.argv[2], "w") as f:
        f.write(f".v {' '.join(names)}\n.i {' '.join(names)}\n\nBEGIN\n")
        f.write("\n".join(body) + "\nEND\n")


if __name__ == "__main__":
    main()
