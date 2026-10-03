# -*- coding: utf-8 -*-
"""Doorman - motore di protezione (solo libreria standard di Python)."""

import ctypes
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import threading
import winreg
from ctypes import wintypes
from datetime import datetime

import blocklist

APP_NAME = "Doorman"
VERSIONE = "1.1"

MARK_START = "# === DOORMAN START - non modificare manualmente ==="
MARK_END = "# === DOORMAN END ==="
# marcatori del vecchio nome (SafeGuardian): riconosciuti per ripulire il file hosts
_MARK_VECCHI_START = ("# === SAFEGUARDIAN START - non modificare manualmente ===",)
_MARK_VECCHI_END = ("# === SAFEGUARDIAN END ===",)

HOSTS_PATH = os.path.join(os.environ.get("WINDIR", r"C:\Windows"),
                          "System32", "drivers", "etc", "hosts")
DATA_DIR = os.path.join(os.environ.get("PROGRAMDATA", r"C:\ProgramData"), APP_NAME)
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")
LOG_PATH = os.path.join(DATA_DIR, "attivita.log")
# scritto dall'istanza senza privilegi che gira nella sessione dell'utente
LOG_UTENTE_PATH = os.path.join(DATA_DIR, "ricerche.log")

# Cloudflare for Families: filtro malware + contenuti per adulti
DNS_V4 = ["1.1.1.3", "1.0.0.3"]
DNS_V6 = ["2606:4700:4700::1113", "2606:4700:4700::1003"]

_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


# --------------------------------------------------------------------------
# utilita' di base
# --------------------------------------------------------------------------
def esegui(cmd, timeout=25):
    """Esegue un comando senza aprire finestre. Ritorna (returncode, output)."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace",
                           creationflags=_NO_WINDOW)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except Exception as e:                                    # noqa: BLE001
        return -1, str(e)


def powershell(script, timeout=30):
    return esegui(["powershell", "-NoProfile", "-NonInteractive",
                   "-ExecutionPolicy", "Bypass", "-Command", script], timeout)


def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:                                         # noqa: BLE001
        return False


def rilancia_come_admin():
    """Riavvia il processo corrente chiedendo i privilegi di amministratore."""
    if getattr(sys, "frozen", False):
        exe = sys.executable
        params = " ".join(sys.argv[1:])
    else:
        exe = sys.executable
        params = " ".join('"%s"' % a for a in sys.argv)
    ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)


def log(messaggio):
    os.makedirs(DATA_DIR, exist_ok=True)
    riga = "[%s] %s" % (datetime.now().strftime(_FMT_DATA), messaggio)
    for percorso in (LOG_PATH, LOG_UTENTE_PATH):
        try:
            with open(percorso, "a", encoding="utf-8") as f:
                f.write(riga + "\n")
            break
        except OSError:
            continue
    return riga


_FMT_DATA = "%d/%m/%Y %H:%M:%S"


def _data_riga(riga):
    try:
        return datetime.strptime(riga[1:20], _FMT_DATA)
    except ValueError:
        return datetime.min


def leggi_log(ultime=300):
    righe = []
    for percorso in (LOG_PATH, LOG_UTENTE_PATH):
        try:
            with open(percorso, "r", encoding="utf-8", errors="replace") as f:
                righe += f.readlines()
        except OSError:
            pass
    righe.sort(key=_data_riga)
    return righe[-ultime:]


# --------------------------------------------------------------------------
# configurazione
# --------------------------------------------------------------------------
CONFIG_DEFAULT = {
    "protezione_attiva": False,
    "blocco_siti": True,
    "dns_famiglia": True,
    "safe_search": True,
    "blocco_programmi": True,
    "blocca_doh": True,
    "blocco_incognito": True,
    "protezione_file": True,
    "blocco_ricerche": True,
    "parole_ricerca": [],
    "siti_extra": [],
    "siti_consentiti": [],
    "programmi": list(blocklist.PROGRAMMI_SOSPETTI),
    "pin_hash": None,
    "pin_salt": None,
}


def carica_config():
    cfg = dict(CONFIG_DEFAULT)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg.update(json.load(f))
    except (OSError, ValueError):
        pass
    return cfg


def salva_config(cfg):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def imposta_pin(cfg, pin):
    salt = os.urandom(16).hex()
    cfg["pin_salt"] = salt
    cfg["pin_hash"] = hashlib.sha256((salt + pin).encode()).hexdigest()


def verifica_pin(cfg, pin):
    if not cfg.get("pin_hash"):
        return True
    atteso = hashlib.sha256((cfg.get("pin_salt", "") + pin).encode()).hexdigest()
    return atteso == cfg["pin_hash"]


# --------------------------------------------------------------------------
# blocco siti tramite file hosts
# --------------------------------------------------------------------------
def _risolvi(host):
    try:
        return socket.gethostbyname(host)
    except OSError:
        return blocklist.SAFE_SEARCH_FALLBACK.get(host)


def normalizza(dominio):
    d = dominio.lower().strip()
    for prefisso in ("http://", "https://"):
        if d.startswith(prefisso):
            d = d[len(prefisso):]
    return d.split("/")[0].strip()


def costruisci_voci(cfg):
    """Righe da scrivere nel file hosts in base alla configurazione."""
    consentiti = {normalizza(d) for d in cfg.get("siti_consentiti", [])}
    voci = []

    if cfg.get("blocco_siti", True):
        domini = list(blocklist.SITI_ADULTI) + list(cfg.get("siti_extra", []))
        visti = set()
        for grezzo in domini:
            d = normalizza(grezzo)
            if not d or d in consentiti or d in visti:
                continue
            visti.add(d)
            voci.append("0.0.0.0 %s" % d)
            if not d.startswith("www."):
                voci.append("0.0.0.0 www.%s" % d)

    if cfg.get("safe_search", True):
        cache = {}
        for dominio, target in blocklist.SAFE_SEARCH.items():
            if dominio in consentiti:
                continue
            if target not in cache:
                cache[target] = _risolvi(target)
            ip = cache[target]
            if ip:
                voci.append("%s %s" % (ip, dominio))
    return voci


def _leggi_hosts():
    for enc in ("utf-8", "latin-1"):
        try:
            with open(HOSTS_PATH, "r", encoding=enc) as f:
                return f.read().splitlines()
        except UnicodeDecodeError:
            continue
        except OSError:
            return []
    return []


def _scrivi_hosts(righe):
    contenuto = "\r\n".join(righe).rstrip("\r\n") + "\r\n"
    with open(HOSTS_PATH, "w", encoding="utf-8", newline="") as f:
        f.write(contenuto)


def _senza_blocco(righe):
    fuori, dentro = [], False
    for r in righe:
        testo = r.strip()
        if testo == MARK_START or testo in _MARK_VECCHI_START:
            dentro = True
            continue
        if testo == MARK_END or testo in _MARK_VECCHI_END:
            dentro = False
            continue
        if not dentro:
            fuori.append(r)
    return fuori


def applica_hosts(cfg):
    voci = costruisci_voci(cfg)
    righe = _senza_blocco(_leggi_hosts())
    if voci:
        righe = righe + [MARK_START] + voci + [MARK_END]
    _scrivi_hosts(righe)
    svuota_cache_dns()
    log("File hosts aggiornato: %d regole attive" % len(voci))
    return len(voci)


def rimuovi_hosts():
    _scrivi_hosts(_senza_blocco(_leggi_hosts()))
    svuota_cache_dns()
    log("File hosts ripulito: blocco siti disattivato")


def hosts_attivo():
    return any(r.strip() == MARK_START for r in _leggi_hosts())


def conta_regole_hosts():
    dentro, n = False, 0
    for r in _leggi_hosts():
        testo = r.strip()
        if testo == MARK_START:
            dentro = True
        elif testo == MARK_END:
            dentro = False
        elif dentro and testo:
            n += 1
    return n


def svuota_cache_dns():
    esegui(["ipconfig", "/flushdns"], timeout=15)


# --------------------------------------------------------------------------
# DNS con filtro famiglia (Cloudflare for Families)
# --------------------------------------------------------------------------
def interfacce_attive():
    rc, out = powershell(
        "Get-NetIPInterface -ConnectionState Connected -AddressFamily IPv4 "
        "| Select-Object -ExpandProperty InterfaceAlias")
    nomi = [l.strip() for l in out.splitlines() if l.strip()]
    if rc == 0 and nomi:
        return [n for n in dict.fromkeys(nomi) if "Loopback" not in n]

    # ripiego su netsh se PowerShell non e' disponibile
    rc, out = esegui(["netsh", "interface", "show", "interface"])
    nomi = []
    for riga in out.splitlines():
        parti = riga.split(None, 3)
        if len(parti) == 4 and parti[0].lower() in ("enabled", "abilitato", "attivato"):
            nomi.append(parti[3].strip())
    return nomi


def applica_dns_famiglia():
    fatte = []
    for nome in interfacce_attive():
        rc, _ = esegui(["netsh", "interface", "ipv4", "set", "dnsservers",
                        "name=%s" % nome, "static", DNS_V4[0], "primary", "validate=no"])
        if rc == 0:
            esegui(["netsh", "interface", "ipv4", "add", "dnsservers",
                    "name=%s" % nome, DNS_V4[1], "index=2", "validate=no"])
            esegui(["netsh", "interface", "ipv6", "set", "dnsservers",
                    "name=%s" % nome, "static", DNS_V6[0], "primary", "validate=no"])
            esegui(["netsh", "interface", "ipv6", "add", "dnsservers",
                    "name=%s" % nome, DNS_V6[1], "index=2", "validate=no"])
            fatte.append(nome)
    svuota_cache_dns()
    log("DNS famiglia attivato su: %s" % (", ".join(fatte) or "nessuna interfaccia"))
    return fatte


def ripristina_dns():
    for nome in interfacce_attive():
        esegui(["netsh", "interface", "ipv4", "set", "dnsservers", "name=%s" % nome, "dhcp"])
        esegui(["netsh", "interface", "ipv6", "set", "dnsservers", "name=%s" % nome, "dhcp"])
    svuota_cache_dns()
    log("DNS ripristinati su automatico (DHCP)")


def dns_famiglia_attivo():
    rc, out = powershell("Get-DnsClientServerAddress -AddressFamily IPv4 "
                         "| Select-Object -ExpandProperty ServerAddresses")
    return any(ip in out for ip in DNS_V4)


# --------------------------------------------------------------------------
# policy dei browser (DNS-over-HTTPS e navigazione in incognito)
#
# Senza queste, il browser risolve i domini da solo via HTTPS e salta sia il
# file hosts sia i DNS di sistema: il filtro non vedrebbe nulla.
# Ogni voce: (sottochiave, nome, tipo, valore)
# --------------------------------------------------------------------------
_CHROMIUM = [
    r"SOFTWARE\Policies\Google\Chrome",
    r"SOFTWARE\Policies\Microsoft\Edge",
    r"SOFTWARE\Policies\BraveSoftware\Brave",
    r"SOFTWARE\Policies\Chromium",
]


def _voci_policy(cfg):
    voci = []
    if cfg.get("blocca_doh", True):
        for chiave in _CHROMIUM:
            voci.append((chiave, "DnsOverHttpsMode", winreg.REG_SZ, "off"))
            voci.append((chiave, "BuiltInDnsClientEnabled", winreg.REG_DWORD, 0))
        voci.append((r"SOFTWARE\Policies\Mozilla\Firefox\DNSOverHTTPS",
                     "Enabled", winreg.REG_DWORD, 0))
        voci.append((r"SOFTWARE\Policies\Mozilla\Firefox\DNSOverHTTPS",
                     "Locked", winreg.REG_DWORD, 1))
    if cfg.get("blocco_incognito", True):
        voci.append((r"SOFTWARE\Policies\Google\Chrome",
                     "IncognitoModeAvailability", winreg.REG_DWORD, 1))
        voci.append((r"SOFTWARE\Policies\Microsoft\Edge",
                     "InPrivateModeAvailability", winreg.REG_DWORD, 1))
        voci.append((r"SOFTWARE\Policies\BraveSoftware\Brave",
                     "IncognitoModeAvailability", winreg.REG_DWORD, 1))
        voci.append((r"SOFTWARE\Policies\Mozilla\Firefox",
                     "DisablePrivateBrowsing", winreg.REG_DWORD, 1))
    return voci


def applica_policy_browser(cfg):
    scritte = 0
    for sottochiave, nome, tipo, valore in _voci_policy(cfg):
        try:
            with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, sottochiave, 0,
                                    winreg.KEY_SET_VALUE) as k:
                winreg.SetValueEx(k, nome, 0, tipo, valore)
            scritte += 1
        except OSError as e:
            log("Policy non applicata (%s\\%s): %s" % (sottochiave, nome, e))
    log("Policy browser applicate: %d valori" % scritte)
    return scritte


def rimuovi_policy_browser():
    cfg_tutto = {"blocca_doh": True, "blocco_incognito": True}
    for sottochiave, nome, _, _ in _voci_policy(cfg_tutto):
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, sottochiave, 0,
                                winreg.KEY_SET_VALUE) as k:
                winreg.DeleteValue(k, nome)
        except OSError:
            pass
    log("Policy browser rimosse")


def policy_attive(cfg):
    """True se ogni valore previsto dalla configurazione e' presente nel registro."""
    voci = _voci_policy(cfg)
    if not voci:
        return True
    for sottochiave, nome, _, atteso in voci:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, sottochiave) as k:
                if winreg.QueryValueEx(k, nome)[0] != atteso:
                    return False
        except OSError:
            return False
    return True


# --------------------------------------------------------------------------
# protezione dei file dall'eliminazione
#
# Nega il permesso di eliminazione al gruppo Utenti (SID S-1-5-32-545, uguale
# in ogni lingua di Windows). Un account standard riceve "accesso negato"; un
# amministratore puo' sempre prendere possesso dei file e forzare la rimozione.
# --------------------------------------------------------------------------
SID_UTENTI = "*S-1-5-32-545"


def percorsi_protetti():
    """L'eseguibile (o i sorgenti) piu' la cartella dati.

    Da congelato si protegge il singolo file .exe, non la cartella che lo
    contiene: quella puo' essere il Desktop, e negarne l'eliminazione
    bloccherebbe tutto quello che c'e' dentro.
    """
    if getattr(sys, "frozen", False):
        propria = sys.executable
    else:
        propria = os.path.dirname(os.path.abspath(__file__))
    return [p for p in (propria, DATA_DIR) if os.path.exists(p)]


def _argomenti_icacls(percorso):
    return ["/t", "/c", "/q"] if os.path.isdir(percorso) else ["/q"]


def proteggi_file():
    fatti = []
    for percorso in percorsi_protetti():
        rc, _ = esegui(["icacls", percorso, "/deny", "%s:(DE,DC)" % SID_UTENTI]
                       + _argomenti_icacls(percorso), timeout=90)
        if rc == 0:
            fatti.append(percorso)
    log("Protezione file attivata su: %s" % (", ".join(fatti) or "nessun percorso"))
    return fatti


def sproteggi_file():
    for percorso in percorsi_protetti():
        esegui(["icacls", percorso, "/remove:d", SID_UTENTI]
               + _argomenti_icacls(percorso), timeout=90)
    log("Protezione file rimossa")


def protezione_file_attiva():
    for percorso in percorsi_protetti():
        rc, out = esegui(["icacls", percorso], timeout=30)
        if rc != 0 or "(DENY)" not in out.upper():
            return False
    return bool(percorsi_protetti())


# --------------------------------------------------------------------------
# sorveglianza processi
# --------------------------------------------------------------------------
def processi_in_esecuzione():
    rc, out = esegui(["tasklist", "/fo", "csv", "/nh"], timeout=20)
    nomi = []
    for riga in out.splitlines():
        riga = riga.strip()
        if riga.startswith('"'):
            nomi.append(riga.split('","')[0].strip('"').lower())
    return nomi


def termina(nome_exe):
    rc, _ = esegui(["taskkill", "/f", "/im", nome_exe], timeout=15)
    return rc == 0


# --------------------------------------------------------------------------
# controllo delle ricerche
#
# Le ricerche viaggiano in HTTPS: dalla rete non si leggono. Il titolo della
# finestra del browser invece si': sulla pagina dei risultati e' "<testo
# cercato> - Cerca con Google". Se il testo contiene una parola della lista,
# la scheda viene chiusa. Funziona solo dalla sessione dell'utente (non da
# SYSTEM), per questo a ogni accesso parte un'istanza apposita.
# --------------------------------------------------------------------------
CLASSI_BROWSER = {"Chrome_WidgetWin_1", "MozillaWindowClass"}  # Chrome/Edge/Brave/Opera, Firefox
_user32 = ctypes.windll.user32 if os.name == "nt" else None


def testo_cercato(titolo):
    """Il testo cercato se il titolo e' una pagina di risultati, altrimenti None."""
    for suffisso in blocklist.MOTORI_RICERCA:
        if suffisso in titolo:
            return titolo.split(suffisso)[0].strip()
    return None


def parola_vietata(testo, parole):
    """Prima parola della lista contenuta nel testo (a inizio parola, maiuscole ignorate)."""
    testo = testo.lower()
    for p in parole:
        p = p.strip().lower()
        if p and re.search(r"(?<!\w)" + re.escape(p), testo):
            return p
    return None


def finestre_browser():
    trovate = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def visita(hwnd, _):
        if _user32.IsWindowVisible(hwnd):
            classe = ctypes.create_unicode_buffer(64)
            _user32.GetClassNameW(hwnd, classe, 64)
            n = _user32.GetWindowTextLengthW(hwnd)
            if classe.value in CLASSI_BROWSER and n:
                buf = ctypes.create_unicode_buffer(n + 1)
                _user32.GetWindowTextW(hwnd, buf, n + 1)
                trovate.append((hwnd, buf.value))
        return True

    _user32.EnumWindows(visita, 0)
    return trovate


def chiudi_scheda(hwnd):
    # ponytail: se la finestra non e' in primo piano Ctrl+W finirebbe altrove,
    # quindi si chiude l'intera finestra del browser (WM_CLOSE)
    if _user32.GetForegroundWindow() == hwnd:
        for tasto, su in ((0x11, 0), (0x57, 0), (0x57, 2), (0x11, 2)):  # Ctrl+W
            _user32.keybd_event(tasto, 0, su, 0)
    else:
        _user32.PostMessageW(hwnd, 0x0010, 0, 0)


class Sorveglianza(threading.Thread):
    """Chiude i programmi in blacklist e le ricerche con parole vietate.

    processi / ricerche: quali controlli fa questa istanza.
    ricarica: rilegge config.json a ogni giro (istanze senza interfaccia).
    """

    def __init__(self, cfg, callback=None, intervallo=2,
                 processi=True, ricerche=True, ricarica=False):
        super().__init__(daemon=True)
        self.cfg = cfg
        self.callback = callback
        self.intervallo = intervallo
        self.processi = processi
        self.ricerche = ricerche
        self.ricarica = ricarica
        self._stop = threading.Event()
        self._giro = 0
        self.bloccati = 0

    def aggiorna(self, cfg):
        self.cfg = cfg

    def _segnala(self, testo):
        self.bloccati += 1
        msg = log(testo)
        if self.callback:
            self.callback(msg)

    def _controlla_processi(self):
        lista = {p.lower().strip() for p in self.cfg.get("programmi", [])}
        for nome in processi_in_esecuzione():
            if nome in lista and termina(nome):
                self._segnala("MINACCIA BLOCCATA: processo '%s' terminato" % nome)

    def _controlla_ricerche(self):
        parole = self.cfg.get("parole_ricerca", [])
        if not parole:
            return
        for hwnd, titolo in finestre_browser():
            testo = testo_cercato(titolo)
            parola = testo and parola_vietata(testo, parole)
            if parola:
                chiudi_scheda(hwnd)
                self._segnala("RICERCA BLOCCATA: \"%s\" (parola: %s)" % (testo, parola))

    def run(self):
        log("Sorveglianza avviata")
        while not self._stop.is_set():
            try:
                if self.ricarica:
                    self.cfg = carica_config()
                if self.cfg.get("protezione_attiva"):
                    if self.ricerche and self.cfg.get("blocco_ricerche", True):
                        self._controlla_ricerche()
                    # tasklist e' lento: i processi si controllano un giro si' e uno no
                    if (self.processi and self.cfg.get("blocco_programmi", True)
                            and self._giro % 2 == 0):
                        self._controlla_processi()
            except Exception as e:                            # noqa: BLE001
                log("Errore sorveglianza: %s" % e)
            self._giro += 1
            self._stop.wait(self.intervallo)
        log("Sorveglianza fermata")

    def ferma(self):
        self._stop.set()


# --------------------------------------------------------------------------
# attivazione / disattivazione complessiva
# --------------------------------------------------------------------------
def attiva(cfg):
    esiti = []
    if cfg.get("blocco_siti", True) or cfg.get("safe_search", True):
        esiti.append("%d regole sui siti" % applica_hosts(cfg))
    if cfg.get("dns_famiglia", True):
        esiti.append("DNS protetto su %d schede di rete" % len(applica_dns_famiglia()))
    if cfg.get("blocca_doh", True) or cfg.get("blocco_incognito", True):
        esiti.append("%d policy browser" % applica_policy_browser(cfg))
    _prepara_log_utente()
    if cfg.get("protezione_file", True):
        esiti.append("%d cartelle protette" % len(proteggi_file()))
    if not avvio_automatico_attivo():
        imposta_avvio_automatico(True)
    cfg["protezione_attiva"] = True
    salva_config(cfg)
    log("PROTEZIONE ATTIVATA (%s)" % "; ".join(esiti))
    return esiti


def disattiva(cfg):
    rimuovi_hosts()
    if cfg.get("dns_famiglia", True):
        ripristina_dns()
    rimuovi_policy_browser()
    sproteggi_file()
    imposta_avvio_automatico(False)
    cfg["protezione_attiva"] = False
    salva_config(cfg)
    log("PROTEZIONE DISATTIVATA dall'utente")


def _prepara_log_utente():
    """Crea ricerche.log scrivibile dagli Utenti: l'istanza senza privilegi
    non puo' scrivere in attivita.log."""
    os.makedirs(DATA_DIR, exist_ok=True)
    open(LOG_UTENTE_PATH, "a").close()
    esegui(["icacls", LOG_UTENTE_PATH, "/grant", "%s:(W)" % SID_UTENTI, "/q"])


# --------------------------------------------------------------------------
# avvio automatico: due attivita' pianificate
#
#  "Doorman"         all'accensione, come SYSTEM: riapplica le protezioni
#                         e chiude i programmi vietati, prima di ogni accesso.
#  "Doorman Utente"  a ogni accesso, per qualsiasi utente, senza privilegi
#                         e senza finestra: controlla le ricerche nel browser.
#
# Entrambe girano anche a batteria e senza limite di tempo (i default di
# schtasks fermano l'attivita' a batteria e dopo 72 ore).
# --------------------------------------------------------------------------
TASK_UTENTE = APP_NAME + " Utente"


def _comando_avvio():
    """(eseguibile, argomenti di base) per lanciare il programma."""
    if getattr(sys, "frozen", False):
        return sys.executable, ""
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    script = os.path.abspath(os.path.join(os.path.dirname(__file__), "app.py"))
    return (pythonw if os.path.exists(pythonw) else sys.executable), '"%s" ' % script


def avvio_automatico_attivo():
    return all(esegui(["schtasks", "/query", "/tn", t])[0] == 0
               for t in (APP_NAME, TASK_UTENTE))


def imposta_avvio_automatico(attivo):
    if attivo:
        exe, base = _comando_avvio()
        q = lambda t: t.replace("'", "''")                    # noqa: E731
        azione = ("(New-ScheduledTaskAction -Execute '%s' -Argument '%s%%s')"
                  % (q(exe), q(base)))
        rc, out = powershell(
            "$ErrorActionPreference = 'Stop';"
            "$s = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries "
            "-DontStopIfGoingOnBatteries -StartWhenAvailable "
            "-ExecutionTimeLimit ([TimeSpan]::Zero);"
            "Register-ScheduledTask -TaskName '%s' -Force -Settings $s -Action %s "
            "-Trigger (New-ScheduledTaskTrigger -AtStartup) "
            "-Principal (New-ScheduledTaskPrincipal -UserId 'SYSTEM' "
            "-LogonType ServiceAccount -RunLevel Highest) | Out-Null;"
            "Register-ScheduledTask -TaskName '%s' -Force -Settings $s -Action %s "
            "-Trigger (New-ScheduledTaskTrigger -AtLogOn) "
            "-Principal (New-ScheduledTaskPrincipal -GroupId 'S-1-5-32-545' "
            "-RunLevel Limited) | Out-Null"
            % (APP_NAME, azione % "--servizio", TASK_UTENTE, azione % "--avvio"),
            timeout=60)
        log("Avvio automatico attivato (accensione + accesso utenti)" if rc == 0
            else "Avvio automatico non riuscito: %s" % out.strip())
        return rc == 0
    for t in (APP_NAME, TASK_UTENTE, "SafeGuardian", "SafeGuardian Utente"):  # + vecchio nome
        esegui(["schtasks", "/delete", "/tn", t, "/f"])
    log("Avvio automatico disattivato")
    return True


def servizio():
    """Modalita' --servizio: lanciata da SYSTEM all'accensione, senza finestra."""
    cfg = carica_config()
    if cfg.get("protezione_attiva"):
        try:
            attiva(cfg)
        except Exception as e:                                # noqa: BLE001
            log("Errore nel riapplicare le protezioni all'avvio: %s" % e)
    Sorveglianza(cfg, ricerche=False, ricarica=True).run()


def sorveglianza_utente():
    """Modalita' --avvio senza privilegi: solo controllo ricerche, senza finestra."""
    Sorveglianza(carica_config(), processi=False, ricarica=True).run()


# --------------------------------------------------------------------------
# scansione di controllo
# --------------------------------------------------------------------------
def scansione(cfg):
    """Verifica lo stato reale delle protezioni.

    Ritorna una lista di tuple (voce, esito_ok, dettaglio).
    """
    risultati = []

    n = conta_regole_hosts()
    risultati.append(("Filtro siti per adulti (file hosts)", hosts_attivo() and n > 0,
                      "%d regole attive" % n if n else "nessun blocco applicato"))

    righe = _leggi_hosts()
    ss_ok = any("google.com" in r and not r.strip().startswith("#")
                and not r.strip().startswith("0.0.0.0") for r in righe)
    if cfg.get("safe_search", True):
        risultati.append(("Ricerca protetta (Google/YouTube/Bing)", ss_ok,
                          "attiva" if ss_ok else "non applicata"))

    if cfg.get("dns_famiglia", True):
        d = dns_famiglia_attivo()
        risultati.append(("DNS con filtro famiglia", d,
                          "Cloudflare Families attivo" if d else "DNS di sistema non protetti"))

    if cfg.get("blocca_doh", True) or cfg.get("blocco_incognito", True):
        p = policy_attive(cfg)
        risultati.append(("Policy browser (DNS-over-HTTPS e incognito)", p,
                          "applicate" if p else
                          "mancanti: il browser puo' aggirare il filtro"))

    if cfg.get("protezione_file", True):
        f = protezione_file_attiva()
        risultati.append(("File di Doorman protetti dall'eliminazione", f,
                          "eliminazione negata agli account standard" if f
                          else "chiunque puo' eliminare il programma"))

    if cfg.get("blocco_ricerche", True):
        n = len(cfg.get("parole_ricerca", []))
        risultati.append(("Controllo delle ricerche", n > 0,
                          "%d parole sorvegliate" % n if n
                          else "nessuna parola in elenco: aggiungile dalla scheda Ricerche"))

    lista = {p.lower().strip() for p in cfg.get("programmi", [])}
    trovati = sorted({p for p in processi_in_esecuzione() if p in lista})
    risultati.append(("Programmi sospetti in esecuzione", not trovati,
                      "nessuna minaccia rilevata" if not trovati
                      else "trovati: %s" % ", ".join(trovati)))

    auto = avvio_automatico_attivo()
    risultati.append(("Protezione all'avvio di Windows", auto,
                      "all'accensione e a ogni accesso" if auto else "non configurata"))

    admin = is_admin()
    risultati.append(("Privilegi di amministratore", admin,
                      "concessi" if admin else "mancanti: il blocco non puo' essere applicato"))
    return risultati
