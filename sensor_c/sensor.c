#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <sodium.h>
#include <stdint.h>

#define SERVER_PORT 9000
#define SIGNATURE_SIZE crypto_sign_BYTES
#define PRIVATE_KEY_SIZE crypto_sign_SECRETKEYBYTES

int main() {

    if (sodium_init() < 0) {
        printf("libsodium init failed\n");
        return 1;
    }

    unsigned char sk[PRIVATE_KEY_SIZE];
    FILE *keyfile = fopen("keys/sensor_private.key", "rb");
    if (!keyfile) {
        perror("Private key not found");
        exit(1);
    }
    fread(sk, 1, PRIVATE_KEY_SIZE, keyfile);
    fclose(keyfile);

    int sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock < 0) {
        perror("Socket failed");
        exit(1);
    }

    struct hostent *server = gethostbyname("network");
    if (!server) {
        fprintf(stderr, "ERROR: no such host\n");
        exit(1);
    }

    struct sockaddr_in server_addr;
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(SERVER_PORT);
    memcpy(&server_addr.sin_addr.s_addr,
           server->h_addr,
           server->h_length);

    uint64_t counter = 0;

    while (1) {

        char payload_text[256];
        snprintf(payload_text, sizeof(payload_text), "hello %lu", counter);

        uint16_t payload_len = strlen(payload_text);

        // Build structured buffer
        unsigned char structured[512];

        uint64_t net_counter = htobe64(counter);
        uint16_t net_len = htons(payload_len);

        memcpy(structured, &net_counter, 8);
        memcpy(structured + 8, &net_len, 2);
        memcpy(structured + 10, payload_text, payload_len);

        unsigned char signature[SIGNATURE_SIZE];

        crypto_sign_detached(signature,
                             NULL,
                             structured,
                             10 + payload_len,
                             sk);

        unsigned char packet[1024];
        memcpy(packet, structured, 10 + payload_len);
        memcpy(packet + 10 + payload_len,
               signature,
               SIGNATURE_SIZE);

        sendto(sock,
               packet,
               10 + payload_len + SIGNATURE_SIZE,
               0,
               (struct sockaddr*)&server_addr,
               sizeof(server_addr));

        printf("Sent counter %lu\n", counter);

        counter++;
        sleep(3);
    }

    close(sock);
    return 0;
}