# craft-airdrop

Snapshot tooling to make an export easier to derive balances, staking rewards, etc (Will merge into craft economy once more feature complete)

</br>


Snapshot exports found at: https://reece.sh/exports/


## Example
```
osmosisd export 3500001 2> osmosis_export.json
craftd export 100000 2> craft_export.json

# These can be placed on an nginx server for easy download. Use the following command to generate an index.html file:
#   apt install tree; tree -H '.' -L 1 --noreport --charset utf-8 -P "*.xz" -o index.html 
# After doing so, you can easily download all the files with the main function :)
```

From here you can put the files into the state_exports folder
Ensure you edit airdrop-tools.py main() function to point to the correct files


</br>

### Usage
```
python3 -m pip install ijson requests

# Edit main in airdrop-tools.py to your liking, comment out lines

# Ensure you are in the project directory, then:
python3 airdrop-tools.py
```


</br>

# Notes
##  Group 1: Stakers - %XX
Anyone Staking: (Exclude exchanges)
 - Akash
 - Osmosis
 - Cosmos
 - Juno

<br/>

##  Group 2: Osmo LP'ers: - %XX
Anyone LP'ing:
 - "gamm/pool/1"   # ATOM/OSMO
 - "gamm/pool/561" # OSMO/LUNA

<br/>

##  Group 3: Validators running ATOM Relayers: - %XX
(ATOM_RELAYERS dict in src -> airdrop_data.py)

Confirm the following & add in:
https://twitter.com/SignalSGNL/status/1521384507844091910?s=20&t=7Krj2BWrg5a3N8dHxmTEKA

##  Group 4: Chandra Station Delegators: - %XX
src -> airdrop_data.py -> GENESIS_VALIDATORS have all Chandra addresses.

##  Group 5: ION Holders & ION LPers: - %XX
airdrop-tools.py -> save_balances handles this.
Need to add saving ION LP pool ids as well 
to balance.

##  Group 6: CRAFT Genesis Set: - %XX
src -> airdrop_data.py -> GENESIS_VALIDATORS have all Chandra addresses.
Chandra is apart of this one on top of Group 4 yes?

##  Group 7: CRAFT BETA: - %X
All who participated in the Craft Economy Beta