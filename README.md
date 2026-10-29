# namikonvipy

Converts a member export from NaMi, the membership database of the German scout
association DPSG, into a SEPA direct debit file (`pain.008.003.02`) for online banking.
I wrote it for the annual membership fee collection of my local scout group.

## What it does

1. Reads the NaMi Excel export (`.xls` as downloaded from NaMi, or `.xlsx`) and keeps only active members (status `Aktiv`, type `Mitglied`).
2. Members who share an IBAN are treated as one household and charged in a single
   debit. If there are two or more children, each pays the reduced sibling fee.
   The amounts are set in the app or in the configuration block.
3. Checks every IBAN with the ISO 7064 mod-97 checksum.
4. Writes three files:
   - `sepa_abbuchung.xml`: the direct debit file for the bank
   - `ueberweiser_finanzen.xlsx`: members without an IBAN, who pay by bank transfer
   - `fehlende_daten.xlsx`: records that could not be processed (invalid IBAN,
     missing mandate date), each with the reason

In our group, two people check the XML before it is uploaded to the bank.

## Usage

Most people in scout groups do not use Python, so there is a small Streamlit app
(`app.py`). On Windows, double-clicking `starten.bat` sets up a virtual environment
on the first run and opens the app in the browser. In the app you upload the export,
review the debits in a table and download the files. The XML download stays disabled
while the club's account details are still placeholders.

Without the app:

```bash
pip install -r requirements.txt
```

1. Fill in the configuration block at the top of `namikonvi.py`
   (creditor ID, account, fees, group name, year).
2. Save the NaMi export as `mitglieder_nami.xls` (or `.xlsx`) next to the script.
3. Run `python namikonvi.py`.

Both use the same function `verarbeite()`. A step-by-step guide in German for other
scout groups is in [Anleitung.md](Anleitung.md).

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

The tests only use invented members. They run the pipeline on a small fake export and
validate the generated XML against the `pain.008.003.02` schema of the German banking
industry (`tests/schema/`). Tested with Python 3.13.

## Data protection

The script runs locally and sends nothing over the network. The app only listens on
`localhost`, and Streamlit's usage statistics are switched off in `.streamlit/config.toml`.
`.gitignore` excludes all `.xls`, `.xlsx` and `.xml` files and the saved app settings, so that
member data cannot be committed by accident.

## License

MIT, see [LICENSE](LICENSE). The schema file in `tests/schema/` is published by the
Deutsche Kreditwirtschaft and is not covered by this license.
