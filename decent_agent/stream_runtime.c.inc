/* Incremental HTTP/SSE decoder used by llm_read_response.
   Each socket byte is framed once: headers once, HTTP chunks once, SSE lines once.
   The complete wire response is retained only for the non-SSE compatibility path. */
typedef struct {
    char *raw;
    size_t raw_len, raw_cap, processed;
    int headers_done, is_sse, is_chunked, direct_sse, failed;
    int chunk_phase; /* 0=size line, 1=data, 2=data CRLF, 3=terminal */
    size_t chunk_remaining;
    int chunk_crlf_remaining;
    char chunk_size[64];
    size_t chunk_size_len;
    char *line;
    size_t line_len, line_cap;
} EpSseDecoder;

static int ep_stream_reserve(char **buf, size_t *cap, size_t need) {
    if (need <= *cap) return 1;
    size_t next = *cap ? *cap : 1024;
    while (next < need) {
        if (next > ((size_t)-1) / 2) return 0;
        next *= 2;
    }
    char *grown = (char*)realloc(*buf, next);
    if (!grown) return 0;
    *buf = grown; *cap = next;
    return 1;
}

static int ep_stream_ascii_contains_ci(const char *hay, size_t hlen, const char *needle) {
    size_t nlen = strlen(needle), i, j;
    if (nlen == 0 || nlen > hlen) return 0;
    for (i = 0; i + nlen <= hlen; i++) {
        for (j = 0; j < nlen; j++) {
            unsigned char a = (unsigned char)hay[i+j], b = (unsigned char)needle[j];
            if (a >= 'A' && a <= 'Z') a = (unsigned char)(a + ('a' - 'A'));
            if (b >= 'A' && b <= 'Z') b = (unsigned char)(b + ('a' - 'A'));
            if (a != b) break;
        }
        if (j == nlen) return 1;
    }
    return 0;
}

static int ep_stream_append_output(char **out, size_t *olen, size_t *ocap,
                                   const char *data, size_t len) {
    if (!ep_stream_reserve(out, ocap, *olen + len + 1)) return 0;
    if (len) memcpy(*out + *olen, data, len);
    *olen += len; (*out)[*olen] = 0;
    return 1;
}

static int ep_stream_sse_byte(EpSseDecoder *d, unsigned char c,
                              char **out, size_t *olen, size_t *ocap) {
    if (c == '\n') {
        size_t emit = d->line_len;
        if (emit && d->line[emit-1] == '\r') emit--;
        if (!ep_stream_append_output(out, olen, ocap, d->line, emit) ||
            !ep_stream_append_output(out, olen, ocap, "\n", 1)) return 0;
        d->line_len = 0;
        return 1;
    }
    if (!ep_stream_reserve(&d->line, &d->line_cap, d->line_len + 2)) return 0;
    d->line[d->line_len++] = (char)c;
    d->line[d->line_len] = 0;
    return 1;
}

static int ep_stream_parse_chunk_size(EpSseDecoder *d) {
    size_t i = 0;
    unsigned long long value = 0;
    int saw_digit = 0;
    while (i < d->chunk_size_len && (d->chunk_size[i] == ' ' || d->chunk_size[i] == '\t')) i++;
    for (; i < d->chunk_size_len; i++) {
        unsigned char c = (unsigned char)d->chunk_size[i];
        int digit;
        if (c == ';' || c == '\r' || c == ' ' || c == '\t') break;
        if (c >= '0' && c <= '9') digit = c - '0';
        else if (c >= 'a' && c <= 'f') digit = c - 'a' + 10;
        else if (c >= 'A' && c <= 'F') digit = c - 'A' + 10;
        else return 0;
        if (value > (((unsigned long long)(size_t)-1) - (unsigned long long)digit) / 16ULL) return 0;
        value = value * 16ULL + (unsigned long long)digit;
        saw_digit = 1;
    }
    if (!saw_digit) return 0;
    d->chunk_remaining = (size_t)value;
    d->chunk_size_len = 0;
    if (d->chunk_remaining == 0) d->chunk_phase = 3;
    else d->chunk_phase = 1;
    return 1;
}

static int ep_stream_process_body(EpSseDecoder *d, const char *body, size_t len,
                                  char **out, size_t *olen, size_t *ocap) {
    size_t i = 0;
    if (!d->is_chunked) {
        for (; i < len; i++) if (!ep_stream_sse_byte(d, (unsigned char)body[i], out, olen, ocap)) return 0;
        return 1;
    }
    while (i < len && d->chunk_phase != 3) {
        if (d->chunk_phase == 0) {
            unsigned char c = (unsigned char)body[i++];
            if (c == '\n') {
                if (!ep_stream_parse_chunk_size(d)) return 0;
            } else if (c != '\r') {
                if (d->chunk_size_len + 1 >= sizeof(d->chunk_size)) return 0;
                d->chunk_size[d->chunk_size_len++] = (char)c;
            }
        } else if (d->chunk_phase == 1) {
            size_t take = len - i;
            if (take > d->chunk_remaining) take = d->chunk_remaining;
            size_t end = i + take;
            for (; i < end; i++) if (!ep_stream_sse_byte(d, (unsigned char)body[i], out, olen, ocap)) return 0;
            d->chunk_remaining -= take;
            if (d->chunk_remaining == 0) { d->chunk_phase = 2; d->chunk_crlf_remaining = 2; }
        } else {
            unsigned char c = (unsigned char)body[i++];
            if (d->chunk_crlf_remaining == 2 && c == '\r') d->chunk_crlf_remaining = 1;
            else if ((d->chunk_crlf_remaining == 2 || d->chunk_crlf_remaining == 1) && c == '\n') d->chunk_crlf_remaining = 0;
            else return 0;
            if (d->chunk_crlf_remaining == 0) d->chunk_phase = 0;
        }
    }
    return 1;
}

long long ep_sse_decoder_create(void) {
    EpSseDecoder *d = (EpSseDecoder*)calloc(1, sizeof(EpSseDecoder));
    return (long long)d;
}

long long ep_sse_decoder_feed(long long decoder_ptr, long long chunk_ptr) {
    EpSseDecoder *d = (EpSseDecoder*)decoder_ptr;
    const char *chunk = (const char*)chunk_ptr;
    char *out = NULL; size_t olen = 0, ocap = 0;
    if (!d || !chunk || d->failed) return (long long)strdup("");
    size_t clen = strlen(chunk);
    if (d->direct_sse) {
        if (!ep_stream_process_body(d, chunk, clen, &out, &olen, &ocap)) d->failed = 1;
        if (!out) out = strdup("");
        return (long long)out;
    }
    size_t previous_len = d->raw_len;
    if (!ep_stream_reserve(&d->raw, &d->raw_cap, d->raw_len + clen + 1)) d->failed = 1;
    if (!d->failed) {
        memcpy(d->raw + d->raw_len, chunk, clen);
        d->raw_len += clen; d->raw[d->raw_len] = 0;
    }
    if (!d->failed && !d->headers_done) {
        size_t i;
        for (i = previous_len > 3 ? previous_len - 3 : 0; i + 3 < d->raw_len; i++) {
            if (d->raw[i]=='\r' && d->raw[i+1]=='\n' && d->raw[i+2]=='\r' && d->raw[i+3]=='\n') {
                size_t header_len = i + 4;
                d->headers_done = 1;
                d->is_sse = ep_stream_ascii_contains_ci(d->raw, header_len, "content-type: text/event-stream");
                d->is_chunked = ep_stream_ascii_contains_ci(d->raw, header_len, "transfer-encoding: chunked");
                d->processed = header_len;
                break;
            }
        }
    }
    if (!d->failed && d->headers_done && d->is_sse && d->processed < d->raw_len) {
        if (!ep_stream_process_body(d, d->raw + d->processed, d->raw_len - d->processed, &out, &olen, &ocap)) d->failed = 1;
        d->processed = d->raw_len;
    }
    /* Once the header proves this is SSE, the compatibility wire copy is no longer
       needed. Release it and frame all later socket chunks directly. */
    if (!d->failed && d->headers_done && d->is_sse) {
        free(d->raw); d->raw = NULL; d->raw_len = 0; d->raw_cap = 0; d->processed = 0;
        d->direct_sse = 1;
    }
    if (!out) out = strdup("");
    return (long long)out;
}

long long ep_sse_decoder_is_sse(long long decoder_ptr) {
    EpSseDecoder *d = (EpSseDecoder*)decoder_ptr;
    return d ? d->is_sse : 0;
}

long long ep_sse_decoder_error(long long decoder_ptr) {
    EpSseDecoder *d = (EpSseDecoder*)decoder_ptr;
    return d ? d->failed : 1;
}

long long ep_sse_decoder_finish(long long decoder_ptr) {
    EpSseDecoder *d = (EpSseDecoder*)decoder_ptr;
    if (!d || d->failed || !d->is_sse || d->line_len == 0) return (long long)strdup("");
    size_t emit = d->line_len;
    if (emit && d->line[emit-1] == '\r') emit--;
    char *out = (char*)malloc(emit + 2);
    if (!out) { d->failed = 1; return (long long)strdup(""); }
    memcpy(out, d->line, emit); out[emit] = '\n'; out[emit+1] = 0;
    d->line_len = 0;
    return (long long)out;
}

long long ep_sse_decoder_raw(long long decoder_ptr) {
    EpSseDecoder *d = (EpSseDecoder*)decoder_ptr;
    return (long long)strdup((d && d->raw) ? d->raw : "");
}

long long ep_sse_decoder_destroy(long long decoder_ptr) {
    EpSseDecoder *d = (EpSseDecoder*)decoder_ptr;
    if (!d) return 0;
    free(d->raw); free(d->line); free(d);
    return 0;
}
