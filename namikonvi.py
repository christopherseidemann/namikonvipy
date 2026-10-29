import pandas as pd
import os
import re
import io
from dataclasses import dataclass
from datetime import date, datetime
from xml.etree import ElementTree as ET

# ==============================================================
# VEREINSDATEN – hier ausfüllen (gilt für den Start per Kommandozeile;
# in der App werden die Werte im Bereich "Einstellungen" eingetragen)
# ==============================================================
GLAEUBIGER_NAME    = 'DPSG XXX e.V.'
GLAEUBIGER_ID      = 'DE98ZZZ09999999999'     # <-- von deiner Bank
GLAEUBIGER_IBAN    = 'DE00000000000000000000'  # <-- Vereinskonto
GLAEUBIGER_BIC     = 'XXXXXXXX'                # <-- Vereinsbank BIC
FAELLIGKEITSDATUM  = ''   # leer = heute; oder z.B. '2026-06-01'

STAMM_NAME         = 'DPSG Balingen eV'   # steht im Verwendungszweck
MSG_ID_PREFIX      = 'DPSG-BALINGEN'      # Anfang der Message-ID, höchstens 17 Zeichen
BEITRAGSJAHR       = 2026                 # steht im Verwendungszweck

# Jahresbeitrag in Euro pro Kind
BEITRAG_EINZELKIND  = 40.0  # nur ein Kind im Haushalt
BEITRAG_GESCHWISTER = 30.0  # ab zwei Kindern, gilt dann für jedes Kind

INPUT_DATEI        = 'mitglieder_nami.xlsx'
OUTPUT_XML         = 'sepa_abbuchung.xml'
OUTPUT_UEBERWEISER = 'ueberweiser_finanzen.xlsx'
OUTPUT_FEHLER      = 'fehlende_daten.xlsx'

AKTIV_STATUS       = 'Aktiv'
AKTIV_TYP          = 'Mitglied'
# ==============================================================


@dataclass
class Einstellungen:
    """Alle Werte, die ein Stamm anpassen muss. Standard: der Block oben."""
    glaeubiger_name:     str   = GLAEUBIGER_NAME
    glaeubiger_id:       str   = GLAEUBIGER_ID
    glaeubiger_iban:     str   = GLAEUBIGER_IBAN
    glaeubiger_bic:      str   = GLAEUBIGER_BIC
    stamm_name:          str   = STAMM_NAME
    msg_id_prefix:       str   = MSG_ID_PREFIX
    beitragsjahr:        int   = BEITRAGSJAHR
    beitrag_einzelkind:  float = BEITRAG_EINZELKIND
    beitrag_geschwister: float = BEITRAG_GESCHWISTER


@dataclass
class Ergebnis:
    """Was bei der Verarbeitung herauskommt, noch ohne Dateien."""
    buchungen:  list              # eine Lastschrift pro Haushalt
    ueberweiser: pd.DataFrame     # aktive Mitglieder ohne IBAN
    fehler:     pd.DataFrame      # nicht verarbeitbar, mit Spalte 'Fehlergrund'
    anzahl_gesamt: int = 0
    anzahl_aktiv:  int = 0

    @property
    def gesamtbetrag(self):
        return sum(b['betrag'] for b in self.buchungen)


def iban_valide(iban):
    iban = iban.replace(' ', '').upper()
    if not re.match(r'^[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}$', iban):
        return False
    rotiert = iban[4:] + iban[:4]
    ziffern = ''.join(str(ord(c) - 55) if c.isalpha() else c for c in rotiert)
    return int(ziffern) % 97 == 1


def berechne_beitrag(anzahl, e):
    """Ein Kind zahlt den Einzelbeitrag, bei Geschwistern zahlt jedes Kind den Geschwisterbeitrag."""
    if anzahl == 1:
        return e.beitrag_einzelkind
    return anzahl * e.beitrag_geschwister


def erzeuge_msg_id(zeitpunkt, prefix):
    """Message-ID mit Datum und Uhrzeit (sekundengenau).

    Banken lehnen eine Datei ab, deren Message-ID schon einmal benutzt wurde.
    Mit nur dem Datum hätte ein zweiter Lauf am selben Tag dieselbe ID.
    """
    return f"{prefix}-{zeitpunkt.strftime('%Y%m%d%H%M%S')}"


def sub(parent, tag, text=None, **attrib):
    """Hilfsfunktion: SubElement mit optionalem Text und Attributen."""
    el = ET.SubElement(parent, tag, **attrib)
    if text is not None:
        el.text = str(text)
    return el


def build_pain_xml(buchungen, faellig, msg_id, e):
    """Erzeugt pain.008.003.02 XML als UTF-8 bytes."""
    NS = 'urn:iso:std:iso:20022:tech:xsd:pain.008.003.02'
    ET.register_namespace('', NS)

    gesamt = sum(b['betrag'] for b in buchungen)

    root = ET.Element(
        f'{{{NS}}}Document',
        {'{http://www.w3.org/2001/XMLSchema-instance}schemaLocation':
         f'{NS} pain.008.003.02.xsd'}
    )
    ET.register_namespace('xsi', 'http://www.w3.org/2001/XMLSchema-instance')

    def n(tag):
        return f'{{{NS}}}{tag}'

    doc = sub(root, n('CstmrDrctDbtInitn'))

    # GrpHdr
    hdr = sub(doc, n('GrpHdr'))
    sub(hdr, n('MsgId'),    msg_id)
    sub(hdr, n('CreDtTm'),  datetime.now().strftime('%Y-%m-%dT%H:%M:%S'))
    sub(hdr, n('NbOfTxs'),  str(len(buchungen)))
    sub(hdr, n('CtrlSum'),  f'{gesamt:.2f}')
    sub(sub(hdr, n('InitgPty')), n('Nm'), e.glaeubiger_name)

    # PmtInf
    pi = sub(doc, n('PmtInf'))
    sub(pi, n('PmtInfId'), msg_id + '-PI')
    sub(pi, n('PmtMtd'),   'DD')
    sub(pi, n('BtchBookg'),'true')
    sub(pi, n('NbOfTxs'),  str(len(buchungen)))
    sub(pi, n('CtrlSum'),  f'{gesamt:.2f}')

    pti = sub(pi, n('PmtTpInf'))
    sub(sub(pti, n('SvcLvl')),    n('Cd'), 'SEPA')
    sub(sub(pti, n('LclInstrm')), n('Cd'), 'CORE')
    sub(pti, n('SeqTp'), 'OOFF')

    sub(pi, n('ReqdColltnDt'), faellig)
    sub(sub(pi, n('Cdtr')), n('Nm'), e.glaeubiger_name)
    sub(sub(sub(pi, n('CdtrAcct')), n('Id')), n('IBAN'), e.glaeubiger_iban)
    sub(sub(sub(pi, n('CdtrAgt')), n('FinInstnId')), n('BIC'), e.glaeubiger_bic)
    sub(pi, n('ChrgBr'), 'SLEV')

    # Gläubiger-ID: CdtrSchmeId/Id/PrvtId/Othr mit Id und SchmeNm/Prtry
    othr = sub(sub(sub(sub(pi, n('CdtrSchmeId')), n('Id')), n('PrvtId')), n('Othr'))
    sub(othr, n('Id'), e.glaeubiger_id)
    sub(sub(othr, n('SchmeNm')), n('Prtry'), 'SEPA')

    # Einzelbuchungen
    for b in buchungen:
        tx = sub(pi, n('DrctDbtTxInf'))
        sub(sub(tx, n('PmtId')), n('EndToEndId'), 'ID' + b['mandat'])
        sub(tx, n('InstdAmt'), f"{b['betrag']:.2f}", Ccy='EUR')

        ddt = sub(tx, n('DrctDbtTx'))
        mri = sub(ddt, n('MndtRltdInf'))
        sub(mri, n('MndtId'),    b['mandat'])
        sub(mri, n('DtOfSgntr'), b['mandat_datum'])

        fin = sub(sub(tx, n('DbtrAgt')), n('FinInstnId'))
        if b['bic']:
            sub(fin, n('BIC'), b['bic'])
        else:
            # Ohne BIC sieht das Schema Othr/Id = NOTPROVIDED vor, nicht BIC = NOTPROVIDED
            sub(sub(fin, n('Othr')), n('Id'), 'NOTPROVIDED')
        sub(sub(tx, n('Dbtr')), n('Nm'), b['kontoinhaber'])
        sub(sub(sub(tx, n('DbtrAcct')), n('Id')), n('IBAN'), b['iban'])
        sub(sub(tx, n('RmtInf')), n('Ustrd'), b['verwendungszweck'])

    ET.indent(root, space='  ')
    buf = io.BytesIO()
    ET.ElementTree(root).write(buf, xml_declaration=True, encoding='UTF-8')
    return buf.getvalue()


def lies_export(quelle):
    """Liest den NaMi-Export. quelle = Dateipfad oder hochgeladene Datei."""
    df = pd.read_excel(quelle, dtype=str)
    df.columns = df.columns.str.strip()
    return df.fillna('')


def verarbeite(df, e):
    """Teilt die Mitglieder auf und bildet die Buchungen. Schreibt keine Dateien."""
    aktiv = df[(df['Status'].str.strip() == AKTIV_STATUS) &
               (df['Mitgliedstyp'].str.strip() == AKTIV_TYP)].copy()

    aktiv['IBAN']         = aktiv['IBAN'].str.replace(' ', '').str.upper().str.strip()
    aktiv['Kontoinhaber'] = aktiv['Kontoinhaber'].str.strip()
    aktiv['BIC/SWIFT']    = aktiv['BIC/SWIFT'].str.strip()

    df_lastschrift = aktiv[aktiv['IBAN'].str.len() > 0].copy()
    df_ueberweiser = aktiv[aktiv['IBAN'].str.len() == 0].copy()

    mitglieds_nr_col = [c for c in aktiv.columns if 'Mitglieds-Nr' in c][0]
    fehler_liste = []
    buchungen = []

    # Ein Haushalt = alle Mitglieder, die vom selben Konto abgebucht werden.
    # Der Nachname zählt nicht, weil Geschwister verschiedene Nachnamen haben können.
    for iban, gruppe in df_lastschrift.groupby('IBAN'):
        if not iban_valide(iban):
            for _, row in gruppe.iterrows():
                r = row.to_dict(); r['Fehlergrund'] = f'IBAN ungültig: {iban}'
                fehler_liste.append(r)
            continue

        kontoinhaber = gruppe['Kontoinhaber'].iloc[0]
        bic          = gruppe['BIC/SWIFT'].iloc[0]
        mandat       = gruppe[mitglieds_nr_col].iloc[0]

        # Das Datum der Mandatsunterschrift ist Pflicht. Fehlt es, kommt der
        # Haushalt in den Fehlerbericht, statt mit einem erfundenen Datum abgebucht zu werden.
        eintritt = gruppe['Eintrittsdatum'].iloc[0]
        datum = pd.to_datetime(eintritt, dayfirst=True, errors='coerce')  # unlesbar -> NaT
        if pd.isna(datum):
            for _, row in gruppe.iterrows():
                r = row.to_dict(); r['Fehlergrund'] = f'Mandatsdatum fehlt oder ungültig: "{eintritt}"'
                fehler_liste.append(r)
            continue
        mandat_datum = datum.strftime('%Y-%m-%d')

        vornamen = gruppe['Vorname'].tolist()
        betrag   = berechne_beitrag(len(vornamen), e)
        vwz      = f"{e.stamm_name} {e.beitragsjahr} {', '.join(vornamen)}"

        buchungen.append({
            'kontoinhaber':     kontoinhaber,
            'iban':             iban,
            'bic':              bic,
            'betrag':           betrag,
            'mandat':           mandat,
            'mandat_datum':     mandat_datum,
            'verwendungszweck': vwz,
        })

    cols = [c for c in ['Mitglieds-Nr.', 'Vorname', 'Nachname', 'E-Mail',
            'E-Mail Erziehungsberechtigter', 'Stufe/Abteilung']
            if c in df_ueberweiser.columns]

    return Ergebnis(
        buchungen=buchungen,
        ueberweiser=df_ueberweiser[cols],
        fehler=pd.DataFrame(fehler_liste),
        anzahl_gesamt=len(df),
        anzahl_aktiv=len(aktiv),
    )


def sepa_pipeline():
    """Start per Kommandozeile: liest INPUT_DATEI und schreibt die drei Ausgabedateien."""
    e = Einstellungen()
    print("=" * 55)
    print(f"  {e.stamm_name} – SEPA PIPELINE")
    print("=" * 55)

    if not os.path.exists(INPUT_DATEI):
        print(f"FEHLER: {INPUT_DATEI} nicht gefunden.")
        return

    ergebnis = verarbeite(lies_export(INPUT_DATEI), e)
    print(f"  Datensätze gesamt: {ergebnis.anzahl_gesamt}")
    print(f"  Aktive Mitglieder: {ergebnis.anzahl_aktiv}\n")

    faellig = FAELLIGKEITSDATUM if FAELLIGKEITSDATUM else date.today().strftime('%Y-%m-%d')
    msg_id  = erzeuge_msg_id(datetime.now(), e.msg_id_prefix)

    if ergebnis.buchungen:
        with open(OUTPUT_XML, 'wb') as f:
            f.write(build_pain_xml(ergebnis.buchungen, faellig, msg_id, e))
        print(f"  ✓ SEPA XML: {OUTPUT_XML}")
        print(f"    {len(ergebnis.buchungen)} Buchungen | Gesamtbetrag: {ergebnis.gesamtbetrag:.2f} EUR\n")
    else:
        print("  ⚠ Keine gültigen Lastschriften.\n")

    if not ergebnis.ueberweiser.empty:
        with pd.ExcelWriter(OUTPUT_UEBERWEISER, engine='openpyxl') as writer:
            ergebnis.ueberweiser.to_excel(writer, sheet_name='Überweiser', index=False)
        print(f"  ✓ Überweiser: {OUTPUT_UEBERWEISER} ({len(ergebnis.ueberweiser)} Personen)\n")

    if not ergebnis.fehler.empty:
        ergebnis.fehler.to_excel(OUTPUT_FEHLER, index=False)
        print(f"  ✓ Fehler: {OUTPUT_FEHLER} ({len(ergebnis.fehler)} Einträge)\n")
    else:
        print("  ✓ Keine fehlerhaften Datensätze.\n")

    print("=" * 55)
    print("  FERTIG")
    print("=" * 55)


if __name__ == '__main__':
    sepa_pipeline()
