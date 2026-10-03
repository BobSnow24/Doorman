# -*- coding: utf-8 -*-
"""Widget con angoli tondi per Doorman (tkinter li disegna su Canvas)."""

import tkinter as tk
import tkinter.font as tkfont

# --- palette "portiere d'albergo" -----------------------------------------
# divisa bordeaux, galloni dorati, guanti e marmo color avorio
BG = "#f5efe3"          # avorio
SIDE = "#4a1526"        # bordeaux della divisa
SIDE_SEL = "#5e1d31"
SIDE_FG = "#f5efe3"
SIDE_FG2 = "#c7aeb4"
CARD = "#fffcf6"
CAMPO = "#f5efe3"
BORDO = "#e6d9bf"
FG = "#2a1a14"          # marrone scuro
FG2 = "#7a675a"
FG3 = "#ab9a8a"
ORO = "#c39a3a"         # galloni e bottoni
ORO_TENUE = "#f4e9cf"
BORDEAUX = "#6e1f33"
BORDEAUX_SCURO = "#581827"
OK = "#2f6b4f"          # verde inglese: stato in servizio
OK_TENUE = "#e1ede5"
KO = "#b3362f"
KO_TENUE = "#f8e3df"
GRIGIO = "#eee5d3"
GRIGIO_SCURO = "#e2d6be"

F = "Segoe UI"
SERIF = "Georgia"       # titoli, come l'insegna di un hotel


def tondo(c, x1, y1, x2, y2, r, **kw):
    """Rettangolo con angoli arrotondati di raggio r."""
    r = min(r, (x2 - x1) / 2, (y2 - y1) / 2)
    punti = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
             x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return c.create_polygon(punti, smooth=True, **kw)


class Card(tk.Canvas):
    """Riquadro arrotondato; il contenuto va in self.dentro.

    adatta=True: l'altezza segue il contenuto, altrimenti riempie lo spazio.
    """

    def __init__(self, padre, colore=CARD, sfondo=BG, raggio=18, margine=8,
                 bordo=BORDO, adatta=False):
        # altezza iniziale non minima: un widget fuori dall'area visibile del
        # Canvas non viene mostrato e non riceve <Configure>
        super().__init__(padre, bg=sfondo, highlightthickness=0, bd=0, height=200)
        self.colore, self.raggio, self.margine = colore, raggio, margine
        self.bordo, self.adatta = bordo, adatta
        self.dentro = tk.Frame(self, bg=colore)
        self._win = self.create_window(margine, margine, anchor="nw",
                                       window=self.dentro)
        self.bind("<Configure>", self._ridisegna)
        if adatta:
            self.dentro.bind("<Configure>", lambda e: self.configure(
                height=self.dentro.winfo_reqheight() + 2 * margine))

    def _ridisegna(self, e):
        self.delete("fondo")
        tondo(self, 1, 1, e.width - 2, e.height - 2, self.raggio,
              fill=self.colore, outline=self.bordo or self.colore, tags="fondo")
        self.tag_lower("fondo")
        m = self.margine
        self.itemconfigure(self._win, width=max(1, e.width - 2 * m))
        if not self.adatta:
            self.itemconfigure(self._win, height=max(1, e.height - 2 * m))


class Bottone(tk.Canvas):
    """Bottone a pillola. stile: primario, secondario, pericolo."""

    STILI = {  # sfondo, sfondo al passaggio del mouse, testo
        "primario": (BORDEAUX, BORDEAUX_SCURO, "#f5e6c0"),
        "secondario": (GRIGIO, GRIGIO_SCURO, FG),
        "pericolo": (KO_TENUE, "#fadcdc", KO),
    }

    def __init__(self, padre, testo, comando, stile="primario", sfondo=CARD,
                 grande=False):
        self.font = tkfont.Font(family=F, size=11 if grande else 9, weight="bold")
        self.alto = 46 if grande else 36
        self.comando = comando
        self.attivo = True
        self.sopra = False
        super().__init__(padre, height=self.alto, bg=sfondo,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.bind("<Enter>", lambda e: self._sopra(True))
        self.bind("<Leave>", lambda e: self._sopra(False))
        self.bind("<Button-1>", lambda e: self.attivo and self.comando())
        self.imposta(testo, stile)

    def imposta(self, testo, stile=None):
        self.testo = testo
        self.stile = stile or getattr(self, "stile", "primario")
        self.configure(width=self.font.measure(testo) + (56 if self.alto > 40 else 36))
        self._disegna()

    def abilita(self, si):
        self.attivo = si
        self.configure(cursor="hand2" if si else "arrow")
        self._disegna()

    def _sopra(self, si):
        self.sopra = si
        self._disegna()

    def _disegna(self):
        self.delete("all")
        fondo, fondo_sopra, colore = self.STILI[self.stile]
        if not self.attivo:
            fondo, colore = GRIGIO, FG3
        elif self.sopra:
            fondo = fondo_sopra
        w = int(self["width"])
        tondo(self, 0, 0, w, self.alto, self.alto / 2, fill=fondo, outline="")
        self.create_text(w / 2, self.alto / 2, text=self.testo, fill=colore,
                         font=self.font)


class Interruttore(tk.Canvas):
    """Interruttore on/off; comando() viene chiamato dopo il cambio."""

    def __init__(self, padre, variabile, comando, sfondo=CARD):
        super().__init__(padre, width=42, height=24, bg=sfondo,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.var = variabile
        self.comando = comando
        self.bind("<Button-1>", self._clic)
        self.var.trace_add("write", lambda *a: self._disegna())
        self._disegna()

    def _clic(self, _):
        self.var.set(not self.var.get())
        self.comando()

    def _disegna(self):
        self.delete("all")
        acceso = self.var.get()
        tondo(self, 0, 0, 42, 24, 12, fill=ORO if acceso else GRIGIO_SCURO, outline="")
        x = 30 if acceso else 12
        self.create_oval(x - 9, 3, x + 9, 21, fill="#ffffff", outline="")


def campo_testo(padre, sfondo=CARD):
    """Entry piatta dentro un riquadro arrotondato. Ritorna (contenitore, entry)."""
    box = Card(padre, colore=CAMPO, sfondo=sfondo, raggio=12, margine=6,
               bordo=None, adatta=True)
    entry = tk.Entry(box.dentro, bg=CAMPO, fg=FG, bd=0, relief="flat",
                     insertbackground=FG, font=(F, 10))
    entry.pack(fill="x", padx=8, ipady=4)
    return box, entry
