#!/usr/bin/env python3
"""Quokka# equivalence check helper.

Usage:
  quokka-eq.py prep  <in.qasm> <out.qasm>       translate to Quokka#'s gate set (if needed)
  quokka-eq.py check [--pauli] <circuit1.qasm> <circuit2.qasm>

`prep` keeps the file as is when all gates are supported, otherwise it
translates it with Qiskit (no optimization) and writes angles as plain numbers.
`check` prints result:eq|neq|unknown|error (QUOKKA_CONFIG must be set).
Default: computational basis, cyclic check (one model count).
--pauli: Pauli basis, linear check (2n model counts, one at a time).
"""
import re
import shutil
import sys

SUPPORTED = {"id", "h", "x", "y", "z", "s", "sdg", "t", "tdg",
             "cx", "cy", "cz", "swap", "ccx", "rx", "ry", "rz"}
SKIP = ("OPENQASM", "include", "qreg", "creg", "barrier", "measure", "//")


def needs_translation(path):
    for line in open(path):
        s = line.strip()
        if s and not s.startswith(SKIP):
            if re.match(r"[a-z][a-z0-9_]*", s).group(0) not in SUPPORTED:
                return True
    return False


def prep(src, dst):
    if not needs_translation(src):
        shutil.copyfile(src, dst)
        return
    from qiskit import qasm2, transpile
    qc = qasm2.load(src, custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS)
    qc = transpile(qc, basis_gates=sorted(SUPPORTED - {"id"}), optimization_level=0)
    lines = ['OPENQASM 2.0;', 'include "qelib1.inc";', f"qreg q[{qc.num_qubits}];"]
    for inst in qc.data:
        name = inst.operation.name
        if name == "barrier":
            continue
        params = ",".join(repr(float(p)) for p in inst.operation.params)
        qubits = ", ".join(f"q[{qc.find_bit(q).index}]" for q in inst.qubits)
        lines.append(f"{name}({params}) {qubits};" if params else f"{name} {qubits};")
    with open(dst, "w") as f:
        f.write("\n".join(lines) + "\n")


def check(c1, c2, pauli=False):
    import quokka_sharp as qk
    if pauli:
        # Pauli basis, 2n model counts one after another (N=1), stops at the first failing one
        res = qk.functionalities.eq(c1, c2, basis="pauli", check="linear", N=1, epsilon=0)
    else:
        res = qk.functionalities.eq(c1, c2, basis="comp", check="cyclic", epsilon=0)
    if res is True or res == "True":
        print("result:eq")
    elif res is False or res == "False":
        print("result:neq")
    elif res in ("TIMEOUT", "MEMOUT"):
        print(f"quokka:{res}")
        print("result:unknown")
    else:
        print(f"quokka:{res}")
        print("result:error")


def main():
    args = sys.argv[1:]
    pauli = "--pauli" in args
    if pauli:
        args.remove("--pauli")
    if len(args) != 3 or args[0] not in ("prep", "check") or (pauli and args[0] != "check"):
        sys.exit(__doc__)
    if args[0] == "prep":
        prep(args[1], args[2])
    else:
        check(args[1], args[2], pauli)


if __name__ == "__main__":
    main()
