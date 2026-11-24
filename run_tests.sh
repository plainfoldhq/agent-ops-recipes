#!/usr/bin/env bash
# Run every recipe's offline tests. Exit 1 if any fail.
set -u
cd "$(dirname "$0")"
fail=0
for d in */; do
  [ -d "$d" ] || continue
  ls "$d"test_*.py >/dev/null 2>&1 || continue
  echo "== $d"
  (cd "$d" && python3 -B -m unittest discover -p 'test_*.py' -q) || fail=1
done
[ $fail -eq 0 ] && echo "all recipe tests passed" || echo "SOME TESTS FAILED"
exit $fail
