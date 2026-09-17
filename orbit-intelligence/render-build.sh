#!/usr/bin/env bash

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "========================================"
echo " Orbit Intelligence — Find_Orb Build"
echo " Project root: $PROJECT_ROOT"
echo "========================================"

export CPPFLAGS="-I$HOME/include"
export CFLAGS="-I$HOME/include"
export CXXFLAGS="-I$HOME/include"
export LDFLAGS="-L$HOME/lib"

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

echo "=== Building Find_Orb ==="

cd /tmp/find_orb
make clean
make

echo "=== Installing Find_Orb ==="

mkdir -p "$PROJECT_ROOT/backend/bin"
mkdir -p "$PROJECT_ROOT/backend/findorb-data"

echo "=== Installing Find_Orb executable and data files ==="

make PREFIX="$PROJECT_ROOT/backend" install

echo "=== Copying Find_Orb configuration data ==="

if [ ! -d "$PROJECT_ROOT/backend/share/findorb/data" ]; then
    echo "ERROR: Find_Orb data directory was not created."
    exit 1
fi

cp -a \
    "$PROJECT_ROOT/backend/share/findorb/data/." \
    "$PROJECT_ROOT/backend/findorb-data/"

echo "=== Installing DE430 planetary ephemeris ==="

wget -O \
    "$PROJECT_ROOT/backend/findorb-data/linux_p1550p2650.430t" \
    ftp://ssd.jpl.nasa.gov/pub/eph/planets/Linux/de430t/linux_p1550p2650.430t

echo "=== Verifying Find_Orb runtime files ==="

if [ ! -f "$PROJECT_ROOT/backend/bin/fo" ]; then
    echo "ERROR: Find_Orb executable was not installed."
    exit 1
fi

if [ ! -x "$PROJECT_ROOT/backend/bin/fo" ]; then
    chmod +x "$PROJECT_ROOT/backend/bin/fo"
fi

if [ ! -f "$PROJECT_ROOT/backend/findorb-data/cospar.txt" ]; then
    echo "ERROR: cospar.txt was not installed."
    echo "Find_Orb configuration is incomplete."
    exit 1
fi

echo "Find_Orb executable:"
ls -lh "$PROJECT_ROOT/backend/bin/fo"

echo "Find_Orb configuration:"
echo "$PROJECT_ROOT/backend/findorb-data"

echo "Checking cospar.txt:"
ls -lh "$PROJECT_ROOT/backend/findorb-data/cospar.txt"

echo "========================================"
echo " Find_Orb successfully installed!"
echo " Executable:"
echo " $PROJECT_ROOT/backend/bin/fo"
echo ""
echo " Configuration:"
echo " $PROJECT_ROOT/backend/findorb-data"
echo "========================================"

echo "=== Find_Orb configuration files ==="

ls -lh "$PROJECT_ROOT/backend/findorb-data" | head -40

echo "=== Build complete ==="
