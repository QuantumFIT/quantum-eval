OPENQASM 2.0;
include "qelib1.inc";
qreg q[6];
cx q[5], q[2];
cx q[5], q[0];
x q[5];
x q[0];
