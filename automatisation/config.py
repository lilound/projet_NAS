import json

with open ("intent.json", "r") as f:
    intent_json = f.read()

data = json.loads(intent_json)

for router_name, router_info in data["routeurs"].items():
    config = []
    config.append(f"hostname {router_name}")
    
    lb_ip = router_info["loopback"].split('/')[0]
    config.append("interface Loopback0")
    config.append(f" ip address {lb_ip} 255.255.255.255")
    config.append(" exit")
    
    ospf_networks = [f"network {lb_ip} 0.0.0.0 area 0"]
    
    for link in data["links"]:
        if link["routeur_a"] == router_name:
            iface, local_ip = link["interface_a"], link["sous_res"].replace(".0/30", ".1")
            net_addr = link["sous_res"].split('/')[0]
        elif link["routeur_b"] == router_name:
            iface, local_ip = link["interface_b"], link["sous_res"].replace(".0/30", ".2")
            net_addr = link["sous_res"].split('/')[0]
        else:
            continue
            
        config.append(f"interface {iface}")
        config.append(f" ip address {local_ip} 255.255.255.252")
        if data["mpls"]["ldp"]:
            config.append(" mpls ip")
        config.append(" no shutdown")
        config.append(" exit")
        
        ospf_networks.append(f" network {net_addr} 0.0.0.3 area 0")

    # Configuration OSPF
    config.append("router ospf 1")
    config.append(f" router-id {router_info['routeurID']}")
    config.extend(ospf_networks)
    config.append(" end\n")

    # Affichage du résultat pour chaque routeur
    print(f"--- CONFIGURATION POUR {router_name} ---")
    print("\n".join(config))