import bech32
import requests
import math
import re
import os

from tqdm import tqdm

OUTPUT_DIR = "output"
EXPORT_DIRECTORY = "exports"
FINAL_DIRECTORY = "final"

def convert_address_to_craft(address) -> str:
    if address.startswith('0x'):
        return None  # TODO: DIG 0x addresses? how do we convert to beh32
    _, data = bech32.bech32_decode(address)
    return bech32.bech32_encode('craft', data)


def createDefaultPathsIfNotExisting():
    if not os.path.exists(EXPORT_DIRECTORY):
        os.mkdir(EXPORT_DIRECTORY)
    if not os.path.exists(OUTPUT_DIR):
        os.mkdir(OUTPUT_DIR)
    if not os.path.exists(FINAL_DIRECTORY):
        os.mkdir(FINAL_DIRECTORY) # where we place completed files

def getOutputFileName(chain_name, reason="staking_values"):
    return f"{OUTPUT_DIR}/{chain_name}_{reason}.txt"





def getExportsOnWebsiteIndex(link="https://reece.sh/exports/index.html", extensions="(.*xz)") -> list:
    '''
    Returns a list of all .xz files on a website (by default).
    This index.html was generated with the following command on the server:
        apt install tree; tree -H '.' -L 1 --noreport --charset utf-8 -P "*.xz" -o index.html 
    '''
    html = requests.get(link).text
    files = re.findall(f'href="{extensions}"', html)
    return list(x for x in (files))


def downloadAndDecompressXZFileFromServer(baseLink="https://reece.sh/exports", fileName="app_export.json.xz", debug=False):
    # doesn't download if we already have a copy of the xz file OR the json file normally
    if os.path.exists(f"exports/{fileName}") or os.path.exists(f"exports/{fileName.replace('.xz', '')}"):
        if debug: 
            print(f"{fileName} already exists, skipping")
        return

    os.chdir("exports")
    
    # response = requests.get(baseLink + "/" + fileName, stream=True)
    # with open(fileName, 'wb') as f:
        # f.write(response.content)

    print(f"Downloading {fileName}...")
    download(baseLink + "/" + fileName, fileName)
    print(f"Downloaded {fileName}!\nDecompressing....")

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
