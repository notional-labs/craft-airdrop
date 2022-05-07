import bech32
import requests
import re
import os

OUTPUT_DIR = "output"
EXPORT_DIRECTORY = "exports"

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

def getOutputFileName(chain_name):
    return f"{OUTPUT_DIR}/{chain_name}_staking_values.txt"





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
    if os.path.exists(f"exports/{fileName}"):
        if debug: 
            print(f"{fileName} already exists, skipping")
        return

    os.chdir("exports")
    with open(fileName, 'wb') as f:
        print(f"Downloading {fileName}...")
        response = requests.get(baseLink + "/" + fileName)
        f.write(response.content)
    print(f"Downloaded {fileName}!\nDecompressing....")

    # decompress the xz file
    os.system(f"xz -d {fileName}")
    print(f"Decompressed {fileName}")
    os.chdir("..")