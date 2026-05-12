#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RAW_DIR="$SCRIPT_DIR/raw"
VENV_PYTHON="$SCRIPT_DIR/../venv/bin/python"

mkdir -p "$RAW_DIR"

echo "=== Downloading CASAS Aruba raw data ==="
if [ ! -f "$RAW_DIR/aruba.csv" ]; then
    $VENV_PYTHON -c "
import urllib.request, struct, zlib, sys

url = 'https://zenodo.org/records/15708568/files/data.zip?download=1'
local_offset = 2117635050
comp_size = 12117151
out_path = sys.argv[1]

req = urllib.request.Request(url)
req.add_header('Range', f'bytes={local_offset}-{local_offset + 300}')
header = urllib.request.urlopen(req).read()

fname_len = struct.unpack('<H', header[26:28])[0]
extra_len = struct.unpack('<H', header[28:30])[0]
data_offset = local_offset + 30 + fname_len + extra_len

print(f'Downloading aruba.csv ({comp_size/1024/1024:.1f} MB compressed)...')
req2 = urllib.request.Request(url)
req2.add_header('Range', f'bytes={data_offset}-{data_offset + comp_size - 1}')
comp_data = urllib.request.urlopen(req2).read()

raw = zlib.decompress(comp_data, -15)
print(f'Decompressed: {len(raw)/1024/1024:.1f} MB')

with open(out_path, 'wb') as f:
    f.write(raw)
print(f'Saved to {out_path}')
" "$RAW_DIR/aruba.csv"
    echo "CASAS Aruba downloaded."
else
    echo "aruba.csv already exists, skipping."
fi

echo ""
echo "=== Downloading Llumiguano et al. test set ==="
ZENODO_DIR="$RAW_DIR/zenodo_test"
mkdir -p "$ZENODO_DIR"
if [ ! -d "$ZENODO_DIR/CASAS" ]; then
    curl -L -o "$RAW_DIR/CASAS.zip" "https://zenodo.org/records/15800764/files/CASAS.zip?download=1"
    cd "$RAW_DIR"
    unzip -o CASAS.zip -d zenodo_test/
    rm -f CASAS.zip
    cd "$SCRIPT_DIR"
    echo "Zenodo test set downloaded."
else
    echo "Zenodo test set already exists, skipping."
fi

echo ""
echo "=== Download complete ==="
echo "Raw dir contents:"
ls -la "$RAW_DIR"
echo ""
echo "Zenodo test dir:"
find "$ZENODO_DIR" -type f | head -20
