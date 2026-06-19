# Ernos Programming Language — Reference Document

**Source**: [github.com/MettaMazza/Ernos-Programming-Language](https://github.com/MettaMazza/Ernos-Programming-Language)
**Author**: Maria Smith
**Version**: 1.0.0 — Rust-bootstrapped compiler with self-hosted compiler in Ernos (epc.ep), 36/36 tests passing
**Platform**: macOS, Linux
**Compiler backend**: Ernos → C → Clang native binary

> [!IMPORTANT]
> This is the standing reference for all agents and collaborators working on ErnosDecent. Read this before writing any `.ep` code.

---

## 1. What Ernos Is

A **compiled, statically-typed, memory-safe** language with plain English syntax. Compiles to C via `clang -O2`. No interpreter overhead — runs at C speed.

```ernos
define factorial with n as Int returning Int:
    if n < 2:
        return 1
    return n * factorial(n - 1)

define main:
    display factorial(20)
    return 0
```

---

## 2. Compiler Toolchain

| Command | What it does |
|---------|-------------|
| `ernos file.ep` | Compile to native binary |
| `ernos check file.ep` | Type/syntax check only (no compile) |
| `ernos test file.ep` | Run test suite |
| `ernos format file.ep` | Auto-format source |
| `ernos --repl` | Interactive REPL |
| `ernos --list-builtins` | Show built-in functions |
| `ernos file.ep --debug` | Compile with `-O0 -g` |
| `ernos file.ep --release` | Compile with `-O3 -flto` |

After building from source with `cargo build --release`, the compiler binary is at `target/release/ernos`. Add it to your `PATH`.

---

## 3. Core Syntax

### Variables
```ernos
set x to 42
set name to "Maria"
```

### Functions
```ernos
# Without types (inferred via Hindley-Milner)
define greet with name:
    display f"Hello, {name}!"
    return 0

# With explicit types
define add with a as Int and b as Int returning Int:
    return a + b
```

### Control Flow
```ernos
if x > 10:
    display "big"
else:
    display "small"

repeat while i < 100:
    set i to i + 1
```

### Structs
```ernos
define structure Point:
    field x as Int
    field y as Int
```

### Enums
```ernos
define choice Color:
    variant Red with value as Int
    variant Blue with value as Int
```

### Imports
```ernos
import "string"                           # stdlib module
import "collections"                       # stdlib module
import "../stdlib/bridge/libsodium"        # bridge library
import "mymodule"                          # local file (mymodule.ep in same dir)
```

### String Interpolation (F-strings)
```ernos
set name to "ErnosDecent"
display f"Building {name} today"

# LIMITATION: Cannot nest escaped quotes inside f-string expressions
# BAD:  f"value: {map_get(m and \"key\")}"
# GOOD: set val to map_get(m and "key")
#       display f"value: {val}"
```

### Comparison
```ernos
# Numeric comparison
if x == 42:
if x != 0:
if x > 10:
if x < 5:
if x >= 1:
if x <= 100:

# String comparison
if name equals "Maria":
if name equals other_name:
```

> [!WARNING]
> Use `==` for integer comparison and `equals` for string comparison. They are not interchangeable.

---

## 4. Type System

### Primitive Types
| Type | Description | C equivalent |
|------|-------------|-------------|
| `Int` | 64-bit signed integer | `long long` |
| `Str` | Immutable string (char pointer) | `char*` |
| `List` | Dynamic array of `long long` | `EpList*` |
| `Map` | Hash map (string keys) | `EpMap*` |
| `Channel` | Thread-safe message channel | `EpChannel*` |

### Hindley-Milner Type Inference
Types are inferred automatically. Explicit annotations are optional but recommended for clarity:
```ernos
define foo with x:           # x type inferred from usage
    return x + 1             # infers x: Int, returns Int

define bar with x as Int returning Int:  # explicit
    return x + 1
```

### Ownership & Move Semantics
- Strings are **NOT moved** on assignment (strings are immutable pointers)
- Lists and maps **ARE moved** on assignment — use with care
- Borrowed references cannot be sent to threads

```ernos
set a to "hello"
set b to a          # OK — strings copy the pointer
set c to a          # OK — no move

set list1 to create_list()
set list2 to list1  # list1 is MOVED — cannot use list1 after this
```

---

## 5. Built-in Functions

### Strings
| Function | Signature | Description |
|----------|-----------|-------------|
| `concat` | `(Str, Str) → Str` | Concatenate two strings |
| `string_length` | `(Str) → Int` | Length in characters |
| `substring` | `(Str, Int, Int) → Str` | Extract substring (start, length) |
| `int_to_string` | `(Int) → Str` | Number to string |
| `get_character` | `(Str, Int) → Int` | Char code at index |
| `string_contains` | `(Str, Str) → Int` | Contains substring (1/0) |
| `string_index_of` | `(Str, Str) → Int` | First index of substring (-1 if not found) |
| `string_replace` | `(Str, Str, Str) → Str` | Replace all occurrences |
| `string_from_list` | `(List) → Str` | Build string from char codes |
| `string_upper` | `(Str) → Str` | To uppercase |
| `string_lower` | `(Str) → Str` | To lowercase |
| `string_trim` | `(Str) → Str` | Strip whitespace |
| `string_split` | `(Str, Str) → List` | Split by delimiter |
| `char_at` | `(Str, Int) → Int` | Char code at index |
| `char_from_code` | `(Int) → Str` | Single-char string |

### Lists
| Function | Signature | Description |
|----------|-----------|-------------|
| `create_list` | `() → List` | Empty list |
| `append_list` | `(List, Int) → Int` | Append element |
| `get_list` | `(List, Int) → Int` | Get element at index |
| `set_list` | `(List, Int, Int) → Int` | Set element at index |
| `length_list` | `(List) → Int` | List length |
| `pop_list` | `(List) → Int` | Remove and return last |
| `free_list` | `(List) → Int` | Free list memory |

> [!NOTE]
> Lists store `long long` (8 bytes per element). They are **not** packed byte arrays. For byte buffers, use `alloc_bytes()`.

### Maps (from `import "collections"`)
| Function | Signature | Description |
|----------|-----------|-------------|
| `create_map` | `() → Map` | Empty hash map |
| `map_put` | `(Map, Str, Any) → Int` | Insert key-value |
| `map_get` | `(Map, Str) → Any` | Get value by key |
| `map_contains` | `(Map, Str) → Int` | Key exists (1/0) |
| `map_delete` | `(Map, Str) → Int` | Remove key |
| `map_keys` | `(Map) → List` | All keys |
| `map_size` | `(Map) → Int` | Entry count |

### File I/O
| Function | Signature | Description |
|----------|-----------|-------------|
| `file_read` | `(Str) → Str` | Read entire file |
| `file_write` | `(Str, Str) → Int` | Write to file |
| `file_append` | `(Str, Str) → Int` | Append to file |
| `file_exists` | `(Str) → Int` | Check existence |

### JSON (built-in flat extraction)
| Function | Signature | Description |
|----------|-----------|-------------|
| `json_get_string` | `(Str, Str) → Str` | Extract string field from JSON |
| `json_get_int` | `(Str, Str) → Int` | Extract int field |
| `json_get_bool` | `(Str, Str) → Int` | Extract bool field |

### Hashing
| Function | Signature | Description |
|----------|-----------|-------------|
| `ep_sha256` | `(Str) → Str` | SHA-256 hex digest |
| `ep_md5` | `(Str) → Str` | MD5 hex digest |
| `ep_sha1` | `(Str) → Str` | SHA-1 hex digest |

### Networking
| Function | Signature | Description |
|----------|-----------|-------------|
| `ep_net_connect` | `(Str, Int) → Int` | TCP connect → fd |
| `ep_net_listen` | `(Int) → Int` | TCP listen → fd |
| `ep_net_accept` | `(Int) → Int` | TCP accept → fd |
| `ep_net_send` | `(Int, Str) → Int` | Send data |
| `ep_net_recv` | `(Int, Int) → Str` | Receive data |
| `ep_net_close` | `(Int) → Int` | Close connection |
| `ep_http_request` | `(Str, Str, Str, Str) → Str` | HTTP request (method, url, headers, body) |

### Concurrency
| Function | Signature | Description |
|----------|-----------|-------------|
| `create_channel` | `() → Channel` | Message channel |
| `send X to CH` | statement | Send to channel |
| `receive from CH` | `→ Int` | Blocking receive |
| `spawn func(args)` | statement | Run in new thread |
| `ep_sleep_ms` | `(Int) → Int` | Sleep milliseconds |
| `channel_select` | `(List, Int) → Int` | Wait on multiple channels |
| `channel_has_data` | `(Channel) → Int` | Non-blocking check |

### Time
| Function | Signature | Description |
|----------|-----------|-------------|
| `ep_time_now_ms` | `() → Int` | Epoch milliseconds |
| `ep_time_now_sec` | `() → Int` | Epoch seconds |

### Math
| Function | Signature | Description |
|----------|-----------|-------------|
| `ep_random_int` | `(Int, Int) → Int` | Random in range |
| `ep_abs` | `(Int) → Int` | Absolute value |

---

## 6. FFI Interop Builtins

These builtins bridge EP's managed types and raw C memory for FFI calls:

| Function | Signature | Description |
|----------|-----------|-------------|
| `str_to_ptr` | `(Str) → Int` | Get raw `char*` pointer from EP string |
| `ptr_to_str` | `(Int) → Str` | Copy null-terminated C string into EP |
| `peek_byte` | `(Int, Int) → Int` | Read byte at `ptr + offset` |
| `poke_byte` | `(Int, Int, Int) → void` | Write byte at `ptr + offset` |
| `alloc_bytes` | `(Int) → Int` | Allocate zeroed byte buffer (returns pointer) |
| `free_bytes` | `(Int) → Int` | Free byte buffer |
| `list_to_bytes` | `(List) → Int` | Pack list of ints into contiguous byte buffer |
| `bytes_to_list` | `(Int, Int) → List` | Unpack byte buffer into list |

> [!IMPORTANT]
> Always use `alloc_bytes`/`free_bytes` for C FFI byte buffers. EP lists store 8 bytes per element — they are NOT compatible with C byte arrays.

---

## 7. FFI — Dynamic Library Loading

```ernos
external define ep_dlopen with lib:        # Open shared library → handle
external define ep_dlsym with handle and name:  # Get function pointer → fn_ptr
external define ep_dlcall0 with fn:        # Call with 0 args
external define ep_dlcall1 with fn and a0: # Call with 1 arg
# ... up to ep_dlcall10
```

All `ep_dlcall` arguments and return values are `long long`. This means:
- `Int` passes directly
- `Str` (which is `char*`) passes as the pointer value
- Raw pointers from `alloc_bytes` pass as `Int`

---

## 8. Standard Library Modules (23)

| Module | Import | Key Functions |
|--------|--------|---------------|
| `string` | `import "string"` | String manipulation, parsing, formatting |
| `collections` | `import "collections"` | HashMap (`map_put`/`map_get`), HashSet, Stack, Queue |
| `fs` | `import "fs"` | File I/O, directories, paths |
| `json` | `import "json"` | JSON parsing and generation (node-based) |
| `csv` | `import "csv"` | CSV parsing and generation |
| `net` | `import "net"` | TCP sockets |
| `http` | `import "http"` | HTTP client/server |
| `crypto` | `import "crypto"` | SHA256, byte_to_hex, hmac_sha256 |
| `regex` | `import "regex"` | POSIX regex match, find, replace, split |
| `sync` | `import "sync"` | Mutex, RWLock, Atomic, Barrier, Semaphore |
| `os` | `import "os"` | Environment, process, system commands |
| `test` | `import "test"` | assert_equal, assert_true, test suites |
| `log` | `import "log"` | Structured logging with levels |
| `math` | `import "math"` | Mathematical functions |
| `sort` | `import "sort"` | Sorting algorithms |
| `datetime` | `import "datetime"` | Timestamps, formatting |
| `sql` | `import "sql"` | SQLite bindings |
| `gui` | `import "gui"` | Raylib GUI |
| `toml` | `import "toml"` | TOML config parsing |
| `websocket` | `import "websocket"` | WebSocket protocol |
| `static_server` | `import "static_server"` | Static file HTTP serving |
| `select` | `import "select"` | I/O multiplexing |
| `hash` | `import "hash"` | Hashing utilities |

---

## 9. FFI Bridge Libraries (29)

Pre-built C library bindings via `ep_dlopen`/`ep_dlsym`/`ep_dlcall`:

| Bridge | Import Path | Library |
|--------|-------------|---------|
| libsodium | `import "../stdlib/bridge/libsodium"` | Modern crypto |
| openssl | `import "../stdlib/bridge/openssl"` | TLS/crypto |
| curl | `import "../stdlib/bridge/curl"` | HTTP client |
| sqlite | `import "../stdlib/bridge/sqlite"` | Database |
| raylib | `import "../stdlib/bridge/raylib"` | Game/GUI framework |
| sdl2 | `import "../stdlib/bridge/sdl2"` | Multimedia |
| ncurses | `import "../stdlib/bridge/ncurses"` | Terminal UI |
| cairo | `import "../stdlib/bridge/cairo"` | 2D graphics |
| libpng | `import "../stdlib/bridge/libpng"` | PNG images |
| stb_image | `import "../stdlib/bridge/stb_image"` | Image loading |
| stb_truetype | `import "../stdlib/bridge/stb_truetype"` | Font rendering |
| miniaudio | `import "../stdlib/bridge/miniaudio"` | Audio |
| libsndfile | `import "../stdlib/bridge/libsndfile"` | Sound files |
| portmidi | `import "../stdlib/bridge/portmidi"` | MIDI I/O |
| zlib | `import "../stdlib/bridge/zlib"` | Compression |
| jansson | `import "../stdlib/bridge/jansson"` | JSON (C) |
| expat | `import "../stdlib/bridge/expat"` | XML parsing |
| pcre | `import "../stdlib/bridge/pcre"` | Regex (C) |
| libgit2 | `import "../stdlib/bridge/libgit2"` | Git operations |
| libuv | `import "../stdlib/bridge/libuv"` | Async I/O |
| lmdb | `import "../stdlib/bridge/lmdb"` | Key-value store |
| chipmunk | `import "../stdlib/bridge/chipmunk"` | 2D physics engine |
| freetype | `import "../stdlib/bridge/freetype"` | Font loading |
| libnotify | `import "../stdlib/bridge/libnotify"` | Desktop notifications |
| libusb | `import "../stdlib/bridge/libusb"` | USB device access |
| lua | `import "../stdlib/bridge/lua"` | Lua scripting |
| mongoose | `import "../stdlib/bridge/mongoose"` | Embedded web server |
| mosquitto | `import "../stdlib/bridge/mosquitto"` | MQTT messaging |
| termbox2 | `import "../stdlib/bridge/termbox2"` | Terminal UI (alt) |

### Libsodium Bridge — Key Constants
```ernos
import "../stdlib/bridge/libsodium"

# Available constants:
# crypto_secretbox_KEYBYTES    = 32
# crypto_secretbox_NONCEBYTES  = 24
# crypto_secretbox_MACBYTES    = 16
# crypto_box_PUBLICKEYBYTES    = 32
# crypto_box_SECRETKEYBYTES    = 32
# crypto_box_NONCEBYTES        = 24
# crypto_box_MACBYTES          = 16
# crypto_sign_PUBLICKEYBYTES   = 32
# crypto_sign_SECRETKEYBYTES   = 64
# crypto_sign_BYTES            = 64
# crypto_generichash_BYTES     = 32
# crypto_pwhash_SALTBYTES      = 16
# crypto_pwhash_STRBYTES       = 128
```

---

## 10. Import Resolution

The compiler resolves imports as follows:
1. **Stdlib modules**: Checks `stdlib/` directory relative to CWD, then relative to the compiler binary
2. **Local modules**: Checks relative to the importing file's directory
3. **Path imports**: `import "../path/to/module"` resolves relative to the importing file

For ErnosDecent, stdlib is symlinked: `ErnosDecent/stdlib` → `Ernos-Programming-Language/stdlib`

---

## 11. Memory Model

- **Strings**: Immutable `char*` pointers. Managed by the runtime. Can be freely assigned to multiple variables.
- **Lists**: Heap-allocated `EpList*` with `long long*` data array (8 bytes per element). Subject to ownership/move rules.
- **Maps**: Heap-allocated `EpMap*`. Subject to ownership/move rules.
- **Byte buffers** (`alloc_bytes`): Raw C heap `calloc`'d memory. Must be manually freed with `free_bytes`. Used exclusively for FFI interop.

---

## 12. Known Constraints & Issue Protocol

Ernos is purpose-built and actively developed. The following constraints have been identified during ErnosDecent development:

- **F-string nesting**: Nested double quotes inside f-string interpolation expressions trigger lexer errors. Break complex expressions into variables before interpolation.
- **Channel receive syntax**: The compiler requires `set <name> to receive from <channel>` — bare `receive` statements are invalid.
- **List/Map reassignment**: Reassigning list or map variables inside loops can trigger premature deallocation due to codegen-generated `free_list`/`free_map` calls.
- **Large integer comparisons**: Values ≥ 4096 in comparisons may trigger incorrect `strcmp` generation — use composite range boundaries (`<=` and `>=`).

If during development a new language-level issue is discovered (type system gap, missing builtin, codegen bug, borrow checker false positive, FFI interop problem), the standing protocol is:

1. **Stop work immediately.** Do not write workaround code.
2. **Report the issue** with a clear description: what you tried, what failed, what the compiler said, and what capability is missing.
3. **The compiler, runtime, or stdlib is updated.**
4. **Resume work** using the clean, fixed language.

---

## 13. Testing

```ernos
import "test"

# The stdlib test.ep provides:
# - assert_equal(actual, expected, message)
# - assert_true(condition, message)
# - create_test_suite(name)
```

Run tests: `ernos test file.ep` or compile and run directly: `ernos file.ep && ./file`

---

*Maria Smith. Scotland. May 2026.*
*Standing reference for the ErnosDecent project.*
