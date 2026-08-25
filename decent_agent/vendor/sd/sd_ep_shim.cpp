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
#include <time.h>

#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "stb_image_write.h"

static pthread_mutex_t g_sd_mutex = PTHREAD_MUTEX_INITIALIZER;
static sd_ctx_t* g_sd_ctx = NULL;
static char g_sd_model[2048] = "";

static double sd_ep_now_ms(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec * 1000.0 + (double)ts.tv_nsec / 1000000.0;
}

typedef struct {
    double started_ms;
    double first_step_ms;
    double last_step_ms;
    int last_step;
    int total_steps;
    int expected_steps;
} sd_ep_progress_state_t;

static void sd_ep_progress(int step, int steps, float time, void* data) {
    sd_ep_progress_state_t* state = (sd_ep_progress_state_t*)data;
    if (!state) return;
    /* The library also reports lazy weight-upload progress through this callback.
     * Only sampler progress has the configured diffusion-step denominator. */
    if (steps != state->expected_steps) return;
    double now = sd_ep_now_ms();
    if (state->first_step_ms == 0.0) state->first_step_ms = now;
    double step_ms = state->last_step_ms > 0.0 ? now - state->last_step_ms : now - state->started_ms;
    state->last_step_ms = now;
    state->last_step = step;
    state->total_steps = steps;
    fprintf(stderr, "[ImageGen timing] denoise step=%d/%d callback_ms=%.1f library_s=%.3f\n",
            step, steps, step_ms, (double)time);
}

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
    /* Exact Metal execution accelerators only: these change kernels/load strategy,
     * never dimensions, diffusion steps, sampler, cache approximation, or weights.
     * Live 1024px isolation found mmap crashes this dylib and both direct-convolution
     * modes are neutral/slower, so those remain off; eager upload + attention won. */
    cp.enable_mmap = false;
    cp.flash_attn = true;
    cp.diffusion_flash_attn = true;
    cp.diffusion_conv_direct = false;
    cp.vae_conv_direct = false;
    cp.eager_load = true;
    double load_started_ms = sd_ep_now_ms();
    g_sd_ctx = new_sd_ctx(&cp);
    double load_ms = sd_ep_now_ms() - load_started_ms;
    if (g_sd_ctx != NULL) {
        strncpy(g_sd_model, key, sizeof(g_sd_model) - 1);
        g_sd_model[sizeof(g_sd_model) - 1] = '\0';
        fprintf(stderr, "[ImageGen shim] ctx loaded OK in %.1f ms (mmap=0 eager=1 flash=1 diffusion_flash=1 diffusion_conv_direct=0 vae_conv_direct=0)\n", load_ms);
    } else {
        fprintf(stderr, "[ImageGen shim] new_sd_ctx FAILED (rc 3 path) — check the weight file paths above\n");
    }
    return g_sd_ctx;
}

/* Load and retain the configured model without running diffusion. The node invokes
 * this once on a background worker after startup, so the first user render does not
 * pay model parsing, Metal allocation, and eager parameter upload. */
extern "C" long long sd_ep_preload(long long model_path_ll,
                    long long diffusion_model_ll,
                    long long clip_l_ll,
                    long long t5xxl_ll,
                    long long vae_ll) {
    const char* model_path       = (const char*)model_path_ll;
    const char* diffusion_model = (const char*)diffusion_model_ll;
    const char* clip_l           = (const char*)clip_l_ll;
    const char* t5xxl            = (const char*)t5xxl_ll;
    const char* vae              = (const char*)vae_ll;
    pthread_mutex_lock(&g_sd_mutex);
    sd_ctx_t* ctx = sd_ep_ctx_for(model_path, diffusion_model, clip_l, t5xxl, vae);
    pthread_mutex_unlock(&g_sd_mutex);
    return ctx != NULL ? 0 : 3;
}

/* Flat entry point EP calls over FFI. extern "C" keeps the symbol unmangled — this file
 * compiles as C++ (sd.cpp's stb_image_write.h uses C++ default args), but EP links the
 * plain C name `sd_ep_generate`.
 *
 * ABI: ALL parameters are long long — this MUST match the all-long-long prototype the
 * ErnosPlain compiler emits for `external define` (node_compiled.c). The previous mixed
 * int/int64 signature corrupted every STACK-passed argument (args 9+; Apple ARM64 packs
 * stack args at natural size, so the callee read 4-byte slots against the caller's
 * 8-byte writes): steps arrived as 0, cfg as the steps value, seed as the cfg value,
 * and out_png_path as the SEED reinterpreted as a pointer -> stbi_write_png failed ->
 * the live 'shim code 5' with 'generating ... steps=0 cfg=28 seed=1' in the log.
 * Pointers/ints are cast from the long longs inside. */
extern "C" long long sd_ep_generate(long long model_path_ll,
                   long long diffusion_model_ll,  /* Flux: transformer gguf ("" = single-file mode) */
                   long long clip_l_ll,           /* Flux: CLIP-L path ("" if unused) */
                   long long t5xxl_ll,            /* Flux: T5-XXL path ("" if unused) */
                   long long vae_ll,              /* Flux: VAE path ("" if unused) */
                   long long prompt_ll,
                   long long negative_ll,
                   long long width_ll,
                   long long height_ll,
                   long long steps_ll,
                   long long cfg_ll,        /* integer CFG scale (EP FFI passes ints/pointers, not doubles) */
                   long long seed,
                   long long out_png_path_ll) {
    const char* model_path      = (const char*)model_path_ll;
    const char* diffusion_model = (const char*)diffusion_model_ll;
    const char* clip_l          = (const char*)clip_l_ll;
    const char* t5xxl           = (const char*)t5xxl_ll;
    const char* vae             = (const char*)vae_ll;
    const char* prompt          = (const char*)prompt_ll;
    const char* negative        = (const char*)negative_ll;
    const char* out_png_path    = (const char*)out_png_path_ll;
    int width  = (int)width_ll;
    int height = (int)height_ll;
    int steps  = (int)steps_ll;
    int cfg    = (int)cfg_ll;
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
    sd_ep_progress_state_t progress;
    memset(&progress, 0, sizeof(progress));
    progress.started_ms = sd_ep_now_ms();
    progress.expected_steps = steps;
    sd_set_progress_callback(sd_ep_progress, &progress);
    bool ok = generate_image(ctx, &gp, &images, &num_images);
    double generated_ms = sd_ep_now_ms();
    sd_set_progress_callback(NULL, NULL);
    fprintf(stderr,
            "[ImageGen timing] conditioning_to_first_step_ms=%.1f denoise_callback_span_ms=%.1f post_denoise_ms=%.1f generate_total_ms=%.1f callbacks=%d/%d\n",
            progress.first_step_ms > 0.0 ? progress.first_step_ms - progress.started_ms : -1.0,
            progress.first_step_ms > 0.0 && progress.last_step_ms > 0.0 ? progress.last_step_ms - progress.first_step_ms : -1.0,
            progress.last_step_ms > 0.0 ? generated_ms - progress.last_step_ms : -1.0,
            generated_ms - progress.started_ms,
            progress.last_step, progress.total_steps);

    int rc = 0;
    if (!ok || num_images < 1 || images == NULL || images[0].data == NULL) {
        fprintf(stderr, "[ImageGen shim] generate_image FAILED (ok=%d n=%d) — rc 4\n", (int)ok, num_images);
        rc = 4;  /* generation produced no image */
    } else {
        int stride = (int)(images[0].width * images[0].channel);
        double png_started_ms = sd_ep_now_ms();
        int wrote = stbi_write_png(out_png_path,
                                   (int)images[0].width,
                                   (int)images[0].height,
                                   (int)images[0].channel,
                                   images[0].data,
                                   stride);
        fprintf(stderr, "[ImageGen timing] png_encode_write_ms=%.1f\n", sd_ep_now_ms() - png_started_ms);
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

extern "C" long long sd_ep_preload(long long model_path, long long diffusion_model,
                    long long clip_l, long long t5xxl, long long vae) {
    (void)model_path; (void)diffusion_model; (void)clip_l; (void)t5xxl; (void)vae;
    return 99;
}

extern "C" long long sd_ep_generate(long long model_path, long long diffusion_model,
                   long long clip_l, long long t5xxl, long long vae,
                   long long prompt, long long negative,
                   long long width, long long height, long long steps, long long cfg,
                   long long seed, long long out_png_path) {
    (void)model_path; (void)diffusion_model; (void)clip_l; (void)t5xxl; (void)vae;
    (void)prompt; (void)negative; (void)width; (void)height;
    (void)steps; (void)cfg; (void)seed; (void)out_png_path;
    return 99;  /* image runtime not built on this machine */
}

#endif
