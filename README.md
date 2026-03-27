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

# Commandes de test 

### Couche 1 — OSPF (sur PE1, P1, P2, P3, PE2) :

``` show ip ospf neighbor ```
``` show ip route ospf ```

Attendu : tous les routeurs core voient leurs voisins en état FULL, et les loopbacks 1.1.1.1 à 5.5.5.5 apparaissent dans la table de routage.

### Couche 2 — MPLS/LDP (sur PE1 et PE2 surtout) :

``` show mpls ldp neighbor ```
``` show mpls forwarding-table ```

Attendu : sessions LDP Operational sur chaque interface core, et des entrées de label pour les loopbacks des deux PE.

### Couche 3 — BGP VPNv4 (sur PE1 et PE2) :

``` show bgp vpnv4 unicast all summary ``` 
``` show bgp vpnv4 unicast all ``` 

Attendu : la session iBGP entre 1.1.1.1 et 5.5.5.5 est Established, et les loopbacks des 4 CE apparaissent avec un label VPN et le bon RT (65000:10 ou 65000:20).

### Couche 4 — Tables VRF (sur PE1 et PE2) :

``` show ip route vrf CLIENT_A ``` 
``` show ip route vrf CLIENT_B ``` 

Attendu : chaque PE connaît les deux loopbacks de chaque client (les siens via eBGP direct, ceux du PE distant via VPNv4).

### Couche 5 — End-to-end (depuis PE1 en mode VRF) :

``` ping vrf CLIENT_A 12.12.12.12 source Loopback0 ``` 
``` ping vrf CLIENT_B 24.24.24.24 source Loopback0 ``` 
``` ping vrf CLIENT_A 23.23.23.23 source Loopback0   ← doit échouer ``` 

Le dernier ping vérifie l'isolation : CLIENT_A ne doit pas pouvoir joindre CLIENT_B.

!["](image.png "")

### PARTIE 4B 

rajouter un client bleu qui peut parler a vert et rouge, mais rouge ne peut parler qu'à vert et vert ne peut parler quà bleu -> ajouter un autre client et établir ça 
Puis, route reflector
puis, rsvp pr joindre l'internet global et les vpns
avoir un code propre 