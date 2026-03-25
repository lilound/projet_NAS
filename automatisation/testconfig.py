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

# =========================
# UTILS
# =========================

def send(tn, cmd):
    tn.write((cmd + "\r\n").encode("ascii"))
    time.sleep(TELNET_DELAY)

def ensure_started(node):
    node.get()
    if node.status != "started":
        node.start()
        time.sleep(5)

# =========================
# INIT ROUTER
# =========================

def init_router(tn):
    time.sleep(10)
    tn.write(b"\r\n")
    time.sleep(1)
    tn.write(b"no\r\n")
    time.sleep(1)
    tn.write(b"\r\n")
    time.sleep(5)

    send(tn, "enable")
    send(tn, "configure terminal")

# =========================
# BASE CONFIG
# =========================

def configure_base(tn, router_name, router_info):
    send(tn, f"hostname {router_name}")
    send(tn, "ip cef")

    lb_ip = router_info["loopback"].split('/')[0]

    send(tn, "interface Loopback0")
    send(tn, f" ip address {lb_ip} 255.255.255.255")
    send(tn, " no shutdown")
    send(tn, " exit")

# =========================
# INTERFACES
# =========================

def configure_interfaces(tn, router_name):
    for link in data["links"]:
        if link["routeur_a"] == router_name:
            iface = link["interface_a"]
            local_ip = link["sous_res"].replace(".0/30", ".1")

        elif link["routeur_b"] == router_name:
            iface = link["interface_b"]
            local_ip = link["sous_res"].replace(".0/30", ".2")

        else:
            continue

        send(tn, f"interface {iface}")
        send(tn, f" ip address {local_ip} 255.255.255.252")

        # MPLS uniquement pour CORE
        if data.get("mpls", {}).get("ldp"):
            send(tn, " mpls ip")

        send(tn, " no shutdown")
        send(tn, " exit")

# =========================
# CORE (P + PE)
# =========================

def configure_core(tn, router_name):
    router_id = data["routeurs"][router_name]["routeurID"]

    send(tn, "router ospf 1")
    send(tn, f" router-id {router_id}")

    for link in data["links"]:
        if link["routeur_a"] == router_name or link["routeur_b"] == router_name:
            net_addr = link["sous_res"].split('/')[0]
            send(tn, f" network {net_addr} 0.0.0.3 area 0")

    send(tn, " exit")

# =========================
# CE CONFIG
# =========================

def configure_ce(tn, router_name, router_info):
    send(tn, "router ospf 10")
    send(tn, f" router-id {router_info['routeurID']}")

    lb_ip = router_info["loopback"].split('/')[0]
    send(tn, f" network {lb_ip} 0.0.0.0 area 0")

    for link in data["links"]:
        if link["routeur_a"] == router_name or link["routeur_b"] == router_name:
            net_addr = link["sous_res"].split('/')[0]
            send(tn, f" network {net_addr} 0.0.0.3 area 0")

    send(tn, " exit")

# =========================
# PE CONFIG (placeholder)
# =========================

def configure_pe(tn, router_name, router_info):
    # CORE OSPF
    configure_core(tn, router_name)

    # FUTUR :
    # - VRF
    # - MP-BGP
    # - OSPF VRF

# =========================
# SAVE
# =========================

def save_config(tn):
    send(tn, "end")
    send(tn, "write memory")

# =========================
# MAIN CONFIG ROUTER
# =========================

def configure_router(node, router_name, router_info):
    tn = telnetlib.Telnet(node.console_host, node.console)

    init_router(tn)
    configure_base(tn, router_name, router_info)
    configure_interfaces(tn, router_name)

    if router_info["type"] == "P":
        configure_core(tn, router_name)

    elif router_info["type"] == "CE":
        configure_ce(tn, router_name, router_info)

    elif router_info["type"] == "PE":
        configure_pe(tn, router_name, router_info)

    save_config(tn)
    tn.close()

# =========================
# THREAD WORKER
# =========================

def configure_worker(router_name, router_info):
    node = Node(project_id=project.project_id, name=router_name, connector=server)
    node.get()

    ensure_started(node)
    configure_router(node, router_name, router_info)

    print(f"Config routeur {router_name} terminée")

# =========================
# MAIN
# =========================

def main():
    max_threads = 5

    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        for router_name, router_info in data["routeurs"].items():
            executor.submit(configure_worker, router_name, router_info)
            time.sleep(0.5)

    print("Configuration terminée.")

if __name__ == "__main__":
    main()

