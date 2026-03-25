import json
import time
import telnetlib
from gns3fy import Gns3Connector, Project, Node
from concurrent.futures import ThreadPoolExecutor

GNS3_URL = "http://127.0.0.1:3080"
TELNET_DELAY = 0.3

with open("intent.json", "r") as f:
    data = json.load(f)

server = Gns3Connector(url=GNS3_URL)
project = Project(name="structure_vide", connector=server)
project.get()
project.open()
project.get_nodes()


# utils

def send(tn, cmd):
    tn.write((cmd + "\r\n").encode("ascii"))
    time.sleep(TELNET_DELAY)


def ensure_started(node):
    node.get()
    if node.status != "started":
        node.start()
        time.sleep(2)




# config routeur



def configure_router(node, router_name, router_info):
    tn = telnetlib.Telnet(node.console_host, node.console)
    time.sleep(10)

    send(tn, "")
    send(tn, "no")
    send(tn, "\n")
    time.sleep(10)
    send(tn, "enable")
    send(tn, "configure terminal")

    # hostname
    send(tn, f"hostname {router_name}")

    # CEF obligatoire MPLS
    send(tn, "ip cef")

    # loopback
    lb_ip = router_info["loopback"].split('/')[0]
    send(tn, "interface Loopback0")
    send(tn, f" ip address {lb_ip} 255.255.255.255")
    send(tn, " no shutdown")
    send(tn, " exit")

    ospf_networks = [f"network {lb_ip} 0.0.0.0 area 0"]

    # interfaces
    for link in data["links"]:
        if link["routeur_a"] == router_name:
            iface = link["interface_a"]
            local_ip = link["sous_res"].replace(".0/30", ".1")
            net_addr = link["sous_res"].split('/')[0]

        elif link["routeur_b"] == router_name:
            iface = link["interface_b"]
            local_ip = link["sous_res"].replace(".0/30", ".2")
            net_addr = link["sous_res"].split('/')[0]

        else:
            continue

        send(tn, f"interface {iface}")
        send(tn, f" ip address {local_ip} 255.255.255.252")

        # MPLS si activé
        if data.get("mpls", {}).get("ldp"):
            send(tn, " mpls ip")

        send(tn, " no shutdown")
        send(tn, " exit")

        ospf_networks.append(f" network {net_addr} 0.0.0.3 area 0")

    # OSPF
    send(tn, "router ospf 1")
    send(tn, f" router-id {router_info['routeurID']}")
    for net in ospf_networks:
        send(tn, f" {net}")
    send(tn, " exit")

    # fin
    send(tn, "end")
    send(tn, "write memory")
    send(tn, "y")

    tn.close()

def configure_worker(router_name, router_info):
    node = Node(project_id=project.project_id, name=router_name, connector=server)
    node.get()

    ensure_started(node)
    configure_router(node, router_name, router_info)

    print(f"Config routeur {router_name} terminée")


def main():
    max_threads = 5 

    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        for router_name, router_info in data["routeurs"].items():
            executor.submit(configure_worker, router_name, router_info)
            time.sleep(0.5)

    print("Configuration MPLS terminée.")



if __name__ == "__main__":
    main()