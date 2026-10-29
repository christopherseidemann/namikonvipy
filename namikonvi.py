import pandas as pd
import os
import re
import io
from datetime import date, datetime
from xml.etree import ElementTree as ET

# ==============================================================
# VEREINSDATEN – hier ausfüllen
# ==============================================================
GLAEUBIGER_NAME    = 'DPSG XXX e.V.'
GLAEUBIGER_ID      = 'DE98ZZZ09999999999'     # <-- von deiner Bank
GLAEUBIGER_IBAN    = 'DE00000000000000000000'  # <-- Vereinskonto
GLAEUBIGER_BIC     = 'XXXXXXXX'                # <-- Vereinsbank BIC
FAELLIGKEITSDATUM  = ''   # leer = heute; oder z.B. '2026-06-01'

STAMM_NAME         = 'DPSG Balingen eV'   # steht im Verwendungszweck
MSG_ID_PREFIX      = 'DPSG-BALINGEN'      # Anfang der Message-ID, höchstens 17 Zeichen
BEITRAGSJAHR       = 2026                 # steht im Verwendungszweck

INPUT_DATEI        = 'mitglieder_nami.xlsx'
OUTPUT_XML         = 'sepa_abbuchung.xml'
OUTPUT_UEBERWEISER = 'ueberweiser_finanzen.xlsx'
OUTPUT_FEHLER      = 'fehlende_daten.xlsx'

BEITRAG_ERSTKIND    = 40.0
BEITRAG_GESCHWISTER = 30.0
AKTIV_STATUS        = 'Aktiv'
AKTIV_TYP           = 'Mitglied'
# ==============================================================


def iban_valide(iban):
    iban = iban.replace(' ', '').upper()
    if not re.match(r'^[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}$', iban):
        return False
    rotiert = iban[4:] + iban[:4]
    ziffern = ''.join(str(ord(c) - 55) if c.isalpha() else c for c in rotiert)
    return int(ziffern) % 97 == 1


def berechne_beitrag(anzahl):
    if anzahl == 1:
        return BEITRAG_ERSTKIND
    return anzahl * BEITRAG_GESCHWISTER


def erzeuge_msg_id(zeitpunkt):
    """Message-ID mit Datum und Uhrzeit (sekundengenau).

    Banken lehnen eine Datei ab, deren Message-ID schon einmal benutzt wurde.
    Mit nur dem Datum hätte ein zweiter Lauf am selben Tag dieselbe ID.
    """
    return f"{MSG_ID_PREFIX}-{zeitpunkt.strftime('%Y%m%d%H%M%S')}"


def sub(parent, tag, text=None, **attrib):
    """Hilfsfunktion: SubElement mit optionalem Text und Attributen."""
    el = ET.SubElement(parent, tag, **attrib)
    if text is not None:
        el.text = str(text)
    return el


def build_pain_xml(buchungen, faellig, msg_id):
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
    sub(sub(hdr, n('InitgPty')), n('Nm'), GLAEUBIGER_NAME)

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
    sub(sub(pi, n('Cdtr')), n('Nm'), GLAEUBIGER_NAME)
    sub(sub(sub(pi, n('CdtrAcct')), n('Id')), n('IBAN'), GLAEUBIGER_IBAN)
    sub(sub(sub(pi, n('CdtrAgt')), n('FinInstnId')), n('BIC'), GLAEUBIGER_BIC)
    sub(pi, n('ChrgBr'), 'SLEV')

    # Gläubiger-ID: CdtrSchmeId/Id/PrvtId/Othr mit Id und SchmeNm/Prtry
    othr = sub(sub(sub(sub(pi, n('CdtrSchmeId')), n('Id')), n('PrvtId')), n('Othr'))
    sub(othr, n('Id'), GLAEUBIGER_ID)
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


def sepa_pipeline():
    print("=" * 55)
    print(f"  {STAMM_NAME} – SEPA PIPELINE")
    print("=" * 55)

    if not os.path.exists(INPUT_DATEI):
        print(f"FEHLER: {INPUT_DATEI} nicht gefunden.")
        return

    df = pd.read_excel(INPUT_DATEI, dtype=str)
    df.columns = df.columns.str.strip()
    df = df.fillna('')

    print(f"  Datensätze gesamt: {len(df)}")

    aktiv = df[(df['Status'].str.strip() == AKTIV_STATUS) &
               (df['Mitgliedstyp'].str.strip() == AKTIV_TYP)].copy()
    print(f"  Aktive Mitglieder: {len(aktiv)}")
    print(f"  Herausgefiltert:   {len(df) - len(aktiv)}\n")

    aktiv['IBAN']         = aktiv['IBAN'].str.replace(' ', '').str.upper().str.strip()
    aktiv['Kontoinhaber'] = aktiv['Kontoinhaber'].str.strip()
    aktiv['BIC/SWIFT']    = aktiv['BIC/SWIFT'].str.strip()

    df_lastschrift = aktiv[aktiv['IBAN'].str.len() > 0].copy()
    df_ueberweiser = aktiv[aktiv['IBAN'].str.len() == 0].copy()

    print(f"  → Lastschrift: {len(df_lastschrift)}")
    print(f"  → Überweisung: {len(df_ueberweiser)}\n")

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
        betrag   = berechne_beitrag(len(vornamen))
        vwz      = f"{STAMM_NAME} {BEITRAGSJAHR} {', '.join(vornamen)}"

        buchungen.append({
            'kontoinhaber':     kontoinhaber,
            'iban':             iban,
            'bic':              bic,
            'betrag':           betrag,
            'mandat':           mandat,
            'mandat_datum':     mandat_datum,
            'verwendungszweck': vwz,
        })

    faellig = FAELLIGKEITSDATUM if FAELLIGKEITSDATUM else date.today().strftime('%Y-%m-%d')
    msg_id  = erzeuge_msg_id(datetime.now())

    if buchungen:
        xml_bytes = build_pain_xml(buchungen, faellig, msg_id)
        with open(OUTPUT_XML, 'wb') as f:
            f.write(xml_bytes)
        gesamt = sum(b['betrag'] for b in buchungen)
        print(f"  ✓ SEPA XML: {OUTPUT_XML}")
        print(f"    {len(buchungen)} Buchungen | Gesamtbetrag: {gesamt:.2f} EUR\n")
    else:
        print("  ⚠ Keine gültigen Lastschriften.\n")

    if not df_ueberweiser.empty:
        cols = [c for c in ['Mitglieds-Nr.', 'Vorname', 'Nachname', 'E-Mail',
                'E-Mail Erziehungsberechtigter', 'Stufe/Abteilung']
                if c in df_ueberweiser.columns]
        with pd.ExcelWriter(OUTPUT_UEBERWEISER, engine='openpyxl') as writer:
            df_ueberweiser[cols].to_excel(writer, sheet_name='Überweiser', index=False)
        print(f"  ✓ Überweiser: {OUTPUT_UEBERWEISER} ({len(df_ueberweiser)} Personen)\n")

    if fehler_liste:
        pd.DataFrame(fehler_liste).to_excel(OUTPUT_FEHLER, index=False)
        print(f"  ✓ Fehler: {OUTPUT_FEHLER} ({len(fehler_liste)} Einträge)\n")
    else:
        print("  ✓ Keine fehlerhaften Datensätze.\n")

    print("=" * 55)
    print("  FERTIG")
    print("=" * 55)


if __name__ == '__main__':
    sepa_pipeline()
