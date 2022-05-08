import requests
import ijson # https://pypi.org/project/ijson/#usage JSON as a stream
import json
import re
import os

import src.utils as utils

from src.airdrop_data import AIRDROP_DISTRIBUTIONS, AIRDROP_RATES, \
    BLACKLISTED_CENTRAL_EXCHANGES, GENESIS_VALIDATORS, ATOM_RELAYERS

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

# used for all chains so we can get a persons % of total stake
totalStakedUTokens = {}

# When going over the cosmos chain, we calculate the total stake
# all their validators have. Then get users &'s absed off this.
# This is calulated in group 1, but not used until group 3 :)
totalAtomRelayersTokens = 0 

totalIONSupply = { # 2, 630, 151, 640 based on dexmos.app
    "uion": 0, # used in group 5
    "gamm/pool/2": 0,
    "gamm/pool/630": 0,
    "gamm/pool/151": 0,
    "gamm/pool/640": 0,
}

def main():
    global totalStakedUTokens
    # makes exports & output directories
    utils.createDefaultPathsIfNotExisting()

    files = {
        "osmosis": "exports/osmosis_export.json",
        # "akash": "exports/akash_export.json",
        # "cosmos": "exports/cosmos_export.json",
        # "juno": "exports/juno_export.json",
    }
    
    # Downloads files to exports dir if not already downloaded
    for file in utils.getExportsOnWebsiteIndex():
        # if "juno" in file: # to do only 1 for testing
        utils.downloadAndDecompressXZFileFromServer(fileName=file)

    

    # save stake amount data to a a file
    # for chain in files.keys():
    #     totalTokens = save_staked_amounts(files[chain], utils.getOutputFileName(chain))
    #     totalStakedUTokens[chain] = totalTokens

    # Group 1
    # for chain in ["akash", "cosmos", "juno", "osmosis"]:
    # for chain in ["cosmos"]:
    #     # if chain in files: # to do only ones uncommented
    #     # Gets the staked amount file & does the logic on it for the airdrop
    #     group1_stakers_with_genesis_bonus(chain)
    # group3_atom_relayers()

    # Group 2
    if True: # Change to True to run osmosis logic
        # saves osmosis balances & does the pool airdrop calculation
        save_balances(
            files['osmosis'], 
            'output/osmosis_balances.json', 
            ignoreNonNativeIBCDenoms=True, 
            ignoreEmptyAccounts=True
        )            
        # group2_fairdrop_for_osmosis_pools() # group 2
        group5_ION_holders_and_LPers()


def group1_stakers_with_genesis_bonus(chainName):
    '''Group 1: Stakers and Genesis Bonus for Akash, Osmosis, Cosmos, Juno'''
    print(f"Running Group 1  airdrop for {chainName}")

    # TODO: Actual airdrop allotments
    CRAFT_ALLOTMENTS = {
        "juno": 1_000_000, # 1mil craft for all juno stakers + bonus on top of this
        "akash": 5_000_000, 
        "cosmos": 2_500_000,
        "osmosis": 3_500_000
    }

    ACTUAL_ALLOTMENT_GIVEN = 0 # This should be higher since bonuses
    ACTUAL_BONUS_GIVEN = 0

    stake_balance_filename = utils.getOutputFileName(chainName)

    reset_craft_airdrop_temp_dict()
    for delegator, valaddr, bonus, ustake in yield_staked_values(stake_balance_filename):
        # print(f"{delegator} {valaddr} {bonus} {ustake}")

        theirPercentOfAllStaked = float(ustake) / totalStakedUTokens[chainName]
        theirAllotment = theirPercentOfAllStaked * CRAFT_ALLOTMENTS[chainName] # how much craft THEY get before bonus

        ACTUAL_ALLOTMENT_GIVEN += theirAllotment # actual craft being given

        bonus = float(bonus)
        if bonus > 1.0:
            ACTUAL_BONUS_GIVEN += (theirAllotment*bonus)
            theirAllotment = theirAllotment*bonus # since we save 1.0 bonuses, we could just do this. For now here to debug
            # print(f"{theirAllotment} for {theirPercentOfAllStaked} of {totalStakedUTokens[chainName]} with bonus")

        # saving as ucraft for them
        add_airdrop_to_craft_account(str(delegator), theirAllotment * 1_000_000)
    
    with open(f"final/group1_{chainName}.json", 'w') as o:
        o.write(json.dumps(craft_airdrop_amounts))
    reset_craft_airdrop_temp_dict()

    print(f"{chainName} airdrop - ALLOTMENT: {CRAFT_ALLOTMENTS[chainName]}")
    print(f"GIVEN EXCLUDING BONUS: {ACTUAL_ALLOTMENT_GIVEN} + BONUSES: {ACTUAL_BONUS_GIVEN} = {ACTUAL_ALLOTMENT_GIVEN + ACTUAL_BONUS_GIVEN} TOTAL")

def group3_atom_relayers(): # cosmos
    '''Group 3: ATOM Relayers, we <3 you!'''
    print(f"Running Group 3 airdrop for atom relayers validators ")

    # TODO: Actual airdrop allotments
    CRAFT_ALLOTMENTS = 5_000_000

    ACTUAL_ALLOTMENT_GIVEN = 0 

    allCosmosStakers = utils.getOutputFileName("cosmos")

    reset_craft_airdrop_temp_dict()
    for delegator, valaddr, bonus, ustake in yield_staked_values(allCosmosStakers):
        
        if valaddr not in ATOM_RELAYERS.keys():
            continue # wse only want people delegated to relayers here

        theirPercentOfAllStaked = float(ustake) / totalAtomRelayersTokens
        theirAllotment = theirPercentOfAllStaked * CRAFT_ALLOTMENTS # how much craft THEY get before bonus

        ACTUAL_ALLOTMENT_GIVEN += theirAllotment # debugging: actual craft being given, 
        
        add_airdrop_to_craft_account(str(delegator), theirAllotment * 1_000_000)
    
    with open(f"final/group3_atomrelayers.json", 'w') as o:
        o.write(json.dumps(craft_airdrop_amounts))
    reset_craft_airdrop_temp_dict()

    print(f"GROUP 3 airdrop - Atom Relayers - ALLOTMENT: {CRAFT_ALLOTMENTS}. ACTUAL: {ACTUAL_ALLOTMENT_GIVEN}")



def group4_chandra_station_delegators():
    chandra_station = { # This is just copy pasted from GENESIS_VALIDATORS. Boost already applied in group1
        'akashvaloper1lxh0u07haj646pt9e0l2l4qc3d8htfx5kk698d': 1.2, 
        'osmovaloper10ymws40tepmjcu3a2wuy266ddna4ktas0zuzm4': 1.2,
        'junovaloper106y6thy7gphzrsqq443hl69vfdvntgz260uxlc': 1.2,
        'sentvaloper1lxh0u07haj646pt9e0l2l4qc3d8htfx543ss9m': 1.2,
        'emoneyvaloper1lxh0u07haj646pt9e0l2l4qc3d8htfx5ev9y8d': 1.2,
        'comdexvaloper1lxh0u07haj646pt9e0l2l4qc3d8htfx59hp5ft': 1.2,
        'gravityvaloper1728s3k0mgzmc38eswpu9seghl0yczupyhc695s': 1.2,
        'digvaloper1dv3v662kd3pp6pxfagck4zyysas82adspfvtw4': 1.2, 
        'chihuahuavaloper1lxh0u07haj646pt9e0l2l4qc3d8htfx5pd5hur': 1.2,
    }

    CHANDRA_CRAFT_ALLOTMENTS = {
        "akash": 250_000,
        "osmosis": 100_000,
        "juno": 100_000,
        "sent": 100_000,
        "emoney": 100_000,
        "comdex": 100_000,
        "gravity": 100_000, # ?? can we do
        "dig": 100_000, # ?? how do we do 0x
        "chihuahua": 100_000,
    }
    
    
def group5_ION_holders_and_LPers():
    '''Group 5: ION Holders and LPers'''
    print(f"Running Group 5 airdrop for ION holders and LPers ")

    CRAFT_ION_ALLOTMENT = { # 2, 630, 151, 640 based on dexmos.app
        "uion": 500_000,
        "gamm/pool/2": 50_000,
        "gamm/pool/630": 50_000,
        "gamm/pool/151": 25_000,
        "gamm/pool/640": 25_000,
    }
    ACTUAL_LP_ALLOTMENT = 0
    ACTUAL_ION_ALLOTMENT = 0
    # ensure you have already save_balances() up in main before this section

    with open("output/osmosis_balances.json", 'r') as f:
        osmosis_balances = json.loads(f.read())

    for address in osmosis_balances.keys():
        # print(address, osmosis_balances[address])

        for denom in osmosis_balances[address].keys():

            if denom == "uion" or denom in CRAFT_ION_ALLOTMENT.keys():  
                balance = float(osmosis_balances[address][denom])
                totalSupply = totalIONSupply[denom]

                percentOfTotalSupply = balance / totalSupply
                theirAllotment = percentOfTotalSupply * CRAFT_ION_ALLOTMENT[denom]

                if denom == "uion":
                    ACTUAL_ION_ALLOTMENT += theirAllotment
                else:
                    ACTUAL_LP_ALLOTMENT += theirAllotment

                add_airdrop_to_craft_account(address, theirAllotment * 1_000_000)

    with open(f"final/group5_ion.json", 'w') as o:
        o.write(json.dumps(craft_airdrop_amounts))

    print(f"GROUP 5 airdrop - ION - ALLOTMENT (includes ion too): {CRAFT_ION_ALLOTMENT}.")
    print(f"{ACTUAL_LP_ALLOTMENT=}")
    print(f"{ACTUAL_ION_ALLOTMENT=}")

                



# Required for every chain we use
def save_staked_amounts(input_file, output_file, excludeCentralExchanges=True):
    global totalAtomRelayersTokens
    '''
    Returns total supply of staked tokens for this chain network
    '''

    print(f"Saving staked amounts to {output_file}. {excludeCentralExchanges=}")
    totalStaked = 0
    output = ""
    delegatorsWithBonuses = 0 # just for stats
    # totalAccounts = 0
    for idx, obj in stream_section(input_file, 'staked_amounts'):
        delegator = str(obj['delegator_address'])
        valaddr = str(obj['validator_address'])
        stake = str(obj['shares'])   

        totalStaked += float(stake)

        # for group 3 :)
        if 'cosmos' in input_file and valaddr in ATOM_RELAYERS.keys():
            totalAtomRelayersTokens += float(stake)

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

    print(f"Total staked utokens: {totalStaked} from {input_file}")
    return totalStaked


def yield_staked_values(input_file):
    with open(input_file, 'r') as f:
        for line in f:
            line = line.strip()
            delegator, valaddr, bonus, ustake = line.split(' ')
            yield delegator, valaddr, bonus, ustake # ensure this matches up with save_staked_amounts() func


def save_balances(input_file, output_file, ignoreNonNativeIBCDenoms=True, ignoreEmptyAccounts=True):
    global totalIONSupply

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

            if denom in totalIONSupply.keys():
                totalIONSupply[denom] += float(amount) # uion, and 4 pools which are ion based. used in group 5

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


def group2_fairdrop_for_osmosis_pools():
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

# used in above function. 
def osmosis_get_all_LP_providers(filePath): # for group 2
    '''
    group2_fairdrop_for_osmosis_pools() calls this to get the totalSupply & all poolHolders for 1 & 561.
    Then the group2_fairdrop_for_osmosis_pools() function loops through these values again to get % of the pool
    THEN it dumps to file
    '''
     
    if not os.path.exists(filePath):
        print(f"{filePath} does not exist, exiting")
        print("Be sure it is not commented out in main() & you ran it at least once")
        return {}, {}

    with open(f"{filePath}", 'r') as f:
        osmosis_balances = json.loads(f.read())

    poolHolders = {}
    # TODO: add ion pools here too? 2, 630, 151, 640 - also add on line:
    # poolHolders[address] = {"gamm/pool/1": 0, "gamm/pool/561": 0}
    totalSupply = {"gamm/pool/1": 0, "gamm/pool/561": 0}

    # Puts pool holders in dict, and updates total supply.
    for acc in osmosis_balances:
        address = acc
        coins = osmosis_balances[acc]
        # print(address, coins)

        for denom in coins:
            amount = coins[denom]
            # print(f"{address} has {amount} {denom}") # shows all balances

            if denom not in totalSupply.keys(): # atom/osmo, luna/osmo
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