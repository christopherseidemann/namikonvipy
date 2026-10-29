"""Oberfläche für namikonvi.py. Start: streamlit run app.py (oder starten.bat)."""
import io
import json
from dataclasses import asdict
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

import namikonvi as nk

EINSTELLUNGEN_DATEI = Path(__file__).parent / 'einstellungen.json'   # nicht auf GitHub (.gitignore)


def lade_einstellungen():
    """Gespeicherte Einstellungen laden, sonst die Werte aus namikonvi.py."""
    if EINSTELLUNGEN_DATEI.exists():
        return nk.Einstellungen(**json.loads(EINSTELLUNGEN_DATEI.read_text(encoding='utf-8')))
    return nk.Einstellungen()


def als_excel(df):
    """DataFrame als Excel-Datei im Speicher, für den Download-Button."""
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    return buf.getvalue()


def euro(betrag):
    """40.0 -> '40,00 €'"""
    return f'{betrag:.2f} €'.replace('.', ',')


def vereinsdaten_fehler(e):
    """Liste der Probleme mit den Vereinsdaten; leer = alles in Ordnung."""
    fehler = []
    if 'XXX' in e.glaeubiger_name:
        fehler.append('Name des Vereins ist noch der Platzhalter.')
    if e.glaeubiger_id == 'DE98ZZZ09999999999':
        fehler.append('Gläubiger-ID ist noch die Test-ID der Bundesbank.')
    if not nk.iban_valide(e.glaeubiger_iban):
        fehler.append('IBAN des Vereinskontos ist ungültig.')
    if 'X' * 8 in e.glaeubiger_bic.upper():
        fehler.append('BIC des Vereinskontos ist noch der Platzhalter.')
    if len(e.msg_id_prefix) > 17:
        fehler.append('Kennung für die Bank ist länger als 17 Zeichen.')
    return fehler


st.set_page_config(page_title='namikonvipy', layout='wide')

# ---------- Seitenleiste: Einstellungen ----------
gespeichert = lade_einstellungen()
with st.sidebar:
    st.header('Einstellungen')
    st.caption('Einmal ausfüllen und speichern. Die Werte bleiben auf diesem Computer.')

    st.subheader('Verein')
    name = st.text_input('Name des Vereins', gespeichert.glaeubiger_name)
    gl_id = st.text_input('Gläubiger-ID', gespeichert.glaeubiger_id)
    iban = st.text_input('IBAN des Vereinskontos', gespeichert.glaeubiger_iban)
    bic = st.text_input('BIC des Vereinskontos', gespeichert.glaeubiger_bic)

    st.subheader('Beiträge pro Kind')
    einzel = st.number_input('Einzelkind (€)', value=gespeichert.beitrag_einzelkind, min_value=0.0, step=5.0)
    geschw = st.number_input('Geschwister, je Kind (€)', value=gespeichert.beitrag_geschwister,
                             min_value=0.0, step=5.0, help='Gilt für jedes Kind, sobald zwei oder mehr vom selben Konto abgebucht werden.')

    st.subheader('Verwendungszweck')
    stamm = st.text_input('Stamm', gespeichert.stamm_name)
    jahr = st.number_input('Beitragsjahr', value=gespeichert.beitragsjahr, step=1)
    prefix = st.text_input('Kennung für die Bank', gespeichert.msg_id_prefix,
                           help='Anfang der Dateikennung, höchstens 17 Zeichen, z. B. DPSG-BALINGEN.')

    e = nk.Einstellungen(
        glaeubiger_name=name.strip(),
        glaeubiger_id=gl_id.strip(),
        glaeubiger_iban=iban.replace(' ', '').upper(),
        glaeubiger_bic=bic.strip().upper(),
        stamm_name=stamm.strip(),
        msg_id_prefix=prefix.strip(),
        beitragsjahr=int(jahr),
        beitrag_einzelkind=einzel,
        beitrag_geschwister=geschw,
    )

    if st.button('Einstellungen speichern'):
        EINSTELLUNGEN_DATEI.write_text(json.dumps(asdict(e), indent=2, ensure_ascii=False), encoding='utf-8')
        st.success('Gespeichert.')

# ---------- Hauptbereich ----------
st.title('namikonvipy')
st.write('Mitgliedsbeiträge per Lastschrift: Aus dem NaMi-Export wird eine SEPA-Datei für das '
         'Online-Banking. Alles läuft auf diesem Computer, es werden keine Daten verschickt.')

st.subheader('1. NaMi-Export hochladen')
datei = st.file_uploader('Excel-Export der Mitglieder aus NaMi (.xls oder .xlsx)', type=['xls', 'xlsx'])
faellig = st.date_input('Abbuchungsdatum', value=date.today() + timedelta(days=3),
                        min_value=date.today(), format='DD.MM.YYYY',
                        help='Die Bank braucht die Datei mindestens einen Bankarbeitstag vorher.')

if datei is None:
    st.info('Sobald ein Export hochgeladen ist, erscheinen hier die Lastschriften zur Prüfung.')
    st.stop()

try:
    export = nk.lies_export(datei)
except Exception:   # beliebiger Lesefehler, z. B. Datei ist keine echte Excel-Datei
    st.error('Die Datei konnte nicht gelesen werden. Bitte in Excel öffnen, '
             'als .xlsx speichern und diese Datei hochladen.')
    st.stop()

try:
    ergebnis = nk.verarbeite(export, e)
except KeyError as fehlende_spalte:
    st.error(f'Die Datei sieht nicht wie ein NaMi-Export aus: Spalte {fehlende_spalte} fehlt.')
    st.stop()

# ---------- Schritt 2: prüfen ----------
st.subheader('2. Prüfen')
a, b, c, d = st.columns(4)
a.metric('Lastschriften', len(ergebnis.buchungen))
b.metric('Summe', euro(ergebnis.gesamtbetrag))
c.metric('Zahlen selbst', len(ergebnis.ueberweiser))
d.metric('Mit Fehler', len(ergebnis.fehler))

tab_ls, tab_ue, tab_fe = st.tabs(['Lastschriften', 'Zahlen selbst', 'Fehler'])
with tab_ls:
    tabelle = pd.DataFrame(ergebnis.buchungen)
    if tabelle.empty:
        st.write('Keine gültigen Lastschriften.')
    else:
        tabelle['betrag'] = tabelle['betrag'].map(euro)
        st.dataframe(
            tabelle[['kontoinhaber', 'iban', 'betrag', 'verwendungszweck', 'mandat', 'mandat_datum']],
            column_config={
                'kontoinhaber': 'Kontoinhaber', 'iban': 'IBAN', 'betrag': 'Betrag',
                'verwendungszweck': 'Verwendungszweck', 'mandat': 'Mandat',
                'mandat_datum': 'Mandat seit',
            },
            hide_index=True)
with tab_ue:
    st.caption('Aktive Mitglieder ohne IBAN. Sie müssen den Beitrag selbst überweisen.')
    st.dataframe(ergebnis.ueberweiser, hide_index=True)
with tab_fe:
    if ergebnis.fehler.empty:
        st.write('Keine fehlerhaften Datensätze.')
    else:
        st.caption('Diese Mitglieder werden nicht abgebucht. Daten in NaMi korrigieren und neu exportieren.')
        spalten = ['Fehlergrund'] + [s for s in ['Vorname', 'Nachname', 'IBAN', 'Eintrittsdatum']
                                     if s in ergebnis.fehler.columns]
        st.dataframe(ergebnis.fehler[spalten], hide_index=True)

# ---------- Schritt 3: herunterladen ----------
st.subheader('3. Herunterladen')
probleme = vereinsdaten_fehler(e)
if probleme:
    st.error('Die SEPA-Datei kann noch nicht erstellt werden. Bitte links in den Einstellungen korrigieren:\n\n'
             + '\n'.join(f'- {p}' for p in probleme))

if ergebnis.buchungen and not probleme:
    xml = nk.build_pain_xml(ergebnis.buchungen, faellig.strftime('%Y-%m-%d'),
                            nk.erzeuge_msg_id(datetime.now(), e.msg_id_prefix), e)
else:
    xml = b''

st.download_button('SEPA-Datei herunterladen', xml, file_name=nk.OUTPUT_XML,
                   mime='application/xml', type='primary', disabled=not xml)
st.caption('Vor dem Hochladen ins Online-Banking von einer zweiten Person prüfen lassen.')

links, rechts = st.columns(2)
links.download_button('Liste „Zahlen selbst“ herunterladen', als_excel(ergebnis.ueberweiser),
                      file_name=nk.OUTPUT_UEBERWEISER, disabled=ergebnis.ueberweiser.empty)
rechts.download_button('Fehlerbericht herunterladen', als_excel(ergebnis.fehler),
                       file_name=nk.OUTPUT_FEHLER, disabled=ergebnis.fehler.empty)
