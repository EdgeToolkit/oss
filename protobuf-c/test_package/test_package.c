#include <stdio.h>
#include <protobuf-c/protobuf-c.h>

int main() {
    const char* ver = protobuf_c_version();
    printf("protobuf-c %s", ver);
    return 0;
}
