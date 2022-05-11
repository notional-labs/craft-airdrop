import requests
import json
import os
import re

import src.utils as utils

from tqdm import tqdm

def getExportsOnWebsiteIndex(link="https://reece.sh/exports/index.html", extensions="(.*xz)", chainsRequested=[]) -> list:
    '''
    Returns a list of all .xz files on a website (by default).
    This index.html was generated with the following command on the server:
        apt install tree; tree -H '.' -L 1 --noreport --charset utf-8 -P "*.xz" -o index.html 
    '''
    html = requests.get(link).text
    serverFiles = re.findall(f'href="{extensions}"', html)
    l = list(f for f in (serverFiles))
    
    if l == None: l = []
    # print(chainsRequested)
    if chainsRequested == []:
        yield []

    for filename in l:
        for c in chainsRequested:
            if c in filename:
                # print(f"Found {c} in {filename}. Yeilding...")
                yield filename


def downloadAndDecompressXZFileFromServer(baseLink="https://reece.sh/exports", fileName="app_export.json.xz", debug=False):
    # doesn't download if we already have a copy of the xz file OR the json file normally
    if os.path.exists(f"exports/{fileName}") or os.path.exists(f"exports/{fileName.replace('.xz', '')}"):
        if debug: 
            print(f"{fileName} already exists, skipping")
        return

    os.chdir("exports")
    print(f"\n [!] Downloading {fileName}...")
    download(baseLink + "/" + fileName, fileName)
    print(f" - Decompressing... via `xz -d` command")

    # decompress the xz file
    os.system(f"xz -d {fileName}")
    print(f"Decompressed {fileName}")
    os.chdir("..")


def download(url, fname):
    resp = requests.get(url, stream=True)
    total = int(resp.headers.get('content-length', 0))
    with open(fname, 'wb') as file, tqdm(
            desc=fname,
            total=total,
            unit='MiB',
            unit_scale=True,
            unit_divisor=1024,
    ) as bar:
        for data in resp.iter_content(chunk_size=1024):
            size = file.write(data)
            bar.update(size)
    print(f"Downloaded {fname}")

