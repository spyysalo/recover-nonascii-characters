# Recover non-ASCII characters

Tool for recovering non-ASCII characters in text where they have been replaced with the [Unicode replacement character](https://en.wikipedia.org/wiki/Specials_(Unicode_block)#Replacement_character) (�).

Originally written for recovering usable text from the [Usenet SFnet archive](https://archive.org/download/usenet-sfnet). See also https://github.com/spyysalo/usenet-mbox-tools .

## Quickstart

Get 1- and 2-gram counts in subset of the [Finnish Internet Parsebank](https://turkunlp.org/finnish_nlp.html#parsebank) (**NOTE**: 3.7G file)

```
wget https://a3s.fi/parsebank/ngram-counts.txt
```

Apply to [example file](https://github.com/spyysalo/recover-nonascii-characters/blob/main/examples/sfnet.atk.ms-windows.palvelimet.txt) (**NOTE** slow startup, uses a lot of memory)

```
python3 replace_replacement_chars.py ngram-counts.txt examples/sfnet.atk.ms-windows.palvelimet.txt
```

Expected output

```
> Kun Windows Server 2008:iin ottaa VPN-yhteyden, toimii se niinkuin
> pitääkin mutta samanaikaisesti koneen oma lähiverkko ei enää toimi
> eik� koneella pääsee samanaikaisesti esim sähköpostiin tai
> www-sivuille. Kun VPN-yhteyden katkaisee niin taas toimii netti. Eli
> mistä kannattaisi alkaa etsimään vikaa?

Kyseessä ei todennäköisesti ole vika vaan ominaisuus.
Ja tällä ominaisuudella suojellaan sitä serveriä silt� että siitä työaseman
kautta pääsisi joku intternetistä sinne serverille.
Eli että se ty�asema toimisi ikäänkuin reitittimenä.
```

Lower threshold, ignoring n-grams that have irregular capitalization (potentially arising from encoding errors):

```
python3 replace_replacement_chars.py -p 0.9 -i ~/FinNLP/ngram-counts.txt examples/sfnet.atk.ms-windows.palvelimet.txt 
```

Expected output

```
> Kun Windows Server 2008:iin ottaa VPN-yhteyden, toimii se niinkuin
> pitääkin mutta samanaikaisesti koneen oma lähiverkko ei enää toimi
> eikä koneella pääsee samanaikaisesti esim sähköpostiin tai
> www-sivuille. Kun VPN-yhteyden katkaisee niin taas toimii netti. Eli
> mistä kannattaisi alkaa etsimään vikaa?

Kyseessä ei todennäköisesti ole vika vaan ominaisuus.
Ja tällä ominaisuudella suojellaan sitä serveriä siltä että siitä työaseman
kautta pääsisi joku intternetistä sinne serverille.
Eli että se työasema toimisi ikäänkuin reitittimenä.
```
