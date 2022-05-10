import bech32
import requests
import re
import os

import ijson

from tqdm import tqdm

requiredDirs = ["output", "exports", "final"] # auto created

sections = { 
    # locations within the genesis file
    # for ijson, every section MUST end with .item to grab the values
    "staked_amounts": "app_state.staking.delegations.item",
    "account_balances": "app_state.bank.balances.item",
    "total_supply": "app_state.bank.supply.item",
}    
def stream_section(fileName, key, debug=False):
    '''
        Given a fileName and a json key location,
        it will stream the jso objects in that section 
        and yield them as:
        -> index, object
    '''
    if key not in sections:
        print(f"{key} not in sections")
        return

    key = sections[key]

    with open(fileName, 'rb') as input_file:
        parser = ijson.items(input_file, key)
        for idx, obj in enumerate(parser):
            if debug: print(f"stream_section: {idx}: {obj}")
            yield idx, obj


def convert_address_to_craft(address) -> str:
    if address.startswith('0x'):
        return None  # TODO: DIG 0x addresses? how do we convert to beh32. Gravity bridge too?
    _, data = bech32.bech32_decode(address)
    return bech32.bech32_encode('craft', data)


def createDefaultPathsIfNotExisting():
    for dir in requiredDirs:
        if not os.path.exists(dir):
            os.mkdir(dir)

def getOutputFileName(chain_name, reason="staking_values", extension="json"):
    if extension.startswith("."):
        extension = extension[1:]
    return f"output/{chain_name}_{reason}.{extension}"





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
    
    # response = requests.get(baseLink + "/" + fileName, stream=True)
    # with open(fileName, 'wb') as f:
        # f.write(response.content)

    print(f"\n [!] Downloading {fileName}...")
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





## ==== Saving chain values ====
from src.airdrop_data import ATOM_RELAYERS, BLACKLISTED_CENTRAL_EXCHANGES, GENESIS_VALIDATORS
import json

# Just for atom relayers validators. Is only increased if the input file has 'cosmos' in it ($ATOM)
totalAtomRelayersTokens = 0

# Required for every chain we use
def save_staked_amounts(input_file, output_file, excludeCentralExchanges=True) -> int:
    global totalAtomRelayersTokens
    '''
    Returns total supply of staked tokens for this chain network
    '''
    if os.path.isfile(output_file):
        print(f"[!] {output_file} already exists, skipping")
        return -1

    print(f"Saving staked amounts to {output_file}. {excludeCentralExchanges=}")
    totalStaked = 0
    output = ""
    delegatorsWithBonuses = 0 # just for stats

    for idx, obj in stream_section(input_file, 'staked_amounts'):
        delegator = str(obj['delegator_address'])
        valaddr = str(obj['validator_address'])
        stake = str(obj['shares'])   

        totalStaked += float(stake)

        # for group 3 atom relayers
        if 'cosmos' in input_file and valaddr in ATOM_RELAYERS.keys():
            totalAtomRelayersTokens += float(stake)

        if idx % 50_000 == 0:
            print(f"{idx} staking accounts processing...")

        if excludeCentralExchanges == True and valaddr in BLACKLISTED_CENTRAL_EXCHANGES:
            # print(f"Skipping {delegator} because they are on a central exchange holder {valaddr}")
            continue

        bonus = 1.0 # no bonus by default. View git issue for how to impliment it right for other non core chains
        if valaddr in GENESIS_VALIDATORS.keys():
            bonus = GENESIS_VALIDATORS[valaddr] # 'akashvaloper1lxh0u07haj646pt9e0l2l4qc3d8htfx5kk698d': 1.2,
            delegatorsWithBonuses += 1 # just for statistics

        output += f"{delegator} {valaddr} {bonus} {float(stake)}\n"

    # print(f"{idx} staking accounts processed from {input_file}")
    print(f"{delegatorsWithBonuses=}\n")
    with open(output_file, 'w') as o:
        o.write(output)
    
    if totalAtomRelayersTokens > 0:
        # atom relayers total supply held by all their validators
        print(f"Total atom relayers tokens: {totalAtomRelayersTokens}")
        with open("final/atom_relayers_tokens.txt", 'w') as o:
            o.write(f"{totalAtomRelayersTokens}")

    return totalStaked


def yield_staked_values(input_file):
    with open(input_file, 'r') as f:
        for line in f:
            line = line.strip()
            delegator, valaddr, bonus, ustake = line.split(' ')
            yield delegator, valaddr, bonus, ustake # ensure this matches up with save_staked_amounts() func


def save_osmosis_balances(input_file, output_file, getTotalSuppliesOf=["uion", "gamm/pool/2", "gamm/pool/630", "gamm/pool/151", "gamm/pool/640"], ignoreNonNativeIBCDenoms=True, ignoreEmptyAccounts=True) -> dict:
    print(f"Saving balances to {output_file}. {ignoreNonNativeIBCDenoms=} {ignoreEmptyAccounts=}")
    # print(f"Will return a dict of the following total supplies: {getTotalSuppliesOf}")

    # totalSupply = {str(denom).lower(): 0 for denom in getTotalSuppliesOf}

    # totalSupply = {str(denom).lower(): 0 for denom in getTotalSuppliesOf}
    accounts = {}

    for idx, obj in stream_section(input_file, 'account_balances'):
        address = str(obj['address'])
        coins = obj['coins']

        outputCoins = {}
        for coin in coins:
            denom = coin['denom']
            amount = coin['amount']

            if ignoreNonNativeIBCDenoms and str(denom).startswith('ibc/'):
                continue # ignore any non native ibc tokens held by the account

            # if denom in totalSupply.keys():
            #     totalSupply[denom] += float(amount) # uion, and 4 pools which are ion based. used in group 5

            outputCoins[denom] = amount # {'uion': 1000000, 'uosmo': 1000000}

        if idx % 50_000 == 0:
            print(f"{idx} balances accounts processed")

        if ignoreEmptyAccounts and len(outputCoins) == 0:
            continue

        accounts[address] = outputCoins
        
    print(f"{idx} accounts processed from {input_file}")
    with open(output_file, 'w') as o:
        o.write(json.dumps(accounts))
    
    return accounts

import src.utils as utils
def get_total_supply__of_chains(files=[], denomsWeWant=[]):
    temp_Total_Supply = {}

    # Gets the total supply of ALL chains including LPs if in denomsWeWant=[] list
    # Or uses a cached version if that is avaliable.
    if os.path.isfile("final/total_supply.json"):
        with open("final/total_supply.json", 'r') as f:
            temp_Total_Supply = json.load(f)
            print("Loaded TOTAL_SUPPLY from cached file")
    else:
        for fileName in files:
            print("Getting total supply for chain: ", fileName)
            for idx, supply in utils.stream_section(fileName, "total_supply"):
                denom = supply['denom']
                if denom in denomsWeWant: # denoms we want to save to file for tracking totalSupply
                    temp_Total_Supply[denom] = supply['amount']    
        with open("final/total_supply.json", 'w') as o:
            o.write(json.dumps(temp_Total_Supply, indent=4))

    return temp_Total_Supply # save this to main()