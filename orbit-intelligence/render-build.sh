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

echo "=== Find_Orb executable built successfully ==="

echo "=== Preparing runtime directories ==="

mkdir -p "$PROJECT_ROOT/backend/bin"
mkdir -p "$PROJECT_ROOT/backend/findorb-data"

echo "=== Installing Find_Orb executable ==="

cp /tmp/find_orb/fo \
   "$PROJECT_ROOT/backend/bin/fo"

chmod +x \
   "$PROJECT_ROOT/backend/bin/fo"

echo "=== Locating Find_Orb runtime files ==="

copy_runtime_file() {
    local filename="$1"

    if [ -f "/tmp/find_orb/$filename" ]; then
        echo "Copying $filename"
        cp "/tmp/find_orb/$filename" \
           "$PROJECT_ROOT/backend/findorb-data/$filename"
        return 0
    fi

    local found
    found="$(find /tmp/find_orb \
        -type f \
        -name "$filename" \
        -print -quit)"

    if [ -n "$found" ]; then
        echo "Copying $filename from $found"
        cp "$found" \
           "$PROJECT_ROOT/backend/findorb-data/$filename"
        return 0
    fi

    echo "WARNING: $filename was not found"
    return 1
}

echo "=== Required configuration ==="

copy_runtime_file "environ.def"
copy_runtime_file "cospar.txt"

echo "=== Observatory data ==="

copy_runtime_file "ObsCodes.html" || \
copy_runtime_file "ObsCodes.htm"

copy_runtime_file "rovers.txt"

echo "=== Additional Find_Orb configuration ==="

copy_runtime_file "command.txt" || true
copy_runtime_file "eph_type.txt" || true
copy_runtime_file "fo_options.txt" || true

echo "=== Installing DE430 planetary ephemeris ==="

wget -O \
    "$PROJECT_ROOT/backend/findorb-data/linux_p1550p2650.430t" \
    ftp://ssd.jpl.nasa.gov/pub/eph/planets/Linux/de430t/linux_p1550p2650.430t

echo "=== Verifying Find_Orb installation ==="

if [ ! -f "$PROJECT_ROOT/backend/bin/fo" ]; then
    echo "ERROR: Find_Orb executable was not created."
    exit 1
fi

if [ ! -x "$PROJECT_ROOT/backend/bin/fo" ]; then
    chmod +x "$PROJECT_ROOT/backend/bin/fo"
fi

if [ ! -f "$PROJECT_ROOT/backend/findorb-data/environ.def" ]; then
    echo "ERROR: environ.def is missing."
    exit 1
fi

if [ ! -f "$PROJECT_ROOT/backend/findorb-data/cospar.txt" ]; then
    echo "ERROR: cospar.txt is missing."
    exit 1
fi

if [ ! -f "$PROJECT_ROOT/backend/findorb-data/linux_p1550p2650.430t" ]; then
    echo "ERROR: DE430 ephemeris is missing."
    exit 1
fi

echo ""
echo "========================================"
echo " Find_Orb installation complete!"
echo "========================================"

echo ""
echo "Executable:"
ls -lh \
    "$PROJECT_ROOT/backend/bin/fo"

echo ""
echo "Runtime configuration:"
ls -lh \
    "$PROJECT_ROOT/backend/findorb-data"

echo ""
echo "Environment:"
ls -lh \
    "$PROJECT_ROOT/backend/findorb-data/environ.def"

echo ""
echo "COSPAR:"
ls -lh \
    "$PROJECT_ROOT/backend/findorb-data/cospar.txt"

echo ""
echo "DE430:"
ls -lh \
    "$PROJECT_ROOT/backend/findorb-data/linux_p1550p2650.430t"

echo ""
echo "========================================"
echo " Build completed successfully!"
echo "========================================"
