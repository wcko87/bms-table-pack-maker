# BMS Table Pack Maker
This script is used as a convenient way to bundle a collection of BMS songs from a table and turn it into a song pack.

## Note
Please do not publish packs generated by this program online. The rights to distribute BMS songs are typically held by the original artists.
Unless you have obtained permission from these BMS makers to redistribute their works, generated packs should be for personal use or private distribution only. Please use discretion.

## Usage
1. Enter the path to your beatoraja songdb and the url of the table to make a pack of.
    - The beatoraja songdb is used to locate BMS songs in your local drive to create the pack.
2. Click "**Find Table Songs in DB**".
    - The program displays which charts are missing from your song database, and so won't be included in the generated pack.
3. Click "**Make Table Pack**"
    - This takes the marked BMS's from your local BMS folder and compiles them into a pack in a new folder. (It can take a while to complete)

![image](https://user-images.githubusercontent.com/27341392/174059251-f803c9b7-8add-4a89-ba91-52def00cab9f.png)

## Explanation
- "Find Table Songs in DB" takes the list of charts from the table, and searches for them in the beatoraja songdb.
- If the chart is in the songdb, and the BMS file is indeed present in your PC, it internally records down the path to that BMS.
- It then lists all of the table charts that it could not find in the beatoraja songdb (including those that are in the songdb, but are not present on disk).
- These missing songs will not be included in the generated pack when you click "Make Table Pack".
- "Make Table Pack" takes the BMS song folders that were found and compiles them into a pack in a new folder (in a "packs" subfolder).