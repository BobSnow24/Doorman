# -*- coding: utf-8 -*-
"""Liste di blocco predefinite di Doorman.

SITI_ADULTI      -> domini bloccati tramite il file hosts (risolti a 0.0.0.0)
SAFE_SEARCH      -> domini reindirizzati alla versione "filtrata" del motore di ricerca
PROGRAMMI_SOSPETTI -> eseguibili terminati dal modulo di sorveglianza processi
"""

# --- Siti per adulti / contenuti +18 -------------------------------------
SITI_ADULTI = [
    "pornhub.com", "rt.pornhub.com", "xvideos.com", "xnxx.com", "xhamster.com",
    "redtube.com", "youporn.com", "tube8.com", "spankbang.com", "eporner.com",
    "porntrex.com", "hqporner.com", "txxx.com", "upornia.com", "gotporn.com",
    "porn.com", "porndoe.com", "pornone.com", "porngo.com", "hclips.com",
    "beeg.com", "tnaflix.com", "empflix.com", "drtuber.com", "nuvid.com",
    "sunporno.com", "vporn.com", "pornhd.com", "fapello.com", "erome.com",
    "motherless.com", "youjizz.com", "keezmovies.com", "extremetube.com",
    "brazzers.com", "bangbros.com", "realitykings.com", "naughtyamerica.com",
    "digitalplayground.com", "mofos.com", "twistys.com", "babes.com",
    "onlyfans.com", "fansly.com", "manyvids.com", "clips4sale.com",
    "chaturbate.com", "stripchat.com", "bongacams.com", "cam4.com",
    "livejasmin.com", "myfreecams.com", "camsoda.com", "flirt4free.com",
    "adultfriendfinder.com", "ashleymadison.com", "fling.com",
    "nhentai.net", "hanime.tv", "hentaihaven.xxx", "rule34.xxx", "e-hentai.org",
    "exhentai.org", "gelbooru.com", "danbooru.donmai.us", "hentai2read.com",
    "iwara.tv", "javhd.com", "javfinder.is", "jable.tv", "missav.com",
    "pornolab.net", "sxyprn.com", "pornpics.com", "sex.com", "xxx.com",
    "literotica.com", "asstr.org", "f95zone.to",
    "streamate.com", "imlive.com", "xlovecam.com", "cams.com",
    "thothub.tv", "coomer.su", "kemono.su", "leakedzone.com",
    "escortforumit.xxx", "bakecaincontrii.com", "escortadvisor.com",
    "torrentz2.eu", "1337x.to", "thepiratebay.org",
]

# --- Motori di ricerca in modalita' protetta ------------------------------
# dominio -> host che ospita la versione filtrata (l'IP viene risolto a runtime)
SAFE_SEARCH = {
    "www.google.com": "forcesafesearch.google.com",
    "google.com": "forcesafesearch.google.com",
    "www.google.it": "forcesafesearch.google.com",
    "google.it": "forcesafesearch.google.com",
    "www.youtube.com": "restrictmoderate.youtube.com",
    "m.youtube.com": "restrictmoderate.youtube.com",
    "youtubei.googleapis.com": "restrictmoderate.youtube.com",
    "youtube.googleapis.com": "restrictmoderate.youtube.com",
    "www.youtube-nocookie.com": "restrictmoderate.youtube.com",
    "www.bing.com": "strict.bing.com",
    "bing.com": "strict.bing.com",
}

# IP di riserva se la risoluzione DNS non e' disponibile
SAFE_SEARCH_FALLBACK = {
    "forcesafesearch.google.com": "216.239.38.120",
    "restrictmoderate.youtube.com": "216.239.38.119",
    "strict.bing.com": "204.79.197.220",
}

# --- Pagine di risultati dei motori di ricerca ----------------------------
# Il titolo della finestra e' "<testo cercato><suffisso>": il testo prima del
# suffisso viene confrontato con le parole vietate (scheda Ricerche).
MOTORI_RICERCA = [
    " - Cerca con Google", " - Google Search", " - Ricerca Google",
    " - Cerca con Bing", " - Bing", " - Cerca", " - Search",
    " at DuckDuckGo", " su DuckDuckGo", " - YouTube",
]

# --- Programmi sospetti / aggira-filtro -----------------------------------
PROGRAMMI_SOSPETTI = [
    # Browser e strumenti usati per aggirare i filtri
    "tor.exe", "torbrowser.exe", "firefox.exe.tor", "start-tor-browser.exe",
    "psiphon.exe", "psiphon3.exe", "ultrasurf.exe", "u1310.exe",
    "freegate.exe", "proxifier.exe", "hotspotshield.exe", "hss.exe",
    "browsec.exe", "windscribe.exe", "protonvpn.exe", "nordvpn.exe",
    "expressvpn.exe", "cyberghost.exe", "tunnelbear.exe", "zenmate.exe",
    "opera.exe", "opera_gx.exe",           # VPN integrata nel browser
    # Client P2P
    "utorrent.exe", "bittorrent.exe", "qbittorrent.exe", "transmission.exe",
    "emule.exe", "frostwire.exe", "limewire.exe", "vuze.exe", "deluge.exe",
    # Strumenti di manomissione del filtro
    "hostsfileeditor.exe", "hostsman.exe", "dnsjumper.exe", "acrylicui.exe",
]
