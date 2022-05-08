import requests
import ijson # https://pypi.org/project/ijson/#usage JSON as a stream
import json
import re
import os

import src.utils as utils

from src.airdrop_data import AIRDROP_DISTRIBUTIONS, AIRDROP_RATES, \
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
        if "osmosis" in file: # only testing osmo right now
            utils.downloadAndDecompressXZFileFromServer(fileName=file)

    # save stake amount data to a a file
    for chain in files.keys():
        save_staked_amounts(files[chain], utils.getOutputFileName(chain))

    if True: # Change to True to run osmosis logic
        # saves osmosis balances & does the pool airdrop calculation
        save_balances(
            files['osmosis'], 
            'output/osmosis_balances.json', 
            ignoreNonNativeIBCDenoms=True, 
            ignoreEmptyAccounts=True
        )
        fairdrop_for_osmosis_pools()



def save_staked_amounts(input_file, output_file, excludeCentralExchanges=True):
    print(f"Saving staked amounts to {output_file}. {excludeCentralExchanges=}")
    output = ""
    delegatorsWithBonuses = 0 # just for stats
    # totalAccounts = 0
    for idx, obj in stream_section(input_file, 'staked_amounts'):
        delegator = str(obj['delegator_address'])
        valaddr = str(obj['validator_address'])
        stake = str(obj['shares'])        

        # totalAccounts += 1
        if idx % 25_000 == 0:
            print(f"{idx} staking accounts processing...")

        if excludeCentralExchanges == True and valaddr in BLACKLISTED_CENTRAL_EXCHANGES:
            # print(f"Skipping {delegator} because they are on a central exchange holder {valaddr}")
            continue

        bonus = 1.0 # no bonus by default. View git issue for how to impliment it right for other non core chains
        if valaddr in GENESIS_VALIDATORS.keys():
            bonus = GENESIS_VALIDATORS[valaddr] # 'akashvaloper1lxh0u07haj646pt9e0l2l4qc3d8htfx5kk698d': 1.2,
            delegatorsWithBonuses += 1 # just for statistics

        output += f"{delegator} {valaddr} {bonus} {float(stake)}\n"

    print(f"{idx} staking accounts processed from {input_file}")
    print(f"{delegatorsWithBonuses=}\n")
    with open(output_file, 'w') as o:
        o.write(output)


def save_balances(input_file, output_file, ignoreNonNativeIBCDenoms=True, ignoreEmptyAccounts=True):
    print(f"Saving balances to {output_file}. {ignoreNonNativeIBCDenoms=} {ignoreEmptyAccounts=}")
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

        if idx % 50_000 == 0:
            print(f"{idx} balances accounts processed")

        if ignoreEmptyAccounts and len(outputCoins) == 0:
            continue

        # print(f"{address} {outputCoins}")
        # output += f"{address} {outputCoins}\n"
        accounts[address] = outputCoins
        
    print(f"{idx} accounts processed from {input_file}")
    with open(output_file, 'w') as o:
        o.write(json.dumps(accounts))
        


craft_airdrop_amounts = {} # ENSURE YOU RESET THIS AFTER SAVING FOR A GROUP
def add_airdrop_to_craft_account(craft_address, amount):
    global craft_airdrop_amounts
    '''
    Adds an airdrop amount to their craft account
    '''

    if not craft_address.startswith('craft'):
        craft_address = utils.convert_address_to_craft(craft_address)
    
    if craft_address not in craft_airdrop_amounts:
        craft_airdrop_amounts[craft_address] = 0

    craft_airdrop_amounts[craft_address] += amount

def reset_craft_airdrop_temp_dict():
    '''
    Call this after you calulate all values for a given group &
    save that group to its own unique txt file.
    '''
    global craft_airdrop_amounts
    craft_airdrop_amounts = {}


def fairdrop_for_osmosis_pools():
    '''Group #2 - LPs for pool #1 and #561 (luna/osmo)'''

    filePath = "output/osmosis_balances.json" 

    # FORMAT: poolHolder in file: {"osmoaddress": {"gamm/pool/1": 0, "gamm/pool/561": 0}, {...}}
    # FORMAT: totalSupply in file: {"gamm/pool/1": 0, "gamm/pool/561": 0}
    totalSupply, poolHolders = osmosis_get_all_LP_providers(filePath)    
    if totalSupply == {}: # filePath doesn't exist yet
        return

    CRAFT_SUPPLY_FOR_POOLS = { 
        # TODO: change this with bean based on which rates we give each. move into airdrop_data file.
        "gamm/pool/1": 1_000_000, # Move these into airdrop data
        "gamm/pool/561": 1_500_000
    }
    

    # DEBUGGING - just to check that this is close to CRAFT_SUPPLY_FOR_POOLS total
    totalCraftGivenActual = { "gamm/pool/1": 0, "gamm/pool/561": 0}

    for address in poolHolders.keys():
        # usersPoolPercent = {"gamm/pool/1": 0, "gamm/pool/561": 0}

        for token in ["gamm/pool/1", "gamm/pool/561"]:
            # A users LP Token Share
            tokenAmount = int(poolHolders[address][token])
            if tokenAmount == 0:
                continue

            # decimal percent -> ex 0.00002
            theirPercentOwnership = (tokenAmount / int(totalSupply[token])) 

            # (totalSupplyForGivenPool*0.00002) = theirAllotmentOfCraft
            theirCraftAllotment = CRAFT_SUPPLY_FOR_POOLS[token] * theirPercentOwnership 

            # DEBUG to ensure we are close to giving out ALL of the amount of CRAFT for each pool here
            totalCraftGivenActual[token] += theirCraftAllotment

            # Saved as ucraft
            add_airdrop_to_craft_account(address, theirCraftAllotment * 1_000_000)

            # if token == "gamm/pool/561": # DEBUG
            #     print(f"{address}'s {token} -> {theirCRAFTForThisGroup}craft")


    # save each osmo addresses % of the given pool based on the total supply
    # This will be easier to just do theirPercent*totalCraftSupplyForGroup2 = Their craft
    with open("final/Group2_LP_Pools_Craft_Amounts.json", 'w') as o:
        o.write(json.dumps(craft_airdrop_amounts))
    
    reset_craft_airdrop_temp_dict()

    print(f":::LPs:::\nNumber of unique wallets providing liquidity to #1 & #561: {len(poolHolders)}")
    print(f"Total supply: {totalSupply}")
    print(f"Total craft given: {totalCraftGivenActual=} out of {CRAFT_SUPPLY_FOR_POOLS=}")

def osmosis_get_all_LP_providers(filePath): # for group 2
    '''
    fairdrop_for_osmosis_pools() calls this to get the totalSupply & all poolHolders for 1 & 561.
    Then the fairdrop_for_osmosis_pools() function loops through these values again to get % of the pool
    THEN it dumps to file
    '''
     
    if not os.path.exists(filePath):
        print(f"{filePath} does not exist, exiting")
        print("Be sure it is not commented out in main() & you ran it at least once")
        return {}, {}

    with open(f"{filePath}", 'r') as f:
        osmosis_balances = json.loads(f.read())

    poolHolders = {}
    # TODO: EDIT ME after running this once and paste in the non 0 values of each pool
    totalSupply = {"gamm/pool/1": 0, "gamm/pool/561": 0}

    # Puts pool holders in dict, and updates total supply.
    for acc in osmosis_balances:
        address = acc
        coins = osmosis_balances[acc]
        # print(address, coins)

        for denom in coins:
            amount = coins[denom]
            # print(f"{address} has {amount} {denom}") # shows all balances

            if denom not in ["gamm/pool/561", "gamm/pool/1"]: # atom/osmo, luna/osmo
                continue # checks next coin denom in coins

            if address not in poolHolders:
                poolHolders[address] = {"gamm/pool/1": 0, "gamm/pool/561": 0}

            poolHolders[address][denom] = amount
            totalSupply[denom] += int(amount) # add to total supply for stats
            # print(poolHolders)

    return totalSupply, poolHolders


   
    
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