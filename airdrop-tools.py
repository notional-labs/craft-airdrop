import requests
import ijson # https://pypi.org/project/ijson/#usage JSON as a stream
import json
import re
import os

import src.utils as utils

from airdrop_data import NETWORKS, AIRDROP_DISTRIBUTIONS, AIRDROP_RATES, \
    BLACKLISTED_CENTRAL_EXCHANGES, GENESIS_VALIDATORS

'''
Snapshot tooling to stream an export to a file for easier handling in easy formats

v46 genesis - https://github.com/notional-labs/craft/blob/master/networks/craft-testnet-1/genesis.json
# app_state.distribution.delegator_starting_infos

Example:
osmosisd export 3500001 2> osmosis_export.json
# Done Automatically:
Compress:
    xz appd_export.json
Download:
    https://reece.sh/exports/<name>_export.json.xz
Decompress
    xz -d appd_export.json.xz
'''


sections = { # locations within the genesis file
    "staked_amounts": "app_state.staking.delegations",
    "account_balances": "app_state.bank.balances",
}

def main():
    # makes exports & output directories
    utils.createDefaultPathsIfNotExisting()

    files = {     
        # "craft": "exports/craft_export.json",
        "osmosis": "exports/osmosis_export.json",
        # "akash": "exports/akash_export.json",
        # "cosmos": "exports/cosmos_export.json",
        # "juno": "exports/juno_export.json",
    }
    
    # Downloads files to exports dir if not already downloaded
    for file in utils.getExportsOnWebsiteIndex():
        utils.downloadAndDecompressXZFileFromServer(fileName=file)

    # save stake amount data to a a file
    for chain in files.keys():
        save_staked_amounts(files[chain], utils.getOutputFileName(chain))

    if False: # Change to True to run osmosis logic
        # saves osmosis balances & does the pool airdrop calculation
        save_balances(
            files['osmosis'], 
            'output/osmosis_balances.json', 
            ignoreNonNativeIBCDenoms=True, 
            ignoreEmptyAccounts=True
        )
        fairdrop_for_osmosis_pools()



def save_staked_amounts(input_file, output_file, excludeCentralExchanges=True):
    output = ""
    # totalAccounts = 0
    for idx, obj in stream_section(input_file, 'staked_amounts'):
        delegator = str(obj['delegator_address'])
        valaddr = str(obj['validator_address'])
        stake = str(obj['shares'])        

        # totalAccounts += 1
        if idx % 10_000 == 0:
            print(f"{idx} accounts processing...")

        if excludeCentralExchanges == True and valaddr in BLACKLISTED_CENTRAL_EXCHANGES:
            # print(f"Skipping {delegator} because they are on a central exchange holder {valaddr}")
            continue

        bonus = 1.0 # no bonus by default for now. Look back at notes for how to implement properly
        if valaddr in GENESIS_VALIDATORS.keys():
            bonus = GENESIS_VALIDATORS[valaddr] # 'akashvaloper1lxh0u07haj646pt9e0l2l4qc3d8htfx5kk698d': 1.2,
    
        if bonus > 1.0:
            print(f"{delegator} would get a bonus of {bonus}x for delegating to genesis validator {valaddr}")

        output += f"{delegator} {valaddr} {float(stake)}\n"

    print(f"{idx} accounts processed from {input_file}")
    with open(output_file, 'w') as o:
        o.write(output)


def save_balances(input_file, output_file, ignoreNonNativeIBCDenoms=True, ignoreEmptyAccounts=True):
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

                outputCoins[denom] = amount # {'uion': 1000000, 'uosmo': 1000000}

            if idx % 10_000 == 0:
                print(f"{idx} accounts processed")

            if ignoreEmptyAccounts and len(outputCoins) == 0:
                continue

            # print(f"{address} {outputCoins}")
            # output += f"{address} {outputCoins}\n"
            accounts[address] = outputCoins
            
        print(f"{idx} accounts processed from {input_file}")
        with open(output_file, 'w') as o:
            o.write(json.dumps(accounts))
        

craft_airdrop_amounts = {}
def add_airdrop_to_account(craft_address, amount):
    global craft_airdrop_amounts
    if craft_address not in craft_airdrop_amounts:
        craft_airdrop_amounts[craft_address] = 0
    craft_airdrop_amounts[craft_address] += amount
    pass

def fairdrop_for_osmosis_pools():
    '''Group #2 - LPs for pool #1 and #561 (luna/osmo)'''
    # TODO: POOL #1 & #561 (luna/osmo) - not done
    
    filePath = "output/osmosis_balances.json"
    # Ensure output/osmosis_balances.json exists
    if not os.path.exists(filePath):
        print(f"{filePath} does not exist, exiting")
        print("Be sure it is not commented out in main() & you ran it at least once")
        return

    # Load the osmosis balances file
    with open(f"{filePath}", 'r') as f:
        osmosis_balances = json.loads(f.read())

    poolHolders = {}
    # keep up with the total suppy outstanding for the snapshot
    # so we can get their % of the pool
    totalSupply = {"gamm/pool/1": 0, "gamm/pool/561": 0}

    for acc in osmosis_balances:
        address = acc
        coins = osmosis_balances[acc]
        # print(address, coins)

        for denom in coins:
            amount = coins[denom]
            # print(f"{address} has {amount} {denom}") # shows all balances

            if denom in ["gamm/pool/561", "gamm/pool/1"]: # atom/osmo, luna/osmo
                if address not in poolHolders:
                    pools = {"gamm/pool/1": 0, "gamm/pool/561": 0}
                    poolHolders[address] = pools

                poolHolders[address][denom] = amount
                totalSupply[denom] += int(amount) # add to total supply for stats
                # print(poolHolders)

    # save poolHolders to a pool.json file in the output directory
    with open("output/pool.json", 'w') as o:
        o.write(json.dumps(poolHolders))

    print(f"LPs\nNumber of unique wallets providing liquidity: {len(poolHolders)}")
    print(f"Total supply: {totalSupply}")


   
    
def stream_section(fileName, key):
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
            yield idx, obj


if __name__ == "__main__":
    # Every section must have .item for the json stream to parse
    for key in sections:
        if sections[key].endswith('.item') == False:
            sections[key] += '.item'
    
    # run the main logic
    main()