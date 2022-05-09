import json

fileName = 'final/TESTING_juno.json'
chainAvg = 8400 

with open(fileName, 'r') as f:
    data = json.load(f)

avgs = []
totalWalletOver5000 = 0


overTheAverage = 0

for account in data.keys():
    theirCraftAllocation = sum(data[account])
    # avg
    theirCraftAllocation = theirCraftAllocation / len(data[account])

    if theirCraftAllocation > chainAvg:
        overTheAverage += 1


    avgs.append(theirCraftAllocation)

    totalWalletOver5000 += 1

    # print(f"{account} has an average of {theirCraftAllocation}")


avgOfAvgs = sum(avgs) / len(avgs)
print(f"The average of the avgs is {avgOfAvgs}craft airdrop")
print(f"from totalWalletOver5000: {totalWalletOver5000} for {fileName}")

print(f"{overTheAverage} of the avgs are over the average")