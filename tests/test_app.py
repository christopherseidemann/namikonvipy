"""Prüft, dass die Oberfläche ohne Fehler startet (ohne hochgeladene Datei)."""
from streamlit.testing.v1 import AppTest


def test_app_startet_ohne_fehler():
    app = AppTest.from_file('../app.py').run()
    assert not app.exception
    assert 'Sobald ein Export hochgeladen ist' in app.info[0].value
