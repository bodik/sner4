# Sner scheduler Nacelnik.Mk1

Návrh algoritmu pro scheduler Nacelnik.Mk1.

## Datová struktura

![Datová struktura](sner_scheduler_ratelimiting.png "Datová struktura")

* datová struktura je zaměřená hlavně na optimalizaci přidělování úloh (enqueue a job_dobe dělají špinavou práci, ale pokud není počet Queue Tasků moc velký, je to zanedbatelná práce). 
* globální struktura má seznam zpracovávaných sítí a u každé si pamatuje její maximální limit a aktuální počet zpracovávaných IP adres
* Každá Queue Task má svoji strukturu, priorita je určena přes tabulku Priorities (takže jde snadno procházet Queues v pořadí priorit)
* Každá Queue Task struktura má 
	* pole network, kde jsou jednotlivé podsítě a link na další pole, kde jsou příslučné IP adresy ke zpracování (resp. zde jejich lokální část, páč společná část je už v network - mohlo by být i jako text obecně vzato nebo tam může být kompletní IP adresa)
	* index ready, který obsahuje linky na podsítě, které nejsou zaříznuty rate limitingem

## Pracovní postupy

**enqueue**

* je určena fronta a seznam IP adres
* přidat novou podsíť pro frontu, pokud neexistuje
* podsíť naplnit IP adresami (nebo jejich lokální částí)

**get\_assignment**

* je určen seznam front, které žádající agent umí zpracovat
* Při hledání vhodné IP adresy ke zpracování je tedy postup stejně výpočetně náročný bez ohledu na počet sítí nebo IP adres (záleží jen na počtu front, kvůli for cyklu)
	* najít podle priority první frontu, kterou agent umí zpracovat a jejíž index ready je neprázdný (tj. for a dvě porovnání)
	* vybrat náhodnou podsíť z ready sítí vybrané fronty (randint) 
	* vybrat náhodný prvek z local_part (a spojit network+local) z vybrané podstítě (randint)
* při předání prvku ke zpracování
	* smazát ze seznamu local
	* pokud byl poslední v network, smazat příslušnou podsíť a odkaz z ready indexu
* upravit globální strukturu
	* zvýšit příslušný `in_progress` 
	* pokud `in_progress` == `limit` (bylo dosaženo maximálního limitu)
		* projít všechny fronty
			* pokud je zpracovávaná podsítˇ v ready indexu, zrušit odkaz z ready indexu

**job\_done**

* upravit globální strukturu
	* snížit příslušný `in_progress`
	* pokud je `in_progress` roven nule možno smazat (a příště se zase založí, nebo nechat a smazat nulové položky jen jednou za čas? aby se nehromadily nepoužívané sítě)
	* pokud je `in_progress + 1` roven `limit` (snižovalo se z max limitu)
		* projít všechny fronty
			* pokud je v seznamu front zpracovávaná podsíť, přidat na ni odkaz z ready indexu 

## Poznámky k implementaci a optimalizaci

* v pythonu by to by byly pole a slovníky (slabý článek je vyndání prvku z náhodné pozice pole -- možná by šlo vybraný prvek přepsat posledním a ten poslední smáznout, protože na pořadí nezáleží, stejně je randomizované, a zkrácení pole je rychlá operace)
* u databáze by to chtělo mít asi částečně samostatné tabulky (nějako jako v FTASu nebo jinech NetFlow SW, tam je taky co hodina samostatná tabulka, i když má stejný sloupečky. Tak mít třeba pro každou frontu a její podsíť samostatnou tabulku, aby se ten select nezbláznil), i když možná podceňuju postgresql a nějaké vhodné indexování bude stejně výkonné.
* IP adresu mám rozdělenou na síť a lokální část, páč mi přišlo škoda opakovat stejná data znova, ale je to jen šetření místa, není nutné.
