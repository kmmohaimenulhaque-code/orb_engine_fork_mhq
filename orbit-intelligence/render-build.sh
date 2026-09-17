#!/usr/bin/env bash

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "========================================"
echo " Orbit Intelligence — Find_Orb Build"
echo " Project root: $PROJECT_ROOT"
echo "========================================"

cd /tmp

rm -rf lunar jpl_eph sat_code miscell find_orb

echo "=== Cloning Find_Orb dependencies ==="

git clone --depth 1 https://github.com/Bill-Gray/lunar.git
git clone --depth 1 https://github.com/Bill-Gray/jpl_eph.git
git clone --depth 1 https://github.com/Bill-Gray/sat_code.git
git clone --depth 1 https://github.com/Bill-Gray/miscell.git
git clone --depth 1 https://github.com/Bill-Gray/find_orb.git

echo "=== Building lunar ==="

cd /tmp/lunar
make clean
make
make install

echo "=== Building jpl_eph ==="

cd /tmp/jpl_eph
make clean
make libjpl.a
make install

echo "=== Building lunar integration tools ==="

cd /tmp/lunar
make integrat

echo "=== Building sat_code ==="

cd /tmp/sat_code
make clean
make sat_id
make install

echo "=== Building find_orb ==="

cd /tmp/find_orb
make clean
make

echo "=== Installing Find_Orb executable ==="

mkdir -p "$PROJECT_ROOT/backend/bin"

cp /tmp/find_orb/fo "$PROJECT_ROOT/backend/bin/fo"

chmod +x "$PROJECT_ROOT/backend/bin/fo"

echo "========================================"
echo " Find_Orb successfully built!"
echo " Installed at:"
echo " $PROJECT_ROOT/backend/bin/fo"
echo "========================================"

"$PROJECT_ROOT/backend/bin/fo" || true
