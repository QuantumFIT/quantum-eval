#!/usr/bin/env python3
"""Remove N random gates from an OpenQASM 2 circuit (to create non-equivalent pairs).

Usage: remove-gates.py <N> <input.qasm> [output.qasm] [--seed S]   (stdout if no output given)

    --seed S makes the result reproducible
"""
import random
import sys

NON_GATES = ("OPENQASM", "include", "qreg", "creg", "barrier", "measure", "//")


def gate_line_indices(lines):
    indices, depth = [], 0
    for i, line in enumerate(lines):
        s = line.strip()
        if depth or s.startswith("gate "):
            depth += s.count("{") - s.count("}")
            continue
        if s and not s.startswith(NON_GATES):
            indices.append(i)
    return indices


def main():
    args = sys.argv[1:]
    seed = None
    if "--seed" in args:
        i = args.index("--seed")
        seed = int(args[i + 1])
        del args[i:i + 2]
    if len(args) not in (2, 3):
        sys.exit(__doc__)
    n, inp = int(args[0]), args[1]

    with open(inp) as f:
        lines = f.read().splitlines()
    gates = gate_line_indices(lines)
    if len(gates) < n:
        sys.exit(f"{inp}: only {len(gates)} gates, cannot remove {n}")

    removed = set(random.Random(seed).sample(gates, n))
    for i in sorted(removed):
        print(f"{inp}: removed line {i + 1}: {lines[i].strip()}", file=sys.stderr)
    text = "\n".join(l for i, l in enumerate(lines) if i not in removed) + "\n"

    if len(args) == 3:
        with open(args[2], "w") as f:
            f.write(text)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
