#include <errno.h>
#include <pthread.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <sys/random.h>

#include <openssl/sha.h>
#include <secp256k1.h>
#include <secp256k1_extrakeys.h>
#include <secp256k1_schnorrsig.h>

static pthread_once_t ed_nostr_once = PTHREAD_ONCE_INIT;
static secp256k1_context *ed_nostr_context = NULL;

static void ed_nostr_init(void) {
    ed_nostr_context = secp256k1_context_create(SECP256K1_CONTEXT_NONE);
}

static int ed_nostr_hex_nibble(char value) {
    if (value >= '0' && value <= '9') return value - '0';
    if (value >= 'a' && value <= 'f') return value - 'a' + 10;
    if (value >= 'A' && value <= 'F') return value - 'A' + 10;
    return -1;
}

static int ed_nostr_hex_decode(const char *hex, size_t expected, unsigned char *output) {
    if (hex == NULL || output == NULL || strlen(hex) != expected * 2) return 0;
    for (size_t index = 0; index < expected; index++) {
        int high = ed_nostr_hex_nibble(hex[index * 2]);
        int low = ed_nostr_hex_nibble(hex[index * 2 + 1]);
        if (high < 0 || low < 0) return 0;
        output[index] = (unsigned char)((high << 4) | low);
    }
    return 1;
}

static char *ed_nostr_hex_encode(const unsigned char *input, size_t length) {
    static const char alphabet[] = "0123456789abcdef";
    if (input == NULL || length > (SIZE_MAX - 1) / 2) return strdup("");
    char *output = (char *)malloc(length * 2 + 1);
    if (output == NULL) return strdup("");
    for (size_t index = 0; index < length; index++) {
        output[index * 2] = alphabet[input[index] >> 4];
        output[index * 2 + 1] = alphabet[input[index] & 15];
    }
    output[length * 2] = '\0';
    return output;
}

/*
 * Accept a native 32-byte Nostr secret when supplied. Existing Ernos identities
 * carry a 64-byte Ed25519 secret; for those callers, derive a stable independent
 * Nostr secret by SHA-256 hashing the decoded identity secret. The resulting
 * events use ordinary x-only secp256k1 keys and BIP-340 signatures on the wire.
 */
static int ed_nostr_secret(const char *secret_hex, unsigned char secret[32]) {
    if (secret_hex == NULL || secret_hex[0] == '\0') return 0;
    size_t hex_length = strlen(secret_hex);
    if (hex_length == 64 && ed_nostr_hex_decode(secret_hex, 32, secret)) {
        if (secp256k1_ec_seckey_verify(ed_nostr_context, secret)) return 1;
    }
    if ((hex_length & 1U) != 0 || hex_length > 4096) return 0;
    size_t byte_length = hex_length / 2;
    unsigned char *decoded = (unsigned char *)malloc(byte_length == 0 ? 1 : byte_length);
    if (decoded == NULL) return 0;
    if (!ed_nostr_hex_decode(secret_hex, byte_length, decoded)) {
        free(decoded);
        return 0;
    }
    SHA256(decoded, byte_length, secret);
    free(decoded);
    if (!secp256k1_ec_seckey_verify(ed_nostr_context, secret)) {
        unsigned char retry[33];
        memcpy(retry, secret, 32);
        for (unsigned int counter = 1; counter <= 255; counter++) {
            retry[32] = (unsigned char)counter;
            SHA256(retry, sizeof(retry), secret);
            if (secp256k1_ec_seckey_verify(ed_nostr_context, secret)) return 1;
        }
        return 0;
    }
    return 1;
}

char *ed_nostr_pubkey_from_secret(long long secret_hex_value) {
    const char *secret_hex = (const char *)(intptr_t)secret_hex_value;
    if (pthread_once(&ed_nostr_once, ed_nostr_init) != 0 || ed_nostr_context == NULL) return strdup("");
    unsigned char secret[32];
    if (!ed_nostr_secret(secret_hex, secret)) return strdup("");
    secp256k1_keypair keypair;
    secp256k1_xonly_pubkey public_key;
    unsigned char serialized[32];
    if (!secp256k1_keypair_create(ed_nostr_context, &keypair, secret) ||
        !secp256k1_keypair_xonly_pub(ed_nostr_context, &public_key, NULL, &keypair) ||
        !secp256k1_xonly_pubkey_serialize(ed_nostr_context, serialized, &public_key)) {
        memset(secret, 0, sizeof(secret));
        return strdup("");
    }
    memset(secret, 0, sizeof(secret));
    return ed_nostr_hex_encode(serialized, sizeof(serialized));
}

char *ed_nostr_sign_hash(long long hash_hex_value, long long secret_hex_value) {
    const char *hash_hex = (const char *)(intptr_t)hash_hex_value;
    const char *secret_hex = (const char *)(intptr_t)secret_hex_value;
    if (pthread_once(&ed_nostr_once, ed_nostr_init) != 0 || ed_nostr_context == NULL) return strdup("");
    unsigned char message[32];
    unsigned char secret[32];
    unsigned char auxiliary[32];
    unsigned char signature[64];
    if (!ed_nostr_hex_decode(hash_hex, sizeof(message), message) || !ed_nostr_secret(secret_hex, secret)) return strdup("");
    if (getentropy(auxiliary, sizeof(auxiliary)) != 0) {
        memset(secret, 0, sizeof(secret));
        return strdup("");
    }
    secp256k1_keypair keypair;
    if (!secp256k1_keypair_create(ed_nostr_context, &keypair, secret) ||
        !secp256k1_schnorrsig_sign32(ed_nostr_context, signature, message, &keypair, auxiliary)) {
        memset(secret, 0, sizeof(secret));
        memset(auxiliary, 0, sizeof(auxiliary));
        return strdup("");
    }
    memset(secret, 0, sizeof(secret));
    memset(auxiliary, 0, sizeof(auxiliary));
    return ed_nostr_hex_encode(signature, sizeof(signature));
}

long long ed_nostr_verify_hash(long long hash_hex_value, long long signature_hex_value,
                               long long public_key_hex_value) {
    const char *hash_hex = (const char *)(intptr_t)hash_hex_value;
    const char *signature_hex = (const char *)(intptr_t)signature_hex_value;
    const char *public_key_hex = (const char *)(intptr_t)public_key_hex_value;
    if (pthread_once(&ed_nostr_once, ed_nostr_init) != 0 || ed_nostr_context == NULL) return 0;
    unsigned char message[32];
    unsigned char signature[64];
    unsigned char public_key_bytes[32];
    secp256k1_xonly_pubkey public_key;
    if (!ed_nostr_hex_decode(hash_hex, sizeof(message), message) ||
        !ed_nostr_hex_decode(signature_hex, sizeof(signature), signature) ||
        !ed_nostr_hex_decode(public_key_hex, sizeof(public_key_bytes), public_key_bytes) ||
        !secp256k1_xonly_pubkey_parse(ed_nostr_context, &public_key, public_key_bytes)) return 0;
    return secp256k1_schnorrsig_verify(ed_nostr_context, signature, message, sizeof(message), &public_key) == 1;
}
