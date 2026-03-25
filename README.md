# projet_NAS

## infos qu'on a eu en cours (tp)

* conf ne peut pas être minimaliste
* **au moins** une chaîne de 4 routeurs, max **10 routeurs** apparement c'est pas mal
* implémenter le pen ultimate hop ou l'observer : donc faire en sorte d'avoir une topologie qui permet ça (d'où les 4 routeurs à la chaîne)
* on veut que le provider MPLS au milieu (avec chaîne de 4 routeurs) puisse provider un VPN à ses clients

entre 5 et 10 routeurs dont au moins 2 PE avec au moins 1 et 2 routeurs entre les deux qui font le lien , on peut en ajouter après pour exos bonus, 2 routeurs CE (customer edge) des AS clients liés aux PE BGP entre client et provider. MPLS dans AS provider. besoin d'aussi ospf

mpls ajouter label au pe entrée et enlever à l'avant dernier routeur (dernier avant PE sortie)

!["](schema.png "")

## BONUS : 
* faire IPV6 instead of IPV4 
* add QoS

# TUTOOOOO

1. Installer Python 3.11

Télécharger Python 3.11 :
https://www.python.org/downloads/release/python-3110/

Pendant l’installation, cocher “Add Python to PATH”

Vérifier :

py -3.11 --version

2. Installer les dépendances
py -3.11 -m pip install gns3fy

3. Préparer GNS3

Ouvrir structure_vide

!["](topologie.png "")

5. Lancer le script

Dans le dossier automatisation :
py -3.11 config.py

## les tâches et la répartition 

### petit conseil de pfr
 attention, la reachability au client doit être entière : souvent les élèves se trompent et n'assurent QUE la connexion au premier lien du CE : donc bien vérifier que ça ping DANS le CE (depuis qqch qui est le PE)



commande : bgp allow as in  