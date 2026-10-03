# -*- coding: utf-8 -*-
"""Doorman - interfaccia grafica.

Avvio normale:      python app.py
Avvio automatico:   python app.py --avvio     (riapplica le protezioni e resta in background)
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog

import core
from ui import (BG, BORDO, CAMPO, CARD, F, FG, FG2, FG3, KO, KO_TENUE, OK,
                OK_TENUE, SIDE, Bottone, Card, Interruttore, campo_testo, tondo)


class DoormanApp(tk.Tk):

    def __init__(self, avvio_silenzioso=False):
        super().__init__()
        self.cfg = core.carica_config()
        self.sorveglianza = None
        self.pagine = {}
        self.nav = {}

        self.title("%s %s" % (core.APP_NAME, core.VERSIONE))
        self.geometry("1060x740")
        self.minsize(980, 700)
        self.configure(bg=BG)

        self._barra_laterale()
        self._area()
        self.protocol("WM_DELETE_WINDOW", self._chiudi)

        self._avvia_sorveglianza()
        self._mostra("stato")
        self._aggiorna_stato()

        if avvio_silenzioso:
            if self.cfg.get("protezione_attiva"):
                threading.Thread(target=self._riapplica, daemon=True).start()
            self.after(400, self.withdraw)

    # =================================================== struttura
    PAGINE = (("stato", "Stato"), ("siti", "Siti bloccati"),
              ("ricerche", "Ricerche"), ("programmi", "Programmi"),
              ("registro", "Registro"), ("impostazioni", "Impostazioni"))

    def _barra_laterale(self):
        side = tk.Frame(self, bg=SIDE, width=220)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        tk.Frame(self, bg=BORDO, width=1).pack(side="left", fill="y")

        marchio = tk.Frame(side, bg=SIDE)
        marchio.pack(fill="x", pady=(28, 32), padx=22)
        self.logo = tk.Canvas(marchio, width=32, height=36, bg=SIDE,
                              highlightthickness=0)
        self.logo.pack(side="left")
        testo = tk.Frame(marchio, bg=SIDE)
        testo.pack(side="left", padx=(12, 0))
        tk.Label(testo, text="Doorman", bg=SIDE, fg=FG,
                 font=(F, 13, "bold")).pack(anchor="w")
        tk.Label(testo, text="Protezione famiglia", bg=SIDE, fg=FG3,
                 font=(F, 8)).pack(anchor="w")

        for chiave, etichetta in self.PAGINE:
            voce = tk.Canvas(side, height=40, bg=SIDE, highlightthickness=0,
                             cursor="hand2")
            voce.pack(fill="x", padx=14, pady=2)
            voce.etichetta = etichetta
            voce.bind("<Button-1>", lambda e, k=chiave: self._mostra(k))
            voce.bind("<Configure>", lambda e, k=chiave: self._disegna_voce(k))
            self.nav[chiave] = voce

        tk.Label(side, text="versione %s" % core.VERSIONE, bg=SIDE, fg=FG3,
                 font=(F, 8)).pack(side="bottom", pady=18)

    def _disegna_voce(self, chiave):
        voce = self.nav[chiave]
        attiva = chiave == getattr(self, "pagina", None)
        voce.delete("all")
        if attiva:
            tondo(voce, 0, 0, voce.winfo_width(), 40, 20, fill=OK_TENUE, outline="")
        voce.create_text(20, 20, text=voce.etichetta, anchor="w",
                         fill=OK if attiva else FG2,
                         font=(F, 10, "bold" if attiva else "normal"))

    def _area(self):
        destra = tk.Frame(self, bg=BG)
        destra.pack(side="left", fill="both", expand=True)

        # --- intestazione: riquadro grande con scudo di stato
        testa = Card(destra, raggio=24, margine=18, adatta=True)
        testa.pack(fill="x", padx=28, pady=(26, 18))
        riga = testa.dentro

        self.anello = tk.Canvas(riga, width=84, height=84, bg=CARD,
                                highlightthickness=0)
        self.anello.pack(side="left", padx=(6, 0))

        blocco = tk.Frame(riga, bg=CARD)
        blocco.pack(side="left", padx=(20, 0))
        self.lbl_stato = tk.Label(blocco, text="", bg=CARD, fg=FG,
                                  font=(F, 19, "bold"), anchor="w")
        self.lbl_stato.pack(anchor="w")
        self.lbl_dett = tk.Label(blocco, text="", bg=CARD, fg=FG2, font=(F, 9),
                                 anchor="w", justify="left", wraplength=420)
        self.lbl_dett.pack(anchor="w", pady=(4, 0))

        self.btn_toggle = Bottone(riga, "", self._toggle_protezione, grande=True)
        self.btn_toggle.pack(side="right", padx=(0, 8))

        self.contenitore = tk.Frame(destra, bg=BG)
        self.contenitore.pack(fill="both", expand=True, padx=28, pady=(0, 26))

        costruttori = {"stato": self._pag_stato, "siti": self._pag_siti,
                       "ricerche": self._pag_ricerche,
                       "programmi": self._pag_programmi,
                       "registro": self._pag_registro,
                       "impostazioni": self._pag_impostazioni}
        for chiave, _ in self.PAGINE:
            p = tk.Frame(self.contenitore, bg=BG)
            p.place(relwidth=1, relheight=1)
            costruttori[chiave](p)
            self.pagine[chiave] = p

        self._ricarica_liste()

    def _mostra(self, chiave):
        self.pagina = chiave
        self.pagine[chiave].tkraise()
        for k in self.nav:
            self._disegna_voce(k)
        if chiave == "registro":
            self._ricarica_log()

    # =================================================== grafica stato
    @staticmethod
    def _scudo(c, x, y, s, colore):
        """Scudo arrotondato largo s*2, con vertice in (x, y)."""
        # punti doppi = spigolo vivo (spalle e punta), gli altri vengono smussati
        punti = [x, y, x + s, y + s * .3, x + s, y + s * .3, x + s, y + s,
                 x, y + s * 2.1, x, y + s * 2.1, x - s, y + s,
                 x - s, y + s * .3, x - s, y + s * .3]
        return c.create_polygon(punti, smooth=True, fill=colore, outline="")

    def _disegna_anello(self, attiva):
        c = self.anello
        c.delete("all")
        colore = OK if attiva else KO
        c.create_oval(2, 2, 82, 82, fill=OK_TENUE if attiva else KO_TENUE, outline="")
        self._scudo(c, 42, 16, 21, colore)
        if attiva:
            c.create_line(33, 42, 40, 49, 52, 36, fill="#ffffff", width=4,
                          capstyle="round", joinstyle="round")
        else:
            c.create_line(36, 36, 48, 48, fill="#ffffff", width=4, capstyle="round")
            c.create_line(48, 36, 36, 48, fill="#ffffff", width=4, capstyle="round")

        s = self.logo
        s.delete("all")
        self._scudo(s, 16, 2, 14, colore)

    # =================================================== pagina: stato
    def _pag_stato(self, p):
        barra = tk.Frame(p, bg=BG)
        barra.pack(fill="x", pady=(0, 12))
        self.btn_scan = Bottone(barra, "Avvia scansione", self._scansiona, sfondo=BG)
        self.btn_scan.pack(side="left")
        self.lbl_scan = tk.Label(barra, text="", bg=BG, fg=FG2, font=(F, 9))
        self.lbl_scan.pack(side="left", padx=16)

        self.barra_avanz = tk.Canvas(p, height=6, bg=BG, highlightthickness=0)
        self.barra_avanz.pack(fill="x", pady=(0, 14))

        box = self._card(p, "Esito della scansione")
        box.pack(fill="both", expand=True)
        self.esiti = tk.Text(box.dentro, bg=CARD, fg=FG, bd=0, font=(F, 10),
                             padx=14, pady=4, wrap="word", state="disabled",
                             highlightthickness=0, spacing1=2)
        self.esiti.pack(fill="both", expand=True, pady=(0, 8))
        for tag, col in (("ok", OK), ("ko", KO), ("tit", FG), ("info", FG2)):
            self.esiti.tag_configure(tag, foreground=col)
        self.esiti.tag_configure("tit", font=(F, 10, "bold"))
        self._scrivi_esiti([("Premi \"Avvia scansione\" per controllare le protezioni.",
                             None, "")])

    def _avanzamento(self, frazione):
        c = self.barra_avanz
        c.delete("all")
        w = c.winfo_width()
        tondo(c, 0, 0, w, 6, 3, fill=BORDO, outline="")
        tondo(c, 0, 0, max(6, int(w * frazione)), 6, 3, fill=OK, outline="")

    def _scrivi_esiti(self, righe):
        self.esiti.configure(state="normal")
        self.esiti.delete("1.0", "end")
        for voce, esito, dettaglio in righe:
            if esito is None:
                self.esiti.insert("end", voce + "\n", "info")
                continue
            self.esiti.insert("end", "  ●  " , "ok" if esito else "ko")
            self.esiti.insert("end", voce + "\n", "tit")
            self.esiti.insert("end", "       " + dettaglio + "\n\n", "info")
        self.esiti.configure(state="disabled")

    def _scansiona(self):
        self.btn_scan.abilita(False)
        self._scrivi_esiti([("Scansione in corso...", None, "")])

        fasi = ["Controllo file hosts...", "Verifica ricerca protetta...",
                "Analisi configurazione DNS...", "Controllo policy dei browser...",
                "Verifica protezione dei file...", "Controllo delle ricerche...",
                "Scansione processi attivi...",
                "Controllo avvio automatico..."]

        def avanza(i=0):
            if i < len(fasi):
                self.lbl_scan.configure(text=fasi[i])
                self._avanzamento((i + 1) / len(fasi))
                self.after(260, lambda: avanza(i + 1))

        def lavoro():
            risultati = core.scansione(self.cfg)
            self.after(len(fasi) * 260, lambda: fine(risultati))

        def fine(risultati):
            problemi = [r for r in risultati if not r[1]]
            testa = ("Scansione completata: nessun problema rilevato."
                     if not problemi else
                     "Scansione completata: %d avvisi da controllare." % len(problemi))
            self._scrivi_esiti([(testa, None, "")] + risultati)
            self.lbl_scan.configure(text="")
            self._avanzamento(1)
            self.btn_scan.abilita(True)
            self._aggiorna_stato()

        avanza()
        threading.Thread(target=lavoro, daemon=True).start()

    # =================================================== pagina: siti
    def _pag_siti(self, p):
        sx = self._card(p, "Siti bloccati in piu'",
                        "oltre ai %d domini predefiniti" % len(core.blocklist.SITI_ADULTI))
        sx.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self.lst_siti = self._lista(sx)
        self._riga_input(sx, self._aggiungi_sito,
                         lambda: self._rimuovi(self.lst_siti, "siti_extra"))

        dx = self._card(p, "Eccezioni", "siti sempre permessi")
        dx.pack(side="left", fill="both", expand=True, padx=(8, 0))
        self.lst_perm = self._lista(dx)
        self._riga_input(dx, self._aggiungi_permesso,
                         lambda: self._rimuovi(self.lst_perm, "siti_consentiti"))

    def _aggiungi_sito(self, valore):
        d = core.normalizza(valore)
        if d and d not in self.cfg["siti_extra"]:
            self.cfg["siti_extra"].append(d)
            self._salva_e_riapplica("Sito aggiunto alla lista di blocco: %s" % d)

    def _aggiungi_permesso(self, valore):
        d = core.normalizza(valore)
        if d and d not in self.cfg["siti_consentiti"]:
            self.cfg["siti_consentiti"].append(d)
            self._salva_e_riapplica("Eccezione aggiunta: %s" % d)

    # =================================================== pagina: ricerche
    def _pag_ricerche(self, p):
        box = self._card(p, "Parole vietate nelle ricerche",
                         "Google, Bing, DuckDuckGo, YouTube: la scheda viene chiusa")
        box.pack(fill="both", expand=True)
        self.lst_parole = self._lista(box)
        self._riga_input(box, self._aggiungi_parola,
                         lambda: self._rimuovi(self.lst_parole, "parole_ricerca"),
                         segnaposto="parola o frase")

    def _aggiungi_parola(self, valore):
        parola = " ".join(valore.lower().split())
        if parola and parola not in self.cfg["parole_ricerca"]:
            self.cfg["parole_ricerca"].append(parola)
            self._salva_e_riapplica("Parola aggiunta al controllo ricerche: %s" % parola,
                                    riapplica=False)

    # =================================================== pagina: programmi
    def _pag_programmi(self, p):
        box = self._card(p, "Programmi bloccati",
                         "controllati di continuo e chiusi automaticamente")
        box.pack(fill="both", expand=True)
        self.lst_prog = self._lista(box)
        self._riga_input(box, self._aggiungi_programma,
                         lambda: self._rimuovi(self.lst_prog, "programmi"),
                         segnaposto="nome.exe")

    def _aggiungi_programma(self, valore):
        nome = valore.strip().lower()
        if nome and not nome.endswith(".exe"):
            nome += ".exe"
        if nome and nome not in self.cfg["programmi"]:
            self.cfg["programmi"].append(nome)
            self._salva_e_riapplica("Programma aggiunto alla lista: %s" % nome,
                                    riapplica=False)

    # =================================================== pagina: registro
    def _pag_registro(self, p):
        barra = tk.Frame(p, bg=BG)
        barra.pack(fill="x", pady=(0, 12))
        Bottone(barra, "Aggiorna", self._ricarica_log, sfondo=BG).pack(side="left")
        Bottone(barra, "Apri cartella dati", self._apri_cartella, "secondario",
                sfondo=BG).pack(side="left", padx=8)

        box = self._card(p, "Attivita' registrata")
        box.pack(fill="both", expand=True)
        self.txt_log = tk.Text(box.dentro, bg=CARD, fg=FG2, bd=0, font=("Consolas", 9),
                               padx=14, pady=4, wrap="none", state="disabled",
                               highlightthickness=0)
        self.txt_log.pack(fill="both", expand=True, pady=(0, 8))
        self._ricarica_log()

    def _ricarica_log(self):
        self.txt_log.configure(state="normal")
        self.txt_log.delete("1.0", "end")
        righe = core.leggi_log()
        self.txt_log.insert("end", "".join(righe) if righe
                            else "Nessuna attivita' registrata.")
        self.txt_log.see("end")
        self.txt_log.configure(state="disabled")

    def _apri_cartella(self):
        os.makedirs(core.DATA_DIR, exist_ok=True)
        os.startfile(core.DATA_DIR)                            # noqa: S606

    # =================================================== pagina: impostazioni
    def _pag_impostazioni(self, p):
        box = self._card(p, "Moduli di protezione", adatta=True)
        box.pack(fill="x")

        self.var = {}
        moduli = [
            ("blocco_siti", "Blocco siti per adulti", "circa 200 regole nel file hosts"),
            ("safe_search", "Ricerca protetta", "Google, YouTube e Bing filtrati"),
            ("dns_famiglia", "DNS con filtro famiglia", "Cloudflare for Families"),
            ("blocca_doh", "Blocca DNS-over-HTTPS nei browser",
             "senza questo il browser salta il filtro"),
            ("blocco_incognito", "Disattiva navigazione in incognito",
             "Chrome, Edge, Brave, Firefox"),
            ("blocco_ricerche", "Controlla le ricerche",
             "chiude le ricerche con parole vietate"),
            ("blocco_programmi", "Chiudi i programmi sospetti",
             "VPN, Tor, client P2P"),
            ("protezione_file", "Proteggi i file dall'eliminazione",
             "nega l'eliminazione agli account standard"),
        ]
        for chiave, titolo, nota in moduli:
            self.var[chiave] = self._interruttore(box, chiave, titolo, nota)

        sotto = tk.Frame(p, bg=BG)
        sotto.pack(fill="x", pady=(14, 0))

        auto = self._card(sotto, "Avvio", adatta=True)
        auto.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.var_avvio = tk.BooleanVar(value=core.avvio_automatico_attivo())
        self._riga_interruttore(auto.dentro, self.var_avvio, self._cambia_avvio,
                                "All'accensione del PC", "e a ogni accesso")

        sic = self._card(sotto, "Sicurezza", adatta=True)
        sic.pack(side="left", fill="x", expand=True, padx=(8, 0))
        riga = tk.Frame(sic.dentro, bg=CARD)
        riga.pack(fill="x", padx=14, pady=(0, 10))
        Bottone(riga, "Imposta PIN", self._cambia_pin).pack(side="left")
        self.lbl_pin = tk.Label(riga, bg=CARD, fg=FG2, font=(F, 9))
        self.lbl_pin.pack(side="left", padx=12)
        self._aggiorna_etichetta_pin()

    def _riga_interruttore(self, padre, var, comando, titolo, nota):
        riga = tk.Frame(padre, bg=CARD)
        riga.pack(fill="x", padx=14, pady=5)
        Interruttore(riga, var, comando).pack(side="right")
        tk.Label(riga, text=titolo, bg=CARD, fg=FG, font=(F, 10)).pack(side="left")
        tk.Label(riga, text=nota, bg=CARD, fg=FG3,
                 font=(F, 8)).pack(side="left", padx=(10, 0))

    def _interruttore(self, padre, chiave, titolo, nota):
        v = tk.BooleanVar(value=self.cfg.get(chiave, True))
        self._riga_interruttore(padre.dentro, v, lambda: self._cambia_modulo(chiave),
                                titolo, nota)
        return v

    def _cambia_modulo(self, chiave):
        if not self._chiedi_pin():
            self.var[chiave].set(self.cfg.get(chiave, True))
            return
        self.cfg[chiave] = self.var[chiave].get()
        core.salva_config(self.cfg)
        if self.sorveglianza:
            self.sorveglianza.aggiorna(self.cfg)
        if self.cfg.get("protezione_attiva"):
            self._riapplica()
        self._aggiorna_stato()

    def _cambia_avvio(self):
        if not self._chiedi_pin():
            self.var_avvio.set(not self.var_avvio.get())
            return
        core.imposta_avvio_automatico(self.var_avvio.get())
        self.var_avvio.set(core.avvio_automatico_attivo())

    def _cambia_pin(self):
        if not self._chiedi_pin():
            return
        nuovo = simpledialog.askstring("PIN", "Nuovo PIN (vuoto per rimuoverlo):",
                                       show="*", parent=self)
        if nuovo is None:
            return
        if nuovo.strip():
            core.imposta_pin(self.cfg, nuovo.strip())
            core.log("PIN di protezione impostato")
        else:
            self.cfg["pin_hash"] = None
            self.cfg["pin_salt"] = None
            core.log("PIN di protezione rimosso")
        core.salva_config(self.cfg)
        self._aggiorna_etichetta_pin()

    def _aggiorna_etichetta_pin(self):
        self.lbl_pin.configure(text="PIN attivo" if self.cfg.get("pin_hash")
                               else "nessun PIN impostato")

    def _chiedi_pin(self):
        if not self.cfg.get("pin_hash"):
            return True
        pin = simpledialog.askstring("PIN richiesto", "Inserisci il PIN:",
                                     show="*", parent=self)
        if pin and core.verifica_pin(self.cfg, pin):
            return True
        core.log("Tentativo di modifica con PIN errato")
        messagebox.showerror(core.APP_NAME, "PIN errato.", parent=self)
        return False

    # =================================================== protezione
    def _toggle_protezione(self):
        if self.cfg.get("protezione_attiva"):
            if not self._chiedi_pin():
                return
            if not messagebox.askyesno(core.APP_NAME,
                                       "Disattivare la protezione?\n"
                                       "I siti bloccati torneranno accessibili e i file\n"
                                       "di Doorman potranno essere eliminati.",
                                       parent=self):
                return
            core.disattiva(self.cfg)
        else:
            self._riapplica()
        self._aggiorna_stato()
        self._ricarica_log()

    def _riapplica(self):
        try:
            core.attiva(self.cfg)
        except PermissionError:
            core.log("Errore: privilegi insufficienti per modificare il file hosts")
            messagebox.showerror(core.APP_NAME,
                                 "Servono i privilegi di amministratore.\n"
                                 "Riavvia il programma come amministratore.",
                                 parent=self)
        self._aggiorna_stato()

    def _avvia_sorveglianza(self):
        # le ricerche le controlla l'istanza "Doorman Utente" avviata a ogni accesso:
        # farlo anche qui chiuderebbe due schede per la stessa ricerca
        self.sorveglianza = core.Sorveglianza(self.cfg, callback=self._minaccia,
                                              ricerche=False)
        self.sorveglianza.start()

    def _minaccia(self, messaggio):
        self.after(0, lambda: self._notifica(messaggio))

    def _notifica(self, messaggio):
        self._ricarica_log()
        self.lbl_dett.configure(text=messaggio.split("] ", 1)[-1])

    def _aggiorna_stato(self):
        attiva = bool(self.cfg.get("protezione_attiva"))
        self._disegna_anello(attiva)
        if attiva:
            self.lbl_stato.configure(text="Protezione attiva", fg=FG)
            self.lbl_dett.configure(
                text="%d regole sui siti  ·  %d programmi sorvegliati  ·  policy browser applicate"
                     % (core.conta_regole_hosts(), len(self.cfg.get("programmi", []))))
            self.btn_toggle.imposta("Disattiva", "pericolo")
        else:
            self.lbl_stato.configure(text="Protezione disattivata", fg=FG)
            self.lbl_dett.configure(text="Il computer non e' protetto.")
            self.btn_toggle.imposta("Attiva protezione", "primario")
        if not core.is_admin():
            self.lbl_dett.configure(
                text="Avvia come amministratore per applicare i blocchi.")

    # =================================================== widget
    def _card(self, padre, titolo, sottotitolo=None, adatta=False):
        card = Card(padre, sfondo=padre["bg"], adatta=adatta)
        testa = tk.Frame(card.dentro, bg=CARD)
        testa.pack(fill="x", padx=14, pady=(10, 8))
        tk.Label(testa, text=titolo, bg=CARD, fg=FG,
                 font=(F, 11, "bold")).pack(side="left")
        if sottotitolo:
            tk.Label(testa, text=sottotitolo, bg=CARD, fg=FG3,
                     font=(F, 8)).pack(side="left", padx=(10, 0))
        return card

    def _lista(self, card):
        cont = Card(card.dentro, colore=CAMPO, sfondo=CARD, raggio=14,
                    margine=8, bordo=None)
        cont.pack(fill="both", expand=True, padx=14)
        lst = tk.Listbox(cont.dentro, bg=CAMPO, fg=FG, bd=0, highlightthickness=0,
                         selectbackground=OK_TENUE, selectforeground=OK,
                         font=(F, 10), activestyle="none", relief="flat")
        lst.pack(fill="both", expand=True, padx=4)
        return lst

    def _riga_input(self, card, azione_add, azione_del, segnaposto="esempio.com"):
        riga = tk.Frame(card.dentro, bg=CARD)
        riga.pack(fill="x", padx=14, pady=(10, 10))
        box, campo = campo_testo(riga)
        campo.insert(0, segnaposto)
        campo.configure(fg=FG2)

        def entra(_):
            if campo.get() == segnaposto:
                campo.delete(0, "end")
                campo.configure(fg=FG)

        def esce(_):
            if not campo.get().strip():
                campo.insert(0, segnaposto)
                campo.configure(fg=FG2)

        campo.bind("<FocusIn>", entra)
        campo.bind("<FocusOut>", esce)
        box.pack(side="left", fill="x", expand=True, padx=(0, 8))

        def aggiungi():
            valore = campo.get()
            if valore.strip() and valore != segnaposto:
                azione_add(valore)
                campo.delete(0, "end")
                esce(None)

        campo.bind("<Return>", lambda e: aggiungi())
        Bottone(riga, "Aggiungi", aggiungi).pack(side="left")
        Bottone(riga, "Rimuovi", azione_del, "secondario").pack(side="left", padx=(8, 0))

    def _rimuovi(self, lista, chiave):
        sel = lista.curselection()
        if not sel:
            return
        valore = lista.get(sel[0])
        if valore in self.cfg.get(chiave, []):
            self.cfg[chiave].remove(valore)
            self._salva_e_riapplica("Voce rimossa da %s: %s" % (chiave, valore))

    def _salva_e_riapplica(self, messaggio, riapplica=True):
        if not self._chiedi_pin():
            self._ricarica_liste()
            return
        core.salva_config(self.cfg)
        core.log(messaggio)
        if self.sorveglianza:
            self.sorveglianza.aggiorna(self.cfg)
        if riapplica and self.cfg.get("protezione_attiva"):
            self._riapplica()
        self._ricarica_liste()

    def _ricarica_liste(self):
        for lista, chiave in ((self.lst_siti, "siti_extra"),
                              (self.lst_perm, "siti_consentiti"),
                              (self.lst_parole, "parole_ricerca"),
                              (self.lst_prog, "programmi")):
            lista.delete(0, "end")
            for voce in sorted(self.cfg.get(chiave, [])):
                lista.insert("end", voce)

    def _chiudi(self):
        if self.cfg.get("protezione_attiva"):
            if not messagebox.askyesno(
                    core.APP_NAME,
                    "La protezione resta attiva anche a finestra chiusa.\n\n"
                    "Chiudere la finestra?", parent=self):
                return
        if self.sorveglianza:
            self.sorveglianza.ferma()
        self.destroy()


def main():
    if "--servizio" in sys.argv:
        core.servizio()
        return
    silenzioso = "--avvio" in sys.argv
    if silenzioso and not core.is_admin():
        core.sorveglianza_utente()
        return

    if not core.is_admin():
        radice = tk.Tk()
        radice.withdraw()
        if silenzioso or messagebox.askyesno(
                core.APP_NAME,
                "Doorman deve essere eseguito come amministratore\n"
                "per bloccare siti e programmi.\n\nRiavviare con privilegi elevati?"):
            core.rilancia_come_admin()
        radice.destroy()
        return

    DoormanApp(avvio_silenzioso=silenzioso).mainloop()


if __name__ == "__main__":
    main()
