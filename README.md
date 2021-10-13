![GUI](gui.jpg)
# Validacija posnetkov govora

Aplikacija za validacijo govornih posnetkov, ki omogoča preverjanje skladnosti posnetkov z referenčnim besedilom in ustreznosti začetnih/končnih premorov ter glasnosti.

## Namestitev in uporaba

Koda je spisana v programskem jeziku Python 3. Zahtevane knjižnice se namesti z ```pip install -r requirements.txt```. Aplikacijo se zažene z ukazom ```python audio_validation.py``` pri čemer se prikaže grafični vmesnik, v katerem najprej navedemo vhodne parametre, kot je pot do direktorija s posnetki, pot do datoteke XLSX z besedilom in način delovanja (ročni/samodejni/polsamodejni). Po vnosu vhodnih parametrov s pritiskom na tipko "Zaženi" pričnemo z validacijo posnetkov.

V izogib težavam pri namestitvi zahtevanih programskih knjižnic sta pripravljeni izvršljivi datoteki za okolje [Windows](https://unilj-my.sharepoint.com/:u:/g/personal/janezkrfe_fe1_uni-lj_si/EUk8rVw1B7lGi_FZfrXHtBcB6pLBJAhV2PHNZpCCf5fFSg?e=LhBbgf) in [Linux](https://unilj-my.sharepoint.com/:u:/g/personal/janezkrfe_fe1_uni-lj_si/EasNMx8l5QNGg8U6TQrHyscB9Q-oWLSscv7kmCS_ElhJBQ?e=sAlL71).

## Referenca
[Križaj, Janez; Dobrišek, Simon. "Validacija zvočnih posnetkov pri izdelavi podatkovne zbirke za učenje razpoznavalnika slovenščine", 30. Mednarodna Elektrotehniška in računalniška konferenca, Portorož, Slovenija, pp. 382-385, 2021](https://erk.fe.uni-lj.si/2021/papers/krizaj(validacija_zvocnih).pdf)
