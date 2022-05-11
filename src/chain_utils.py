import json
import os

import src.utils as utils

def getValidatorInformation(inputFile="exports/chain.json") -> dict:
    print(f"Fetching validator info for {inputFile}")
    validators = utils.stream_section(inputFile, "validators_info") # Should we just load this directly?
    vs = {}
    for idx, validator in validators:
        ''' Example keys:
        {'commission': {'commission_rates': {'max_change_rate': '0.010000000000000000', 'max_rate': '0.200000000000000000', 'rate': '0.050000000000000000'}, 
        'update_time': '2021-08-04T06:44:22.108904074Z'}, 
        'consensus_pubkey': {'@type': '/cosmos.crypto.ed25519.PubKey', 'key': '57x1nniP/cy4Dw1v0Akn2A3f6mSdhvl121U+oIU378Q='}, 
        'delegator_shares': '1000010.000000000000000000', 'description': {'details': 'Staking like a beast!', 'identity': '', 'moniker': 'stakebeast', 'security_contact': '', 'website': ''}, 
        'jailed': False, 'min_self_delegation': '1', 'operator_address': 'osmovaloper1qyksxgv03ngylanwzh2mx6k768frgjc0em6800', 
        'status': 'BOND_STATUS_UNBONDED', 'tokens': '1000010', 'unbonding_height': '0', 'unbonding_time': '1970-01-01T00:00:00Z'}
        '''
        vs[validator['operator_address']] = validator
    return vs


def getBondedValidators(chainName, export_file="exports/chain.json", debug=False):  
    validatorCacheFile = f"output/validators/{chainName}.json"

    if os.path.isfile(validatorCacheFile):
        with open(validatorCacheFile, 'r') as f:
            print(f"Loading validators from cache for {chainName}")
            return json.load(f)
    
    _bondedValidators = {}  
    vals = getValidatorInformation(export_file)  
    for v in vals.keys():
        v = vals[v]
        status = v['status']
        if debug and status not in ['BOND_STATUS_UNBONDED', 'BOND_STATUS_BONDED']:
            print(status)
            
        if status == 'BOND_STATUS_UNBONDED':
            continue
        _bondedValidators[v['operator_address']] = v   

    with open(validatorCacheFile, 'w') as f:
        f.write(json.dumps(_bondedValidators))
        
    return _bondedValidators