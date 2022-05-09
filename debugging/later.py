'''
create this tooling to better analze the data.
use matplotlib to plot the data, may require some linear regression? idk
'''

# This was all in Group1.py
'''
    # BIGGEST_WHALE_ACCOUNTS = {}

    # TOTAL_DELEGATED = {}

    # WALLET_BETWEEN_AREAS = {
    #     100: {}, # craft: [amount, amount]
    #     1_000: {},
    #     10_000: {},
    #     100_000: {},
    #     250_000: {},
    #     500_000: {},
    #     1_000_000: {},
    # }   


        # if delegator not in TOTAL_DELEGATED.keys(): # debugging - stats1
        #     TOTAL_DELEGATED[delegator] = 0
        # TOTAL_DELEGATED[delegator] += theirAllotment


    # for user in TOTAL_DELEGATED.keys(): # debugging - stats1
    #     for amt in WALLET_BETWEEN_AREAS.keys():
    #         if TOTAL_DELEGATED[user] < amt:                
    #             WALLET_BETWEEN_AREAS[amt][user] = TOTAL_DELEGATED[user]             
                
        # debugging - stats2
        # if theirAllotment > 5000: # add whale cap?. Avg of all these accounts is 18,600craft allotment. There are 35 over 18,600craft allotment. PER WALLET NOT ENTITY
        #     if delegator not in BIGGEST_WHALE_ACCOUNTS:
        #         BIGGEST_WHALE_ACCOUNTS[delegator] = []
        #     l = list(BIGGEST_WHALE_ACCOUNTS[delegator])
        #     l.append(theirAllotment)
        #     BIGGEST_WHALE_ACCOUNTS[delegator] = l


    # debugging -stats2
    # print(f"{chainName}: len of >5000 {len(BIGGEST_WHALE_ACCOUNTS)}")
    # with open(f"final/TESTING_{chainName}.json", 'w') as o:
    #     o.write(json.dumps(BIGGEST_WHALE_ACCOUNTS))
    # for k in WALLET_BETWEEN_AREAS.keys():
    #     l = len(WALLET_BETWEEN_AREAS[k])
    #     if len(l) > 0: print(k, l)

'''