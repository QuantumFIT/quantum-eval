#!/usr/bin/env python3
"""Shift one angle of one random parameterized gate in an OpenQASM 2 circuit.

Usage: shift-angle.py <EPS> <input.qasm> [output.qasm] [--seed S]   (stdout if no output given)

    --seed S makes the result reproducible
"""
import math
import random
import re
import sys

GATE = re.compile(r"^(\s*)([a-z][a-z0-9_]*)\(([^)]*)\)(\s+.*)$")


def angle(expr):
    """Evaluate an angle expression like 5*pi/2 (only `pi` is allowed)."""
    return eval(expr, {"__builtins__": {}}, {"pi": math.pi})


def main():
    args = sys.argv[1:]
    seed = None
    if "--seed" in args:
        i = args.index("--seed")
        seed = int(args[i + 1])
        del args[i:i + 2]
    if len(args) not in (2, 3):
        sys.exit(__doc__)
    eps, inp = float(args[0]), args[1]

    with open(inp) as f:
        lines = f.read().splitlines()
    gates = [i for i, l in enumerate(lines) if GATE.match(l)]
    if not gates:
        sys.exit(f"{inp}: no parameterized gate to shift")

    rng = random.Random(seed)
    i = rng.choice(gates)
    indent, name, params, rest = GATE.match(lines[i]).groups()
    ps = [p.strip() for p in params.split(",")]
    j = rng.randrange(len(ps))
    ps[j] = repr(angle(ps[j]) + eps)
    new = f"{indent}{name}({','.join(ps)}){rest}"
    print(f"{inp}: line {i + 1}: {lines[i].strip()}  ->  {new.strip()}", file=sys.stderr)
    lines[i] = new
    text = "\n".join(lines) + "\n"

    if len(args) == 3:
        with open(args[2], "w") as f:
            f.write(text)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
