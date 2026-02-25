#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <sodium.h>

#define SERVER_PORT 9000
#define SIGNATURE_SIZE crypto_sign_BYTES
#define PRIVATE_KEY_SIZE crypto_sign_SECRETKEYBYTES

int main() {

    if (sodium_init() < 0) {
        printf("libsodium init failed\n");
        return 1;
    }

    // Load private key
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

    int counter = 0;
    char payload[256];

    while (1) {

        snprintf(payload, sizeof(payload), "hello %d", counter);

        unsigned char signature[SIGNATURE_SIZE];

        crypto_sign_detached(signature,
                             NULL,
                             (unsigned char*)payload,
                             strlen(payload),
                             sk);

        unsigned char packet[512];
        size_t payload_len = strlen(payload);

        memcpy(packet, payload, payload_len);
        memcpy(packet + payload_len, signature, SIGNATURE_SIZE);

        sendto(sock,
               packet,
               payload_len + SIGNATURE_SIZE,
               0,
               (struct sockaddr*)&server_addr,
               sizeof(server_addr));

        printf("Signed packet sent: %s\n", payload);

        counter++;
        sleep(3);
    }

    close(sock);
    return 0;
}