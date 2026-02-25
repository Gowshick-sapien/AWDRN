#include <sodium.h>
#include <stdio.h>

int main() {
    if (sodium_init() < 0) return 1;

    unsigned char pk[crypto_sign_PUBLICKEYBYTES];
    unsigned char sk[crypto_sign_SECRETKEYBYTES];

    crypto_sign_keypair(pk, sk);

    FILE *f1 = fopen("sensor_private.key", "wb");
    fwrite(sk, 1, crypto_sign_SECRETKEYBYTES, f1);
    fclose(f1);

    FILE *f2 = fopen("sensor_public.key", "wb");
    fwrite(pk, 1, crypto_sign_PUBLICKEYBYTES, f2);
    fclose(f2);

    return 0;
}