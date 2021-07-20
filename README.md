# Validacija posnetkov govora

Aplikacija za validacijo govornih posnetkov, ki omogoča preverjanje skladnosti posnetkov z besedilom in ustreznosti začetnih/končnih premorov ter glasnosti.

# Namestitev in uporaba

Koda je spisana v programskem jeziku Python 3. Zahtevane knjižnice se namesti z ```pip install -r requirements.txt```. Aplikacijo se zažene z ukazom ```python audio_validation.py``` pri čemer se prikaže grafični vmesnik, v katerem najprej navedemo vhodne parametre, kot je pot do direktorija s posnetki, pot do datoteke XLSX z besedilom in način delovanja (ročni/samodejni/polsamodejni). Po vnosu vhodnih parametrov s pritiskom na tipko Zaženi pričnemo z validacijo posnetkov.

V okolju Windows namesto Python skripte lahko zaženemo tudi datoteko EXE. Za njeno uporabo je potrebno najprej odpakirati arhiv ZIP in nato zagnati audio_validation.exe.lnk iz arhiva.
