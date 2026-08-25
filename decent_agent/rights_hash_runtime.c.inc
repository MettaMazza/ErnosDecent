/* Exact file-byte SHA-256 for protected recovery and rollback proofs. Ernos strings
   are NUL-terminated, so hashing read_file(path) would truncate binary files. */
#include <openssl/evp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

long long ep_sha256_file(long long path_ptr) {
    const char* path = (const char*)path_ptr;
    if (!path || path[0] == '\0') return (long long)strdup("");
    FILE* file = fopen(path, "rb");
    if (!file) return (long long)strdup("");
    EVP_MD_CTX* context = EVP_MD_CTX_new();
    if (!context || EVP_DigestInit_ex(context, EVP_sha256(), NULL) != 1) {
        if (context) EVP_MD_CTX_free(context);
        fclose(file);
        return (long long)strdup("");
    }
    unsigned char buffer[65536];
    size_t count = 0;
    while ((count = fread(buffer, 1, sizeof(buffer), file)) > 0) {
        if (EVP_DigestUpdate(context, buffer, count) != 1) {
            EVP_MD_CTX_free(context);
            fclose(file);
            return (long long)strdup("");
        }
    }
    if (ferror(file)) {
        EVP_MD_CTX_free(context);
        fclose(file);
        return (long long)strdup("");
    }
    fclose(file);
    unsigned char digest[EVP_MAX_MD_SIZE];
    unsigned int digest_length = 0;
    if (EVP_DigestFinal_ex(context, digest, &digest_length) != 1 || digest_length != 32) {
        EVP_MD_CTX_free(context);
        return (long long)strdup("");
    }
    EVP_MD_CTX_free(context);
    char* hex = (char*)malloc((size_t)digest_length * 2 + 1);
    if (!hex) return (long long)strdup("");
    static const char digits[] = "0123456789abcdef";
    for (size_t i = 0; i < (size_t)digest_length; ++i) {
        hex[i * 2] = digits[(digest[i] >> 4) & 0x0f];
        hex[i * 2 + 1] = digits[digest[i] & 0x0f];
    }
    hex[(size_t)digest_length * 2] = '\0';
    return (long long)hex;
}
