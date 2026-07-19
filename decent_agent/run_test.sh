#!/usr/bin/env bash
# Build + run an ErnosPlain agent test that transitively imports subsystems needing
# the runtime helpers build.sh injects (cast_borrow_to_map / cast_map_to_int /
# ep_net_send_raw). Raw `ernos test.ep` fails at link without them; this replicates
# build.sh's test path generically.
#
# Usage: bash decent_agent/run_test.sh decent_agent/test_foo.ep
set -euo pipefail
TEST="${1:?usage: run_test.sh <path/to/test.ep>}"
T="${TEST%.ep}"
ERNOS="$HOME/.local/bin/ernos"; command -v ernos >/dev/null 2>&1 && ERNOS=ernos

# 1. Prove the source type-checks, then transpile. Some agent tests need the helpers
# below before they can link, so the compiler's initial link failure is printed and
# accepted only when it emitted the expected C translation unit.
"$ERNOS" --check "${T}.ep"
set +e
TRANSPILE_OUTPUT=$("$ERNOS" "${T}.ep" 2>&1)
TRANSPILE_STATUS=$?
set -e
if [ ! -f "${T}_compiled.c" ]; then
  echo "$TRANSPILE_OUTPUT"
  echo "[-] compiler emitted no C translation unit (status $TRANSPILE_STATUS)"
  exit 1
fi
if [ "$TRANSPILE_STATUS" -ne 0 ]; then
  echo "[*] Initial link stopped before helper injection, as required by this test harness."
fi

# 2. Inject the runtime helpers (same definitions build.sh uses).
python3 - "$T" <<'PY'
import sys
f = sys.argv[1] + "_compiled.c"
c = open(f).read()
c = c.replace('long long ep_mutex_lock(long long);', '').replace('long long ep_mutex_unlock(long long);', '')
inj = '''
long long cast_borrow_to_map(long long b){return b;}
long long cast_map_to_int(long long m){return m;}
long long ep_net_send_raw(long long fd,long long buf,long long count){if(count<=0||buf==0)return 0;const char*p=(const char*)buf;long long t=0;while(t<count){ssize_t n=send((int)fd,p+t,(size_t)(count-t),0);if(n<=0)break;t+=n;}return t;}
'''
pat = 'long long ep_net_send(long long fd, const char* data) {'
first = c.find(pat); second = c.find(pat, first + 1)
if second > 0:   c = c[:second] + inj + c[second:]
elif first > 0:  c = c[:first] + inj + c[first:]
else:            c = inj + c
open(f, 'w').write(c)
PY

# 3. Link with the same flags build.sh uses (macOS Homebrew / Linux).
CFLAGS_COMMON="-O2 -lpthread -DEP_HAS_SQLITE -lsqlite3 -Wno-int-conversion -Wno-parentheses-equality"
case "$(uname -s)" in
  Darwin)
    if [ -d /opt/homebrew/lib ]; then
      clang "${T}_compiled.c" -o "./${T}" $CFLAGS_COMMON -L/opt/homebrew/lib -lsodium -L/opt/homebrew/opt/openssl/lib -lcrypto
    else
      clang "${T}_compiled.c" -o "./${T}" $CFLAGS_COMMON -L/usr/local/lib -lsodium -L/usr/local/opt/openssl/lib -lcrypto
    fi
    codesign --force -s - "./${T}"
    ;;
  *)
    clang "${T}_compiled.c" -o "./${T}" $CFLAGS_COMMON -lsodium -lcrypto -lm
    ;;
esac

# 4. Run, preserve its status, then clean up only artifacts created above.
echo "=== $(basename "$T") ==="
set +e
"./${T}"
TEST_STATUS=$?
set -e
rm -f "${T}_compiled.c" "./${T}"
exit "$TEST_STATUS"
