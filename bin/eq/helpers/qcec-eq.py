#!/usr/bin/env python3
"""Check equivalence of two circuits with MQT QCEC and print the verdict.

Usage: qcec-eq.py [--parallel] <circuit1.qasm> <circuit2.qasm>

Prints eq | neq | unknown (QCEC default settings).
By default the checkers run one after another in a single thread;
--parallel runs them at the same time (QCEC's own default, one thread per core).
"""
import sys

from mqt import qcec

RESULTS = {
    "equivalent": "eq",
    "equivalent_up_to_global_phase": "eq",
    "not_equivalent": "neq",
    "probably_equivalent": "unknown",
    "probably_not_equivalent": "unknown",
    "no_information": "unknown",
}


def main():
    args = sys.argv[1:]
    parallel = "--parallel" in args
    if parallel:
        args.remove("--parallel")
    if len(args) != 2:
        sys.exit(__doc__)
    # single thread by default, so QCEC competes on the same resources as the other tools
    res = qcec.verify(args[0], args[1], parallel=parallel)
    criterion = str(res.equivalence).split(".")[-1]
    print(f"criterion:{criterion}")
    print(f"result:{RESULTS.get(criterion, 'unknown')}")


if __name__ == "__main__":
    main()
