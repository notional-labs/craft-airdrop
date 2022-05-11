import bech32
import requests
import re
import os

import ijson

from tqdm import tqdm

requiredDirs = ["output", "exports", "final", "supply", "balances", "staked"] # auto created

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


def convert_address_to_craft(address, non118coins=["0x", "gravity"]) -> str:
    for bad in non118coins:
        if address.startswith(bad):
            return address # return normal address if not 118 coins

    _, data = bech32.bech32_decode(address)
    return bech32.bech32_encode('craft', data)


def createDefaultPathsIfNotExisting():
    for dir in requiredDirs:
        if not os.path.exists(dir):
            os.mkdir(dir)


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





## ==== Saving chain values ====
from src.airdrop_data import ATOM_RELAYERS, BLACKLISTED_CENTRAL_EXCHANGES, GENESIS_VALIDATORS
import json


def yield_staked_values_from_file(stakedUsersInputFile="staked/chain.json"):
    # with open(stakedUsersInputFile, 'r') as f:
    #     for line in f:
    #         line = line.strip()
    #         delegator, valaddr, bonus, ustake = line.split(' ')
    #         yield delegator, valaddr, bonus, ustake # ensure this matches up with save_staked_amounts() func

    with open(stakedUsersInputFile, 'r') as f:
        data = json.load(f) # Do we need to stream it?

    for validator in data.keys():
        delegators = data[validator]["delegators"]
        for delegate in delegators.keys():
            amount = float(delegators[delegate]["amount"])
            bonus = float(delegators[delegate]["bonus"])
            yield {"delegator": delegate, "validator": validator, "ustake": amount, "bonusMultiplier": bonus}

def yield_balances_from_file(balanceUsersInputFile="balances/chain.json"):
    with open(balanceUsersInputFile, 'r') as f:
        accounts = json.load(f)

    for account in accounts.keys():
        yield {"address": account, "balances": accounts[account]}


# Required for every chain we use
def save_staked_users(input_file="exports/chain.json", output_file="staked/chain.json", 
    excludeCentralExchanges=True, doBonusesForGenesisValidators=True) -> dict:
    '''
    Saves all Validators, some stats, and their delegators:
    {
        "osmovaloperxxxxxxxxx": {
            "stats": {
                "total_stake": "200.0",
            },
            "delegators": {
                "delegator1": 
                    {
                        "amount": 100.0,
                        "bonus": 1.2, # means they get 1.2x their staked amount. 1.0 if no bonus
                    }
                "delegator2": 100.0,
            }
        },
    }
    Returns a dict of information
    '''

    print(f"Saving staked amounts to {output_file}. {excludeCentralExchanges=}")

    # delegatorsWithBonuses = 0 # just for stats
    totalStakedOnChain = 0
    totalBonusAmount = 0
    STAKED_VALUES = {}
    numberOfUniqueDelegators = set()

    for idx, obj in stream_section(input_file, 'staked_amounts'):
        delegator = str(obj['delegator_address'])
        valaddr = str(obj['validator_address'])
        stake = float(obj['shares'])  
        bonus = 1.0 
        if idx % 50_000 == 0: print(f"{idx} staking accounts processing...")

        if excludeCentralExchanges and valaddr in BLACKLISTED_CENTRAL_EXCHANGES:
            continue # skip the central exchange since this is their validator address

        if doBonusesForGenesisValidators and valaddr in GENESIS_VALIDATORS.keys():
            bonus = GENESIS_VALIDATORS[valaddr] # 'akashvaloper1lxh0u07haj646pt9e0l2l4qc3d8htfx5kk698d': 1.2,
            totalBonusAmount += (stake * (bonus-1.0)) # statistics
            delegatorsWithBonuses += 1 # just for statistics

        if valaddr not in STAKED_VALUES:
            STAKED_VALUES[valaddr] = {"stats": {"total_stake": 0}, "delegators": {}}

        STAKED_VALUES[valaddr]["stats"]["total_stake"] += stake
        STAKED_VALUES[valaddr]["delegators"][delegator] = {"ustake": stake, "bonusMultiplier": bonus}
        numberOfUniqueDelegators.add(delegator) # only adds unique user addresses to set

        totalStakedOnChain += stake

        # output += f"{delegator} {valaddr} {bonus} {float(stake)}\n"

    print(f"{delegatorsWithBonuses=}\n")
    with open(output_file, 'w') as o:
        o.write(json.dump(STAKED_VALUES))
    
    print(f"Saved {len(STAKED_VALUES)} validators and {len(numberOfUniqueDelegators)} delegators to {output_file}")
    return {
        "total_staked": totalStakedOnChain, 
        "number_of_validators": len(STAKED_VALUES.keys()),
        "number_of_unique_delegators": len(numberOfUniqueDelegators)
    }


def save_balances_to_file(input_file="exports/chain.json", output_file="balances/chain.json", 
    getTotalSuppliesOf=["uion", "gamm/pool/2", "gamm/pool/630", "gamm/pool/151", "gamm/pool/640"], 
    ignoreNonNativeIBCDenoms=True, ignoreEmptyAccounts=True) -> dict:
    '''
    Saves every balance to the file provided it is in getTotalSuppliesOf.
    If that is left as [], it will save All values to the balances folder.
    You can then iterate through this file to get a users held denoms, such as pools or ibc channel
        tokens if you so wish.

    Returns the JSON to the accounts as:
    {
        "address1": {"udenom": 100, "udenom2": 200, ...},
        "address2": {...}
    }
    '''

    print(f"Saving balances to {output_file}. {ignoreNonNativeIBCDenoms=} {ignoreEmptyAccounts=}")

    accounts = {} # "address": {"udenom": amount, "gamm/pool/2": amount, ...}

    for idx, obj in stream_section(input_file, 'account_balances'):
        address, coins = obj['address'], obj['coins']

        if idx % 50_000 == 0: print(f"{idx} balances accounts processed")

        tempCoins = {}
        for coin in coins:
            denom, amount = coin['denom'], coin['amount']

            if ignoreNonNativeIBCDenoms and str(denom).startswith('ibc/'):
                continue # ignore any non native ibc tokens held by the account

            tempCoins[denom] = amount # {'uion': 1000000, 'uosmo': 1000000, etc...}

        if ignoreEmptyAccounts and len(tempCoins) == 0:
            continue

        accounts[address] = tempCoins
        
    print(f"{idx} accounts processed from {input_file}")
    with open(output_file, 'w') as o:
        o.write(json.dumps(accounts))
    
    return accounts