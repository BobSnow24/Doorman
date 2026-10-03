# -*- coding: utf-8 -*-
"""Controllo rapido del riconoscimento delle ricerche:  python test_ricerche.py"""

from core import parola_vietata, testo_cercato

assert testo_cercato("gatti neri - Cerca con Google - Google Chrome") == "gatti neri"
assert testo_cercato("gatti neri - Google Search — Mozilla Firefox") == "gatti neri"
assert testo_cercato("Posta in arrivo - Gmail") is None

parole = ["gatt", "cane lupo"]
assert parola_vietata("Gatti neri", parole) == "gatt"
assert parola_vietata("il CANE LUPO italiano", parole) == "cane lupo"
assert parola_vietata("ingatto", parole) is None        # solo a inizio parola
assert parola_vietata("ricette veloci", parole) is None
assert parola_vietata("qualsiasi", []) is None
print("ok")

# il file hosts scritto col vecchio nome viene ripulito
from core import MARK_END, MARK_START, _senza_blocco
vecchio = ["127.0.0.1 localhost", "# === SAFEGUARDIAN START - non modificare manualmente ===",
           "0.0.0.0 esempio.com", "# === SAFEGUARDIAN END ==="]
assert _senza_blocco(vecchio) == ["127.0.0.1 localhost"]
assert _senza_blocco(["a", MARK_START, "x", MARK_END, "b"]) == ["a", "b"]
print("ok hosts")
