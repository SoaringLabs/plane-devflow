#include <mach/mach.h>
#include <servers/bootstrap.h>
#include <stdio.h>

// Only resolve a service port. Never send a keychain request or read a secret.
int main(int argc, char **argv) {
    if (argc != 2) return 2;
    mach_port_t port = MACH_PORT_NULL;
    kern_return_t result = bootstrap_look_up(bootstrap_port, argv[1], &port);
    if (port != MACH_PORT_NULL) mach_port_deallocate(mach_task_self(), port);
    printf("%d\n", result);
    return result == KERN_SUCCESS ? 0 : 1;
}
