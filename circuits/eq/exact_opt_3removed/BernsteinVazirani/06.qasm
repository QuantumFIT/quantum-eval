OPENQASM 2.0;
include "qelib1.inc";
qreg q[7];
cx q[6], q[4];
cx q[6], q[2];
x q[4];
x q[2];
