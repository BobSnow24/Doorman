# Doorman 1.1

Piccolo programma per Windows in stile antivirus che **blocca l'accesso a siti per adulti
e chiude i programmi sospetti**. Non e' un antivirus vero: non cerca virus nei file, ma
applica filtri reali di rete e di sistema.

## Cosa fa davvero

| Modulo | Come funziona | Effetto |
|---|---|---|
| **Blocco siti** | Scrive ~200 regole nel file `hosts` di Windows | I domini bloccati non si aprono in **nessun browser** (Chrome, Edge, Firefox...) |
| **Ricerca protetta** | Reindirizza Google, YouTube e Bing alle versioni filtrate | Risultati e video espliciti esclusi dalle ricerche |
| **DNS famiglia** | Imposta Cloudflare for Families (`1.1.1.3`) sulle schede di rete | Blocca anche i siti **non presenti in elenco**, aggiornati di continuo |
| **Policy browser** | Chiavi in `HKLM\SOFTWARE\Policies\...` per Chrome, Edge, Brave, Firefox | Spegne **DNS-over-HTTPS** (senza, il browser risolve da solo e salta hosts e DNS) e disattiva l'**incognito** |
| **Controllo ricerche** | Legge il titolo della finestra del browser sulle pagine di risultati (Google, Bing, DuckDuckGo, YouTube) | Se il testo cercato contiene una parola della scheda *Ricerche*, la scheda viene chiusa e l'evento finisce nel registro |
| **Programmi sospetti** | Controlla i processi ogni 4 secondi e chiude quelli in blacklist | Chiude VPN, Tor Browser, client P2P usati per aggirare il filtro |
| **Protezione file** | `icacls` nega `(DE,DC)` al gruppo Utenti su `Doorman.exe` e `C:\ProgramData\Doorman` | Un account standard non può eliminare il programma. Un amministratore può prendere possesso e forzare |
| **PIN** | Codice richiesto per disattivare o modificare le liste | Impedisce di togliere la protezione |
| **Avvio automatico** | Due attivita' pianificate, create da *Attiva protezione* | `Doorman` parte all'accensione come SYSTEM e riapplica le protezioni; `Doorman Utente` parte a ogni accesso, per qualsiasi account, e controlla le ricerche. Anche a batteria, senza limite di tempo |

## Avvio rapido (senza compilare)

Doppio clic su **`Avvia Doorman.bat`**, oppure:

```bash
python app.py
```

Il programma chiede da solo i privilegi di amministratore: servono per modificare il file
`hosts` e i DNS. Poi premi **ATTIVA PROTEZIONE**.

## Creare il file .exe

Doppio clic su **`Crea EXE.bat`**. Il risultato e' `dist\Doorman.exe`, un file unico
che si puo' copiare su altri PC.

> Nota: PyInstaller non funziona con la versione di Python del Microsoft Store.
> Se la compilazione fallisce, installa Python da [python.org](https://www.python.org/downloads/)
> ricordando di spuntare *Add Python to PATH*.

## Le schede del programma

- **Stato** — pulsante di scansione: verifica una per una le protezioni e segnala cosa non e' attivo.
- **Siti bloccati** — aggiungi altri domini da bloccare, o eccezioni sempre consentite.
- **Ricerche** — parole o frasi da intercettare nelle ricerche (l'elenco parte vuoto).
- **Programmi** — elenco degli eseguibili da chiudere (es. `gioco.exe`).
- **Registro** — cronologia di tutto: attivazioni, siti aggiunti, programmi bloccati, PIN errati.
- **Impostazioni** — attiva/disattiva i singoli moduli, PIN, avvio con Windows.

## Dove finiscono i dati

```
C:\ProgramData\Doorman\config.json    impostazioni e liste
C:\ProgramData\Doorman\attivita.log   registro attivita'
C:\ProgramData\Doorman\ricerche.log   ricerche bloccate (scritto dall'istanza utente)
```

Le regole nel file hosts stanno fra i marcatori `# === DOORMAN START ===` e
`# === DOORMAN END ===`: il resto del file non viene mai toccato.

## Ripristino manuale

Se il programma non parte piu' e vuoi togliere i blocchi, da un Prompt dei comandi
**come amministratore**:

```bash
notepad C:\Windows\System32\drivers\etc\hosts
```

cancella le righe fra i due marcatori, poi:

```bash
ipconfig /flushdns
```

e per i DNS:

```bash
netsh interface ipv4 set dnsservers name="Ethernet 2" dhcp
```

## Limiti da conoscere

- Il filtro `hosts` non blocca i siti raggiunti tramite **DNS-over-HTTPS** attivo nel browser:
  il modulo DNS famiglia e la chiusura delle VPN servono proprio a coprire questo caso.
- Un utente amministratore puo' sempre disattivare tutto: la protezione e' un deterrente
  efficace, non una barriera invalicabile.
- Le liste di domini vanno ampliate nel tempo dalla scheda *Siti bloccati*.
- Il controllo ricerche gira nella sessione dell'utente: chi sa usare Gestione attivita' puo'
  chiuderlo. Blocco siti, DNS e chiusura programmi restano attivi comunque.
- Le attivita' pianificate vanno create dall'exe: il Python del Microsoft Store non e'
  avviabile dall'account SYSTEM.
