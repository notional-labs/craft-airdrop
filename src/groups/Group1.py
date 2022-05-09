

import json
import src.utils as utils
import os

def group1_stakers_with_genesis_bonus(chainName, TOTAL_SUPPLY: dict):
    '''Group 1: Stakers and Genesis Bonus for Akash, Osmosis, Cosmos, Juno'''
    print(f"\n\tRunning Group 1  airdrop for {chainName}")

    CRAFT_ALLOTMENTS = {
        "juno": 4_500_000, # 1mil craft for all juno stakers + bonus on top of this
        "akash": 9_000_000, 
        "cosmos": 2_250_000,
        "osmosis": 6_750_000
    }

    DENOMS = { 
        # These are gathered from main file which is done at startup. Just matching chainName -> denom. 
        # Will be required again for the genesis group too.
        "juno": "ujuno",
        "akash": "uakt",
        "cosmos": "uatom",
        "osmosis": "uosmo",
    }

    print(f"Craft allotment for {chainName}: {CRAFT_ALLOTMENTS[chainName]}")

    ACTUAL_ALLOTMENT_GIVEN = 0 # This should be higher since bonuses
    ACTUAL_BONUS_GIVEN = 0

    stake_balance_filename = utils.getOutputFileName(chainName, extension=".txt")

    # check if stake_balance_filename exists
    if not os.path.isfile(stake_balance_filename):
        print(f"{stake_balance_filename} does not exist. Exiting...")
        exit()

    # We want to reset every time since this group is done for all 4 chains
    reset_craft_airdrop_temp_dict()

    # Gets the total supply from startup, while this is not the best it works
    if chainName in DENOMS:
        denom = DENOMS[chainName]
        print(f"Denom: {denom}")
        totalTokensStakedForChain = int(TOTAL_SUPPLY[denom])
        print(f"Total {denom} staked for {chainName}: {totalTokensStakedForChain}.")
    else:
        print(f"[!] Chain name not found. Exiting... {DENOMS=}" )
        exit(1)
    # / End of getting token supply

    for delegator, valaddr, bonus, ustake in utils.yield_staked_values(stake_balance_filename):
        # print(f"{delegator} {valaddr} {bonus} {ustake}")

        theirPercentOfAllStaked = float(ustake) / totalTokensStakedForChain
        theirAllotment = theirPercentOfAllStaked * CRAFT_ALLOTMENTS[chainName] # how much craft THEY get before bonus

        ACTUAL_ALLOTMENT_GIVEN += theirAllotment # debug actual craft being given

        bonus = float(bonus)
        if bonus > 1.0:                        
            ACTUAL_BONUS_GIVEN += (theirAllotment*bonus) # debug

            theirAllotment = theirAllotment*bonus # since we save 1.0 bonuses, we could just do this. For now here to debug
            # print(f"{theirAllotment} for {theirPercentOfAllStaked} of {totalStakedUTokens[chainName]} with bonus")

        # saving as ucraft for them
        add_airdrop_to_craft_account(str(delegator), theirAllotment * 1_000_000)


    # save the airdrop amounts to the file. Then we can processes
    with open(f"final/group1_{chainName}.json", 'w') as o:
        o.write(json.dumps(craft_airdrop_amounts))

    print(f"{chainName} airdrop - ALLOTMENT: {CRAFT_ALLOTMENTS[chainName]}")
    print(f"GIVEN EXCLUDING BONUS: {ACTUAL_ALLOTMENT_GIVEN} + BONUSES: {ACTUAL_BONUS_GIVEN} = {ACTUAL_ALLOTMENT_GIVEN + ACTUAL_BONUS_GIVEN} TOTAL")



# Put this in its own class with custom keys?
# Then we can just dump it to a file
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