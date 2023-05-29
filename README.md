# garmin-notebooks
My personal Jupyter notebooks to analyze my runs, swims, etc....

It uses the [GarminDb](https://github.com/tcgoetz/GarminDB) package and 
a few others packages to summarize and display the data in a jupyter notebook.

## Setup
First install the requirements
```bash
pip install -r requirements.txt
```

Configure [GarminDb](https://github.com/tcgoetz/GarminDB). Set up the user
password and other configs in `~/.GarminDb/GarminConnectConfig.json`

Run the `garmindb.cli` to download and import the latest activities
```bash
garmindb_cli --download --import -al
```

Use the notebook