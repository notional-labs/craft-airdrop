import requests
import ijson # https://pypi.org/project/ijson/#usage JSON as a stream
import json
import re
import os

import src.utils as utils
import src.website_utils as wutils
import src.chain_utils as cutils

from src.airdrop_data import BLACKLISTED_CENTRAL_EXCHANGES, GENESIS_VALIDATORS, ATOM_RELAYERS

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




# used for all chains so we can get a persons % of total stake


# When going over the cosmos chain, we calculate the total stake
# all their validators have. Then get users &'s absed off this.
# This is calulated in group 1, but not used until group 3 :)
totalAtomRelayersTokens = 0 # we grab cosmos cache & loop through valaddrs in ATOM_RELAYERS

TOTAL_SUPPLY = {} 

TOTAL_STAKED_TOKENS = {}

CHAINS = {
    # "cosmos": {
    #     "export": "exports/cosmos_export.json",
    #     "bonding_token": "uatom", 
    #     "denoms": [] # other denoms we want to track the total supply of their balances
    # },
    # "akash": {
    #     "export": "exports/akash_export.json",
    #     "bonding_token": "uakt",
    #     "denoms": []
    # },
    # "juno": {
    #     "export": "exports/juno_export.json",
    #     "bonding_token": "ujuno",
    #     "denoms": []
    # },
    # "osmosis": {
    #     "export": "exports/osmosis_export.json",
    #     "bonding_token": "uosmo",
    #     "denoms": ['uion', 'gamm/pool/1', 'gamm/pool/2', 'gamm/pool/151', 'gamm/pool/630', 'gamm/pool/640', 'gamm/pool/561']
    # },
    "comdex": {
        "export": "exports/comdex_export.json",
        "bonding_token": "ucmdx",
        "denoms": []
    },
    # "desmos": {
    #     "export": "exports/desmos_export.json",
    #     "bonding_token": "udsm",
    #     "denoms": []
    # },
    "dig": {
        "export": "exports/dig_export.json",
        "bonding_token": "udig",
        "denoms": []
    },
    # "sifchain": {
    #     "export": "exports/sifchain_export.json",
    #     "bonding_token": "urowan",
    #     "denoms": []
    # }
}

def main():
    global TOTAL_SUPPLY, TOTAL_STAKED_TOKENS
    utils.createDefaultPathsIfNotExisting()
    
    ## Downloads files to exports dir if not already downloaded AND is in files
    for file in wutils.getExportsOnWebsiteIndex(chainsRequested=list(CHAINS.keys())):
        wutils.downloadAndDecompressXZFileFromServer(fileName=file, debug=False)

    
    fileName = "output/supply/total_supply.json"
    if not os.path.isfile(fileName):
        '''
        Gets the total supply of ALL chains we want including LPs if it is in denomsWeWant
        If it is, it will just return that list
        ex: denomsWeWant = ["uosmo", "uion", "gamm/pool/2", "gamm/pool/630", "gamm/pool/151", "gamm/pool/640"]
        '''
        for chain in CHAINS.keys():
            print("Getting total supply for chain: ", chain)
            
            myChain =  CHAINS[chain]

            denomsWeWant = myChain["denoms"] # do we need to add "bonding_token" here too?
            for idx, supply in utils.stream_section(myChain["export"], "total_supply"):
                denom = supply['denom']
                if denom in denomsWeWant:
                    TOTAL_SUPPLY[denom] = supply['amount']   

        with open(fileName, 'w') as o:
            o.write(json.dumps(TOTAL_SUPPLY))
            
    with open(fileName, 'r') as f:
        TOTAL_SUPPLY = json.load(f)
    print(f"{TOTAL_SUPPLY=}")
    # / End of total supply logic.


    # Save stated data for a given chain: 
    # This makes it easier for us to iterate & see + smaller than the full export
    for chain in CHAINS.keys():
        exportFile = CHAINS[chain]["export"]
        stakedObject = utils.save_staked_users(input_file=exportFile, output_file=f"output/staked/{chain}.json")        
        denom = CHAINS[chain]['bonding_token'] # chain osmosis -> uosmo
        totalStakeduDenom = stakedObject["total_staked"]
        print(f"Total Staked: {totalStakeduDenom} {denom} for chain: {chain}")
        TOTAL_STAKED_TOKENS[denom] = totalStakeduDenom

    # Runs: Group 1 Airdrop. Use this list since all chains are in CHAINS
    # for chain in ["akash", "cosmos", "juno", "osmosis"]:
    # # for chain in ["cosmos"]:
    #     if chain not in CHAINS.keys(): print(f"\n\n[!]Did you remeber to uncomment/add {chain} to the CHAINS dict in main? exiting...\n\n"); exit(1)
    #     group1_stakers_with_genesis_bonus(chain, TOTAL_STAKED_TOKENS, onlyToBondedValidators=True)
    

    # Group 2
    if False: # Change to True to run osmosis logic
        # saves osmosis balances & does the pool airdrop calculation
        osmosisBalances = utils.save_balances_to_file(
            CHAINS['osmosis']['export'], 
            'output/balances/osmosis.json', 
            getTotalSuppliesOf=["uion", "gamm/pool/2", "gamm/pool/630", "gamm/pool/151", "gamm/pool/640"],
            ignoreNonNativeIBCDenoms=True, 
            ignoreEmptyAccounts=True
        )       
        # print(len(osmosisBalances)) 
        # group2_fairdrop_for_osmosis_pools(osmosisBalances, TOTAL_SUPPLY) # group 2
        group5_ION_holders_and_LPers()
    # group3_atom_relayers()

    group6_genesis_set_validators()


def group1_stakers_with_genesis_bonus(chainName: str, TOTAL_STAKED: dict, onlyToBondedValidators=True):
    '''Group 1: Stakers and Genesis Bonus for Akash, Osmosis, Cosmos, Juno'''
    print(f"\n\t[!] Running Group 1  airdrop for {chainName} [!]")

    CRAFT_ALLOTMENTS = {
        "juno": 4_500_000, # 1mil craft for all juno stakers + bonus on top of this
        "akash": 9_000_000, 
        "cosmos": 2_250_000,
        "osmosis": 6_750_000
    }

    print(f"Craft allotment for {chainName}: {CRAFT_ALLOTMENTS[chainName]}")

    ACTUAL_ALLOTMENT_GIVEN = 0 # This should be higher since bonuses
    ACTUAL_BONUS_GIVEN = 0

    stake_balance_filename = f"output/staked/{chainName}.json"

    # check if stake_balance_filename exists
    if not os.path.isfile(stake_balance_filename):
        print(f"{stake_balance_filename} does not exist. Exiting...")
        exit(1)

    BONDED_VALS = {}
    if onlyToBondedValidators:
        print(f"Only sending airdrop to bonded validator's delegators {onlyToBondedValidators=}")
        BONDED_VALS = cutils.getBondedValidators(chainName, export_file=CHAINS[chainName]['export'])
        print(f"# of BONDED_VALS in chain {chainName}: {len(BONDED_VALS)}")

    # We want to reset every time since this group is done for all 4 chains
    reset_craft_airdrop_temp_dict()

    denom = CHAINS[chainName]['bonding_token']
    totalTokensStakedForChain = int(TOTAL_STAKED[denom])
    print(f"- Total {denom} staked for {chainName}: {totalTokensStakedForChain}.")
    # / End of getting token supply

    for delegateObject in utils.yield_staked_values_from_file(stake_balance_filename):
        delegator = delegateObject["delegator"]
        validatorAddress = delegateObject["validator"]
        bonus = delegateObject["bonusMultiplier"]
        amount = delegateObject["amount"]

        if onlyToBondedValidators:
            if validatorAddress not in BONDED_VALS.keys():
                # print(f"Skipping {delegator} since they are with {validatorAddress} who is unbonded")
                continue

        theirPercentOfAllStaked = float(amount) / totalTokensStakedForChain
        theirAllotment = theirPercentOfAllStaked * CRAFT_ALLOTMENTS[chainName] # how much craft THEY get before bonus

        ACTUAL_ALLOTMENT_GIVEN += theirAllotment # debug actual craft being given

        bonus = float(bonus)
        if bonus > 1.0:                        
            ACTUAL_BONUS_GIVEN += (theirAllotment*bonus) # debug
            theirAllotment = theirAllotment*bonus # just so we can know how much bonus is given out
            # print(f"{theirAllotment} for {theirPercentOfAllStaked} of {totalStakedUTokens[chainName]} with bonus")

        # saving as ucraft for them
        add_airdrop_to_craft_account(str(delegator), theirAllotment * 1_000_000)


    # save the airdrop amounts to the file. Then we can processes
    with open(f"final/group1_{chainName}.json", 'w') as o:
        o.write(json.dumps(craft_airdrop_amounts))


    completionData = f"{chainName} airdrop - ALLOTMENT: {CRAFT_ALLOTMENTS[chainName]}\n"
    completionData += f"GIVEN EXCLUDING BONUS: {ACTUAL_ALLOTMENT_GIVEN} + BONUSES: {ACTUAL_BONUS_GIVEN} = {ACTUAL_ALLOTMENT_GIVEN + ACTUAL_BONUS_GIVEN} TOTAL"

    
    print(completionData)

    output = f"Difference for actuals: {CRAFT_ALLOTMENTS[chainName] - ACTUAL_ALLOTMENT_GIVEN}"
    if onlyToBondedValidators:
        output += f"\n{chainName} airdrop - ONLY TO BONDED VALIDATORS (So the actual given will be less than the total allotment)"
    else:
        output += "(This should be as close to 0 as possible)"

    print(output)
    with open(f"output/airdrop_info/group1_{chainName}.txt", 'w') as o:
        o.write(completionData + '\n' + output)

# TODO: Merge group 5 ION LPs in here too? If so osmosis_get_all_LP_providers needs to add their pools as well
def group2_fairdrop_for_osmosis_pools(osmosisBalances: dict, TOTAL_SUPPLY: dict):
    '''Group #2 - LPs for pool #1 and #561 (luna/osmo)'''

    # filePath = "output/osmosis_balances.json" 
    # FORMAT: poolHolder in file: {"osmoaddress": {"gamm/pool/1": 0, "gamm/pool/561": 0}, {...}}
    # FORMAT: totalSupply in file: {"gamm/pool/1": 0, "gamm/pool/561": 0}
    # totalSupply, poolHolders = osmosis_get_all_LP_providers(filePath)    
    # if totalSupply == {}: # filePath doesn't exist yet
    #     return

    CRAFT_SUPPLY_FOR_POOLS = { 
        "gamm/pool/1": 1_000_000,
        "gamm/pool/561": 1_500_000
    }

    reset_craft_airdrop_temp_dict()

    # DEBUGGING - just to check that this is close to CRAFT_SUPPLY_FOR_POOLS total
    totalCraftGivenActual = { "gamm/pool/1": 0, "gamm/pool/561": 0}

    # accounts = {}

    for address in osmosisBalances.keys():
        coins = osmosisBalances[address]
        # print(coins)

        for coin in coins.keys():
            if coin in ["gamm/pool/1", "gamm/pool/561"]:
                # print(f"{address} has {balance} {coin}")

                # A users LP Token Share
                tokenAmount = int(coins[coin])
                if tokenAmount == 0:
                    continue

                if coin not in TOTAL_SUPPLY:
                    print(f"{coin} not in TOTAL_SUPPLY")
                    exit()

                # decimal percent -> ex 0.00002
                theirPercentOwnership = (tokenAmount / int(TOTAL_SUPPLY[coin])) 

                # (totalSupplyForGivenPool*0.00002) = theirAllotmentOfCraft
                theirCraftAllotment = CRAFT_SUPPLY_FOR_POOLS[coin] * theirPercentOwnership 

                # DEBUG to ensure we are close to giving out ALL of the amount of CRAFT for each pool here
                totalCraftGivenActual[coin] += theirCraftAllotment

                # Saved as ucraft
                add_airdrop_to_craft_account(address, theirCraftAllotment * 1_000_000)


    # save each osmo addresses % of the given pool based on the total supply
    # This will be easier to just do theirPercent*totalCraftSupplyForGroup2 = Their craft
    with open("final/Group2_LP_Pools_Craft_Amounts.json", 'w') as o:
        o.write(json.dumps(craft_airdrop_amounts))

    print(f":::LPs:::\nNumber of unique wallets providing liquidity to #1 & #561: {len(craft_airdrop_amounts)}")

    # print(f"Total craft given: {totalCraftGivenActual=} out of {CRAFT_SUPPLY_FOR_POOLS=}")
    for poolID in CRAFT_SUPPLY_FOR_POOLS.keys():
        print(f"{poolID} Given minus intended: {totalCraftGivenActual[poolID] - CRAFT_SUPPLY_FOR_POOLS[poolID]}")

def group3_atom_relayers(): # cosmos
    '''Group 3: ATOM Relayers, we <3 you!'''
    print(f"Running Group 3 airdrop for atom relayers validators ")

    CRAFT_ALLOTMENTS = 5_000_000

    ACTUAL_ALLOTMENT_GIVEN = 0 

    allCosmosStakers = utils.getOutputFileName("cosmos")

    reset_craft_airdrop_temp_dict()
    # TODO: Redo this section for new values
    for delegator, valaddr, bonus, ustake in utils.yield_staked_values_from_file(allCosmosStakers):
        
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

    CHANDRA_CRAFT_ALLOTMENTS = { # make sure to use the same keys as group6_genesis_set_validators()
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

    reset_craft_airdrop_temp_dict()
  
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

    with open("output/balances/osmosis.json", 'r') as f:
        osmosis_balances = json.loads(f.read())

    reset_craft_airdrop_temp_dict()
    for address in osmosis_balances.keys():
        # print(address, osmosis_balances[address])

        for denom in osmosis_balances[address].keys():

            if denom in CRAFT_ION_ALLOTMENT.keys():  
                balance = float(osmosis_balances[address][denom])
                totalSupply = int(TOTAL_SUPPLY[denom])

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
    reset_craft_airdrop_temp_dict()
                
def group6_genesis_set_validators():
    # Modified version of group1. Only bonus is given (so in group 1 it is 1.05 for example, here you only get 0.05)
    # This means actual given will always be less than the total amount allocated?
    print("\nRunning Group 6 airdrop for genesis set validators")

     # do we reset this for every chain loop in here?

    CRAFT_ALLOTMENTS = { # every other chain excluding the main 4. Use tghe same name as in chains.keys()
        "comdex": 250_000,
        # "stargaze": 500_000,
        # "secret": 500_000,
        # "regen": 500_000,
        # "cronos": 500_000,
        # "desmos": 500_000,
        "dig": 10000,
        # "emoney": 500_000,
        # "gravity": 500_000,
        # "chihuahua": 500_000,
        # "persistance": 500_000,
        # "sentinel": 500_000,
    }

    ACTUAL_ALLOTMENT_GIVEN = {}

    for chain in CRAFT_ALLOTMENTS.keys():
        reset_craft_airdrop_temp_dict()

        if chain not in CHAINS.keys():
            print(f"[!] Chain {chain} is not in CHAINS.keys(). Did you forget to uncomment it?\n")
            continue

        denom = CHAINS[chain]['bonding_token']
        totalTokensStakedForChain = int(TOTAL_STAKED_TOKENS[denom])
        print(f"Craft allotment for {chain} (${denom}): {CRAFT_ALLOTMENTS[chain]}")

        # {"delegator": delegate, "validator": validator, "amount": amount, "bonusMultiplier": bonus}
        for info in utils.yield_staked_values_from_file(f"output/staked/{chain}.json"):               
            delegator = info['delegator']
            valaddr = info['validator']     
            amount = int(info['amount'])
            bonusMultiplier = info['bonusMultiplier']

            if str(delegator).startswith("0x"):
                # if it is a "0x" address (dig) or gravity, we have to save their balance without craft conversion
                # print(delegator + " address can not be converted since its an eth based address")
                pass

            if valaddr not in GENESIS_VALIDATORS.keys():
                continue # we only want people delegated to genesis validators here

            theirPercentOfAllStaked = float(amount) / totalTokensStakedForChain
            # Allotment = theirCraft * bonus (where bonus is just the 1.05-1.00 = 0.05*theirCraft).        
            theirAllotment = (theirPercentOfAllStaked * CRAFT_ALLOTMENTS[chain]) * (bonusMultiplier-1.0)
            
            # print(f"{delegator} %={theirPercentOfAllStaked} theirAllotment={theirAllotment} bonus={bonusMultiplier-1.0}")

            if chain not in ACTUAL_ALLOTMENT_GIVEN:
                ACTUAL_ALLOTMENT_GIVEN[chain] = 0
            ACTUAL_ALLOTMENT_GIVEN[chain] += theirAllotment
            
            add_airdrop_to_craft_account(str(delegator), theirAllotment * 1_000_000)
        
        print(f"ACTUAL_ALLOTMENT_GIVEN={ACTUAL_ALLOTMENT_GIVEN[chain]}craft for {chain}")
    
        # Do it for each 1 or at the very end?
        with open(f"final/group6_staked_{chain}.json", 'w') as o:
            o.write(json.dumps(craft_airdrop_amounts))
            print(f"Saved final final/group6_staked_{chain}.json")

    print(f"Total allotments given for group 6: {ACTUAL_ALLOTMENT_GIVEN}")


def group7_beta_participants():
    TOTAL_ALLOCATION = 500_000

    with open("output/beta_wallets.json", 'r') as f:
        beta_wallets = json.loads(f.read())

    ALLOCATION_PER_WALLET = TOTAL_ALLOCATION/len(beta_wallets)

    for wallet in beta_wallets:
        add_airdrop_to_craft_account(wallet, ALLOCATION_PER_WALLET * 1_000_000)


        


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


 
''' # This func Not required anymore? 
def osmosis_get_all_LP_providers(filePath): # for group 2
    """
    group2_fairdrop_for_osmosis_pools() calls this to get the totalSupply & all poolHolders for 1 & 561.
    Then the group2_fairdrop_for_osmosis_pools() function loops through these values again to get % of the pool
    THEN it dumps to file
    """
     
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
'''

   


if __name__ == "__main__": 
    # run the main logic
    main()