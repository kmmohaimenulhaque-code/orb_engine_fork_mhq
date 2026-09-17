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

echo "=== Preparing application runtime directories ==="

mkdir -p "$PROJECT_ROOT/backend/bin"
mkdir -p "$PROJECT_ROOT/backend/findorb-data"

echo "=== Copying Find_Orb executable ==="

cp /tmp/find_orb/fo \
   "$PROJECT_ROOT/backend/bin/fo"

chmod +x \
   "$PROJECT_ROOT/backend/bin/fo"

echo "=== Copying Find_Orb runtime configuration ==="

if [ -d "/tmp/find_orb" ]; then

    echo "Searching Find_Orb source tree for runtime data..."

    find /tmp/find_orb \
        -maxdepth 2 \
        -type f \
        \( \
            -name "cospar.txt" \
            -o -name "command.txt" \
            -o -name "eph_type.txt" \
            -o -name "fo_options.txt" \
            -o -name "*.ini" \
            -o -name "*.cfg" \
        \) \
        -print
fi

echo "=== Locating cospar.txt ==="

COSPAR_SOURCE=""

if [ -f "/tmp/find_orb/cospar.txt" ]; then
    COSPAR_SOURCE="/tmp/find_orb/cospar.txt"
fi

if [ -z "$COSPAR_SOURCE" ]; then
    COSPAR_SOURCE="$(find /tmp/find_orb \
        -type f \
        -name "cospar.txt" \
        -print -quit)"
fi

if [ -z "$COSPAR_SOURCE" ]; then
    echo "ERROR: cospar.txt was not found."
    echo "Find_Orb source tree:"
    find /tmp/find_orb \
        -maxdepth 3 \
        -type f | head -100
    exit 1
fi

echo "Found cospar.txt:"
echo "$COSPAR_SOURCE"

cp "$COSPAR_SOURCE" \
   "$PROJECT_ROOT/backend/findorb-data/cospar.txt"

echo "=== Locating additional Find_Orb configuration files ==="

for FILE in \
    command.txt \
    eph_type.txt \
    fo_options.txt \
    classes.txt \
    asteroid_classes.txt \
    satellite_classes.txt
do

    SOURCE="$(find /tmp/find_orb \
        -type f \
        -name "$FILE" \
        -print -quit)"

    if [ -n "$SOURCE" ]; then

        echo "Copying $FILE"

        cp "$SOURCE" \
           "$PROJECT_ROOT/backend/findorb-data/$FILE"

    fi

done

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
ls -lh "$PROJECT_ROOT/backend/bin/fo"

echo ""
echo "Runtime configuration:"
ls -lh "$PROJECT_ROOT/backend/findorb-data"

echo ""
echo "cospar.txt:"
ls -lh "$PROJECT_ROOT/backend/findorb-data/cospar.txt"

echo ""
echo "DE430:"
ls -lh \
    "$PROJECT_ROOT/backend/findorb-data/linux_p1550p2650.430t"

echo ""
echo "========================================"
echo " Build completed successfully!"
echo "========================================"
