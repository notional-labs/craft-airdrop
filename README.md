# craft-airdrop

Snapshot tooling to make an export easier to derive balances, staking rewards, etc (Will merge into craft economy once more feature complete)

</br>


Snapshot exports found at: https://reece.sh/exports/


## Example
```
osmosisd export 3500001 2> osmosis_state_export.json
craftd export 100000 2> craft_state_export.json
```

From here you can put the files into the state_exports folder
Ensure you edit airdrop-tools.py main() function to point to the correct files


</br>

### Usage
```
python3 -m pip install ijson requests

# Exit main in airdrop-tools.py to your liking

# Ensure you are in the project directory, then:
python3 airdrop-tools.py
```