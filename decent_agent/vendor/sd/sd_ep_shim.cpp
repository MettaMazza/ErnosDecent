/* sd_ep_shim.c — thin C FFI shim over libstable-diffusion (ggml/Metal).
 *
 * ErnosDecent generates images in ErnosPlain: image_gen.ep declares sd_ep_generate
 * via `external define` and calls it. This shim is the FFI boundary only — it builds
 * the (large, version-specific) sd.cpp param structs with sane defaults, runs the
 * ggml Metal pipeline on the model weights, PNG-encodes the first image, and writes it
 * to disk. All orchestration (prompts, sizing, workspace paths, attachment) lives in
 * .ep. No Python; the model runtime is a linked C library, exactly like libsodium/sqlite.
 *
 * Returns 0 on success, non-zero on failure. The sd_ctx is cached by model path so
 * repeated generations in a session don't reload multi-GB weights; a mutex serialises
 * generation (it is heavy and the underlying ctx is not concurrent-safe).
 */
/* build.sh defines SD_EP_HAVE_LIB and links libstable-diffusion when the dylib is present
 * (~/.ernosdecent/lib). When it is absent (e.g. a machine that hasn't built it), this file
 * still compiles as a stub so the node/test builds never break — generate_image just
 * reports the model runtime is unavailable. */
#ifdef SD_EP_HAVE_LIB

#include "stable-diffusion.h"
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <pthread.h>

#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "stb_image_write.h"

static pthread_mutex_t g_sd_mutex = PTHREAD_MUTEX_INITIALIZER;
static sd_ctx_t* g_sd_ctx = NULL;
static char g_sd_model[2048] = "";

/* Load (or reuse a cached) context. Two modes:
 *  - single-file (SD1.5/SDXL): model_path set, encoders empty — CLIP+VAE are built in.
 *  - Flux: diffusion_model set + clip_l + t5xxl + vae as separate files (Maria's diffusers
 *    CLIP/VAE load directly; the T5 is one merged file). Cache key = the primary path.
 * Caller holds g_sd_mutex. Empty ("") strings mean "unset". */
static sd_ctx_t* sd_ep_ctx_for(const char* model_path, const char* diffusion_model,
                               const char* clip_l, const char* t5xxl, const char* vae) {
    int flux = (diffusion_model && diffusion_model[0]);
    const char* key = flux ? diffusion_model : model_path;
    if (g_sd_ctx != NULL && strncmp(g_sd_model, key, sizeof(g_sd_model) - 1) == 0) {
        fprintf(stderr, "[ImageGen shim] ctx cache HIT (%s)\n", key);
        return g_sd_ctx;
    }
    fprintf(stderr, "[ImageGen shim] ctx cache MISS — loading %s weights (%s)\n",
            flux ? "flux" : "single-file", key);
    /* Model switch: deliberately DO NOT free_sd_ctx here. The ggml-metal backend aborts in
     * ggml_metal_device_free (GGML_ASSERT rsets->data count == 0) on teardown — freeing mid-run
     * would crash the whole node. Switching models is rare, so we leak the old ctx instead of
     * crashing (correctness over a bit of memory). The default single-model path never hits this. */
    if (g_sd_ctx != NULL) {
        g_sd_ctx = NULL;
        g_sd_model[0] = '\0';
    }
    sd_ctx_params_t cp;
    sd_ctx_params_init(&cp);
    if (flux) {
        cp.diffusion_model_path = diffusion_model;
        if (clip_l && clip_l[0]) cp.clip_l_path = clip_l;
        if (t5xxl && t5xxl[0])   cp.t5xxl_path = t5xxl;
        if (vae && vae[0])       cp.vae_path = vae;
    } else {
        cp.model_path = model_path;   /* single-file checkpoint (SD1.5/SDXL): CLIP+VAE built in */
    }
    g_sd_ctx = new_sd_ctx(&cp);
    if (g_sd_ctx != NULL) {
        strncpy(g_sd_model, key, sizeof(g_sd_model) - 1);
        g_sd_model[sizeof(g_sd_model) - 1] = '\0';
        fprintf(stderr, "[ImageGen shim] ctx loaded OK\n");
    } else {
        fprintf(stderr, "[ImageGen shim] new_sd_ctx FAILED (rc 3 path) — check the weight file paths above\n");
    }
    return g_sd_ctx;
}

/* Flat entry point EP calls over FFI. extern "C" keeps the symbol unmangled — this file
 * compiles as C++ (sd.cpp's stb_image_write.h uses C++ default args), but EP links the
 * plain C name `sd_ep_generate`. */
extern "C" int sd_ep_generate(const char* model_path,
                   const char* diffusion_model,  /* Flux: transformer gguf ("" = single-file mode) */
                   const char* clip_l,           /* Flux: CLIP-L path ("" if unused) */
                   const char* t5xxl,            /* Flux: T5-XXL path ("" if unused) */
                   const char* vae,              /* Flux: VAE path ("" if unused) */
                   const char* prompt,
                   const char* negative,
                   int width,
                   int height,
                   int steps,
                   int cfg,        /* integer CFG scale (EP FFI passes ints/pointers, not doubles) */
                   long long seed,
                   const char* out_png_path) {
    if (!model_path || !prompt || !out_png_path) return 2;
    pthread_mutex_lock(&g_sd_mutex);

    sd_ctx_t* ctx = sd_ep_ctx_for(model_path, diffusion_model, clip_l, t5xxl, vae);
    if (ctx == NULL) {
        pthread_mutex_unlock(&g_sd_mutex);
        return 3;  /* model failed to load */
    }

    sd_img_gen_params_t gp;
    sd_img_gen_params_init(&gp);
    gp.prompt = prompt;
    gp.negative_prompt = (negative && negative[0]) ? negative : "";
    gp.width = width;
    gp.height = height;
    gp.sample_params.sample_steps = steps;
    gp.sample_params.guidance.txt_cfg = (float)cfg;
    gp.seed = (int64_t)seed;
    gp.batch_count = 1;

    sd_image_t* images = NULL;
    int num_images = 0;
    fprintf(stderr, "[ImageGen shim] generating %dx%d steps=%d cfg=%d seed=%lld\n",
            width, height, steps, cfg, (long long)seed);
    bool ok = generate_image(ctx, &gp, &images, &num_images);

    int rc = 0;
    if (!ok || num_images < 1 || images == NULL || images[0].data == NULL) {
        fprintf(stderr, "[ImageGen shim] generate_image FAILED (ok=%d n=%d) — rc 4\n", (int)ok, num_images);
        rc = 4;  /* generation produced no image */
    } else {
        int stride = (int)(images[0].width * images[0].channel);
        int wrote = stbi_write_png(out_png_path,
                                   (int)images[0].width,
                                   (int)images[0].height,
                                   (int)images[0].channel,
                                   images[0].data,
                                   stride);
        rc = wrote ? 0 : 5;  /* PNG write failed */
    }

    if (images != NULL) {
        for (int i = 0; i < num_images; i++) {
            if (images[i].data) free(images[i].data);
        }
        free(images);
    }
    /* ctx is cached — not freed here. */
    pthread_mutex_unlock(&g_sd_mutex);
    return rc;
}

#else  /* !SD_EP_HAVE_LIB — stub so the build always links */

extern "C" int sd_ep_generate(const char* model_path, const char* diffusion_model,
                   const char* clip_l, const char* t5xxl, const char* vae,
                   const char* prompt, const char* negative,
                   int width, int height, int steps, int cfg, long long seed,
                   const char* out_png_path) {
    (void)model_path; (void)diffusion_model; (void)clip_l; (void)t5xxl; (void)vae;
    (void)prompt; (void)negative; (void)width; (void)height;
    (void)steps; (void)cfg; (void)seed; (void)out_png_path;
    return 99;  /* image runtime not built on this machine */
}

#endif
