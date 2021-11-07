![GUI](gui.jpg)
# Validacija posnetkov govora

Aplikacija za validacijo govornih posnetkov, ki omogoča preverjanje skladnosti posnetkov z referenčnim besedilom in ustreznosti začetnih/končnih premorov ter glasnosti.

## Namestitev

Koda je spisana v programskem jeziku Python 3. Zahtevane knjižnice se namesti z ```pip install -r requirements.txt```. 

V izogib težavam pri namestitvi zahtevanih programskih knjižnic sta pripravljeni izvršljivi datoteki za okolje [Windows](https://unilj-my.sharepoint.com/:u:/g/personal/janezkrfe_fe1_uni-lj_si/EUk8rVw1B7lGi_FZfrXHtBcB6pLBJAhV2PHNZpCCf5fFSg?e=LhBbgf) in [Linux](https://unilj-my.sharepoint.com/:u:/g/personal/janezkrfe_fe1_uni-lj_si/EasNMx8l5QNGg8U6TQrHyscB9Q-oWLSscv7kmCS_ElhJBQ?e=sAlL71).

## Postopek uporabe

Aplikacijo se zažene z ukazom ```python audio_validation.py``` pri čemer se prikaže grafični vmesnik, v katerem najprej navedemo vhodne parametre, kot je pot do direktorija s posnetki, pot do datoteke XLSX z besedilom in način delovanja (ročni/samodejni/polsamodejni). Po vnosu vhodnih parametrov s pritiskom na tipko "Zaženi" pričnemo z validacijo posnetkov. Priporočena je izbira polsamodejnega načina (izbran naj bo prag WER=0), ki omogoča ročno preverjanje vseh posnetkov, ki niso prestali samodejnega preverjanja.

Prvi korak postopka validacije predstavlja preverjanje ustreznosti formata zapisa (mono kanal, frekvenca vzorčenja 44,1 kHz, datoteka wav, podtip PCM_16). Ta korak se vedno izvede samodejno ne glede na izbiro načina delovanja.

Drugi korak predstavlja preverjanje skladnosti z referenčnim besedilom. V ta namen je v spodnjem levem delu grafičnega vmesnika okvir, kjer se izpiše referenčno besedilo in v primeru izbire (pol)samodejnega načina tudi samodejno razpoznano besedilo, vključno s podano vrenostjo metrike WER. V ročnem načinu in v primeru zavrnitve samodejnega razpoznavalnika v polsamodejnem načinu, se posnetek obenem tudi predvaja in na ta način omogoča manualno oceno skladnosti posnetka in referenčnega besedila. Pri tem so v pomoč barvno kodirane razlike med referenčnim in samodejno razpoznanim besedilom. Posnetek odobrimo/zavrnemo s pritiskom na ustrezno tipko, pri čemer se nam v primeru zavrnitve odpre pojavno okno, ki omogoča vpis pojasnila zakaj smo posnetek zavrnili. Predhodno lahko kliknemo tudi na gumb "Opomba", kjer prav tako lahko vpišemo komentar ne glede na to ali bomo posnetek zavrnili/odobrili. Opisi zavrnitev in opombe se shranijo v ustrezne celice v izhodni XLSX datoteki. S pritiskom na gumb "Ponovitev" se posnetek še enkrat predvaja.

V zadnjem koraku se preveri skladnost začetnih/končnih premorov in ustreznost glasnosti posnetka. V pomoč nam je sredinski okvir v grafičnem vmesniku, kjer se pri ročnem in polsamodejnem načinu izrišejo trije grafi, ki so v pomoč pri oceni ustreznosti premorov in glasnosti. Aplikacija vsebuje samodejno oceno premorov in glasnosti, zato so na grafih tihi in govorjeni deli posnetkov ustrezno barvno kodirani. Začetni in končni premor morata biti v območju med 0,5 s in 1,0 s (belo obarvano ozadje na zgornjem grafu), medtem ko naj bi bila glasnost posnetka v večji meri nad -20 dBFS. Tudi v tem koraku posnetek odobrimo ali zavrnemo s pritiskom na ustrezno tipko.

## Pomožne skripte

Skripta [xlsx2txt.py](xlsx2txt.py) iz vhodne datoteke xlsx z označenimi zavrnjenimi posnetki tvori tekstovno datoteko s seznamom zavrnjenih posnetkov.

Skripta [check_val.py](check_val.py) preveri ujemanje števila posnetkov ( #odobreni = #izvorni - #zavrnjeni) v lokalnih mapah in pripadajočih mapah na strežniku.

## Referenca
[Križaj, Janez; Dobrišek, Simon. "Validacija zvočnih posnetkov pri izdelavi podatkovne zbirke za učenje razpoznavalnika slovenščine", 30. Mednarodna Elektrotehniška in računalniška konferenca, Portorož, Slovenija, pp. 382-385, 2021](https://erk.fe.uni-lj.si/2021/papers/krizaj(validacija_zvocnih).pdf)
