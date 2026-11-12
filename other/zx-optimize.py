#!/usr/bin/env python3
"""
Usage: zx-optimize.py <input.qasm> [output.qasm]   (stdout if no output given)
"""
import sys
import pyzx as zx

def optimize(circuit):
    g = circuit.to_graph()
    zx.simplify.full_reduce(g)
    opt = zx.extract_circuit(g.copy())
    opt = zx.optimize.basic_optimization(opt.to_basic_gates())
    return opt.to_basic_gates().split_phase_gates()

def main():
    if len(sys.argv) not in (2, 3):
        sys.exit(__doc__)
    circuit = zx.Circuit.from_qasm_file(sys.argv[1])
    opt = optimize(circuit)
    qasm = opt.to_qasm()
    if len(sys.argv) == 3:
        with open(sys.argv[2], "w") as f:
            f.write(qasm)
    else:
        sys.stdout.write(qasm)


if __name__ == "__main__":
    main()
