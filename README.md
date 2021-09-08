# Validacija posnetkov govora

Aplikacija za validacijo govornih posnetkov, ki omogoča preverjanje skladnosti posnetkov z referenčnim besedilom in ustreznosti začetnih/končnih premorov ter glasnosti.

# Namestitev in uporaba

Koda je spisana v programskem jeziku Python 3. Zahtevane knjižnice se namesti z ```pip install -r requirements.txt```. Aplikacijo se zažene z ukazom ```python audio_validation.py``` pri čemer se prikaže grafični vmesnik, v katerem najprej navedemo vhodne parametre, kot je pot do direktorija s posnetki, pot do datoteke XLSX z besedilom in način delovanja (ročni/samodejni/polsamodejni). Po vnosu vhodnih parametrov s pritiskom na tipko Zaženi pričnemo z validacijo posnetkov.

V okolju Windows namesto Python skripte lahko zaženemo tudi samostojno [izvršljivo datoteko](https://unilj-my.sharepoint.com/:u:/g/personal/janezkrfe_fe1_uni-lj_si/EUk8rVw1B7lGi_FZfrXHtBcB6pLBJAhV2PHNZpCCf5fFSg?e=LhBbgf). Za njeno uporabo je potrebno najprej odpakirati arhiv in nato zagnati audio_validation.exe.lnk iz arhiva.
