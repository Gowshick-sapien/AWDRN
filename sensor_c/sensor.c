#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <netdb.h>

#define SERVER_PORT 9000

int main() {

    int sock;
    struct sockaddr_in server_addr;
    struct hostent *server;

    sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock < 0) {
        perror("Socket creation failed");
        exit(1);
    }

    // Resolve hostname "network"
    server = gethostbyname("network");
    if (server == NULL) {
        fprintf(stderr, "ERROR: no such host\n");
        exit(1);
    }

    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(SERVER_PORT);
    memcpy(&server_addr.sin_addr.s_addr,
           server->h_addr,
           server->h_length);

    int counter = 0;
    char buffer[256];

    while (1) {
        snprintf(buffer, sizeof(buffer), "hello %d", counter);

        sendto(sock,
               buffer,
               strlen(buffer),
               0,
               (struct sockaddr *)&server_addr,
               sizeof(server_addr));

        printf("C Sensor sent: %s\n", buffer);

        counter++;
        sleep(3);
    }

    close(sock);
    return 0;
}