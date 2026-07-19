#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

char *ed_nostr_pubkey_from_secret(long long secret_hex);
char *ed_nostr_sign_hash(long long hash_hex, long long secret_hex);
long long ed_nostr_verify_hash(long long hash_hex, long long signature_hex, long long public_key_hex);

static long long pointer_value(const char *value) {
    return (long long)(intptr_t)value;
}

int main(void) {
    const char *secret = "0000000000000000000000000000000000000000000000000000000000000003";
    const char *public_key = "f9308a019258c31049344f85f89d5229b531c845836f99b08601f113bce036f9";
    const char *message = "0000000000000000000000000000000000000000000000000000000000000000";
    const char *official_signature = "e907831f80848d1069a5371b402410364bdf1c5f8307b0084c55f1ce2dca821525f66a4a85ea8b71e482a74f382d2ce5ebeee8fdb2172f477df4900d310536c0";
    int failures = 0;

    char *derived = ed_nostr_pubkey_from_secret(pointer_value(secret));
    if (strcmp(derived, public_key) != 0) {
        fprintf(stderr, "FAIL: BIP-340 vector 0 public key mismatch\n");
        failures++;
    } else {
        puts("PASS: BIP-340 vector 0 public key");
    }
    free(derived);

    if (!ed_nostr_verify_hash(pointer_value(message), pointer_value(official_signature), pointer_value(public_key))) {
        fprintf(stderr, "FAIL: BIP-340 vector 0 signature rejected\n");
        failures++;
    } else {
        puts("PASS: BIP-340 vector 0 signature verification");
    }

    char *signature = ed_nostr_sign_hash(pointer_value(message), pointer_value(secret));
    if (strlen(signature) != 128 ||
        !ed_nostr_verify_hash(pointer_value(message), pointer_value(signature), pointer_value(public_key))) {
        fprintf(stderr, "FAIL: generated BIP-340 signature did not verify\n");
        failures++;
    } else {
        puts("PASS: generated BIP-340 signature verification");
    }
    signature[0] = signature[0] == '0' ? '1' : '0';
    if (ed_nostr_verify_hash(pointer_value(message), pointer_value(signature), pointer_value(public_key))) {
        fprintf(stderr, "FAIL: corrupted BIP-340 signature accepted\n");
        failures++;
    } else {
        puts("PASS: corrupted BIP-340 signature rejection");
    }
    free(signature);
    return failures == 0 ? 0 : 1;
}
