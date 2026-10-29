"""Tests mit erfundenen Mitgliedern. Es werden keine echten Daten benutzt.

Die IBANs haben gültige Prüfziffern, gehören aber zu keinem echten Konto
(BLZ 10000000 ist die Bundesbank in Berlin, die Kontonummern sind ausgedacht).
"""
from pathlib import Path

import pandas as pd
import pytest
from lxml import etree

import namikonvi

SCHEMA = Path(__file__).parent / 'schema' / 'pain.008.003.02.xsd'
NS = {'p': 'urn:iso:std:iso:20022:tech:xsd:pain.008.003.02'}

IBAN_MUELLER = 'DE30100000001111111111'
IBAN_SCHMIDT = 'DE80100000002222222222'
IBAN_WEBER   = 'DE33100000003333333333'


def mitglied(nr, vorname, nachname, iban='', status='Aktiv',
             typ='Mitglied', eintritt='15.03.2019', bic=''):
    """Eine Zeile, wie sie im NaMi-Export vorkommt."""
    return {
        'Mitglieds-Nr.': nr,
        'Vorname': vorname,
        'Nachname': nachname,
        'Status': status,
        'Mitgliedstyp': typ,
        'IBAN': iban,
        'BIC/SWIFT': bic,
        'Kontoinhaber': f'Elternteil {nachname}' if iban else '',
        'Eintrittsdatum': eintritt,
        'E-Mail': '',
        'E-Mail Erziehungsberechtigter': '',
        'Stufe/Abteilung': 'Wölflinge',
    }


def lauf(tmp_path, monkeypatch, zeilen):
    """Schreibt die Zeilen als Excel-Datei und startet die Pipeline im Testordner."""
    monkeypatch.chdir(tmp_path)
    pd.DataFrame(zeilen).to_excel(namikonvi.INPUT_DATEI, index=False)
    namikonvi.sepa_pipeline()
    return tmp_path


def lies_xml(ordner):
    return etree.parse(str(ordner / namikonvi.OUTPUT_XML))


STANDARD = [
    mitglied('1001', 'Anna', 'Müller', IBAN_MUELLER),
    mitglied('1002', 'Ben', 'Müller', IBAN_MUELLER),
    mitglied('1003', 'Clara', 'Schmidt', IBAN_SCHMIDT, bic='MARKDEF1100'),
    mitglied('1004', 'David', 'Ohnekonto'),                       # überweist selbst
    mitglied('1005', 'Emil', 'Weber', IBAN_WEBER, status='Inaktiv'),
    mitglied('1006', 'Frida', 'Weber', IBAN_WEBER, typ='Schnuppermitglied'),
]


def test_iban_pruefung():
    assert namikonvi.iban_valide(IBAN_MUELLER)
    assert namikonvi.iban_valide('DE30 1000 0000 1111 1111 11')   # mit Leerzeichen
    assert not namikonvi.iban_valide('DE31100000001111111111')     # Prüfziffer falsch
    assert not namikonvi.iban_valide('DE30')                       # zu kurz


def test_xml_entspricht_dem_schema(tmp_path, monkeypatch):
    ordner = lauf(tmp_path, monkeypatch, STANDARD)
    schema = etree.XMLSchema(etree.parse(str(SCHEMA)))
    xml = lies_xml(ordner)
    assert schema.validate(xml), schema.error_log


def test_nur_aktive_mitglieder_mit_iban_werden_abgebucht(tmp_path, monkeypatch):
    ordner = lauf(tmp_path, monkeypatch, STANDARD)
    ibans = lies_xml(ordner).xpath('//p:DbtrAcct/p:Id/p:IBAN/text()', namespaces=NS)
    assert sorted(ibans) == sorted([IBAN_MUELLER, IBAN_SCHMIDT])


def test_ohne_iban_landet_auf_der_ueberweiserliste(tmp_path, monkeypatch):
    ordner = lauf(tmp_path, monkeypatch, STANDARD)
    liste = pd.read_excel(ordner / namikonvi.OUTPUT_UEBERWEISER, dtype=str)
    assert liste['Nachname'].tolist() == ['Ohnekonto']


def test_haushalt_wird_nur_ueber_die_iban_gebildet(tmp_path, monkeypatch):
    # Zwei Geschwister mit unterschiedlichem Nachnamen, gleiches Konto
    zeilen = [
        mitglied('1001', 'Anna', 'Müller', IBAN_MUELLER),
        mitglied('1008', 'Hanna', 'Müller-Yilmaz', IBAN_MUELLER),
    ]
    ordner = lauf(tmp_path, monkeypatch, zeilen)
    buchungen = lies_xml(ordner).xpath('//p:DrctDbtTxInf', namespaces=NS)
    assert len(buchungen) == 1
    zweck = buchungen[0].xpath('p:RmtInf/p:Ustrd/text()', namespaces=NS)[0]
    assert 'Anna' in zweck and 'Hanna' in zweck


@pytest.mark.parametrize('eintritt', ['', 'unbekannt'])
def test_fehlendes_mandatsdatum_landet_im_fehlerbericht(tmp_path, monkeypatch, eintritt):
    zeilen = [
        mitglied('1001', 'Anna', 'Müller', IBAN_MUELLER),
        mitglied('1003', 'Clara', 'Schmidt', IBAN_SCHMIDT, eintritt=eintritt),
    ]
    ordner = lauf(tmp_path, monkeypatch, zeilen)
    fehler = pd.read_excel(ordner / namikonvi.OUTPUT_FEHLER, dtype=str)
    assert fehler['Nachname'].tolist() == ['Schmidt']
    assert 'Mandatsdatum' in fehler['Fehlergrund'].iloc[0]
    ibans = lies_xml(ordner).xpath('//p:DbtrAcct/p:Id/p:IBAN/text()', namespaces=NS)
    assert ibans == [IBAN_MUELLER]


def test_ungueltige_iban_landet_im_fehlerbericht(tmp_path, monkeypatch):
    zeilen = STANDARD + [mitglied('1007', 'Greta', 'Falsch', 'DE31100000001111111111')]
    ordner = lauf(tmp_path, monkeypatch, zeilen)
    fehler = pd.read_excel(ordner / namikonvi.OUTPUT_FEHLER, dtype=str)
    assert fehler['Nachname'].tolist() == ['Falsch']
    assert 'IBAN ungültig' in fehler['Fehlergrund'].iloc[0]
