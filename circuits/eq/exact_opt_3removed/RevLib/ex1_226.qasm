OPENQASM 2.0;
include "qelib1.inc";
qreg q[6];
cx q[1], q[0];
cx q[3], q[0];
x q[4];
x q[2];
