'''
Craft Economy Beta People.
NOT COMPLETED
'''

import utils as utils
import json

craft_airdrop_amounts = {} 
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


def group7_craft_economy_beta_participants():
    with open("crafteconomy_beta_participants.json", 'r') as f:
        beta_participants = json.loads(f.read())
    allotmentPerParticipant = 100
    for wallet in beta_participants:
        add_airdrop_to_craft_account(wallet, 1_000_000)
    pass # Get from MongoDB after we have beta