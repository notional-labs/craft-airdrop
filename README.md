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