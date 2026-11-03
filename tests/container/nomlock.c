/* test containers only: unprivileged user namespaces cannot lock memory */
int mlockall(int flags) { (void)flags; return 0; }
