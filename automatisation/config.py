import json
import time
import telnetlib
from ipaddress import IPv4Network
from gns3fy import Gns3Connector, Project, Node
from concurrent.futures import ThreadPoolExecutor

GNS3_URL = "http://127.0.0.1:3080"
TELNET_DELAY = 0.3
PROJECT_NAME = "structure_vide"

with open("intent.json", "r", encoding="utf-8") as f:
    data = json.load(f)

CORE_BGP_AS = int(data["AS"]["CORE"]["asnumber"])

server = Gns3Connector(url=GNS3_URL)
project = Project(name=PROJECT_NAME, connector=server)
project.get()
project.open()
project.get_nodes()



def send(tn, cmd, delay=TELNET_DELAY):
    tn.write((cmd + "\r\n").encode("ascii", errors="ignore"))
    time.sleep(delay)


def ensure_started(node):
    node.get()
    if node.status != "started":
        node.start()
        time.sleep(2)
        node.get()


def host_ip_from_subnet(subnet_str, host_id):
    net = IPv4Network(subnet_str, strict=False)
    return str(net.network_address + host_id)


def mask_from_prefix(prefix_str):
    return str(IPv4Network(prefix_str, strict=False).netmask)


def get_network_address(prefix_str):
    return str(IPv4Network(prefix_str, strict=False).network_address)


def get_links_for_router(router_name):
    links = []
    for link in data["links"]:
        if link["routeur_a"] == router_name:
            links.append({
                "iface": link["interface_a"],
                "peer": link["routeur_b"],
                "peer_iface": link["interface_b"],
                "subnet": link["sous_res"],
                "local_ip": host_ip_from_subnet(link["sous_res"], 1),
                "peer_ip": host_ip_from_subnet(link["sous_res"], 2),
            })
        elif link["routeur_b"] == router_name:
            links.append({
                "iface": link["interface_b"],
                "peer": link["routeur_a"],
                "peer_iface": link["interface_a"],
                "subnet": link["sous_res"],
                "local_ip": host_ip_from_subnet(link["sous_res"], 2),
                "peer_ip": host_ip_from_subnet(link["sous_res"], 1),
            })
    return links


def get_router(router_name):
    return data["routeurs"][router_name]


def get_router_type(router_name):
    return data["routeurs"][router_name]["type"]


def get_router_as_name(router_name):
    return data["routeurs"][router_name]["as"]


def get_router_asn(router_name):
    as_name = get_router_as_name(router_name)
    return int(data["AS"][as_name]["asnumber"])


def get_loopback_ip(router_name):
    return data["routeurs"][router_name]["loopback"].split("/")[0]


def is_core_link(local_router, peer_router):
    return get_router_type(local_router) in ("P", "PE") and get_router_type(peer_router) in ("P", "PE")


def get_pe_vrfs(pe_name):
    vrfs = set()
    for link in get_links_for_router(pe_name):
        peer = link["peer"]
        if get_router_type(peer) == "CE":
            vrfs.add(get_router_as_name(peer))
    return sorted(vrfs)


def rd_for(vrf_name):
    for name, vrf in data["vrfs"].items():
        if name == vrf_name:
            return vrf["rd"]
    return "65000:100"


def rt_for(vrf_name):
    for name, vrf in data["vrfs"].items():
        if name == vrf_name:
            return vrf["rt_export"]
    return "65000:100"


def clear_prompt(tn):
    send(tn, "", delay=1)
    send(tn, "", delay=1)


# Config de base

def configure_common_base(tn, router_name):
    router_info = get_router(router_name)
    loopback_ip = get_loopback_ip(router_name)

    send(tn, "enable")
    send(tn, "configure terminal")
    send(tn, f"hostname {router_name}")
    send(tn, "ip cef")
    send(tn, "no ip domain lookup")

    send(tn, "interface Loopback0")
    send(tn, f" ip address {loopback_ip} 255.255.255.255")
    send(tn, " no shutdown")
    send(tn, " exit")


def configure_core_igp_and_mpls(tn, router_name):
    router_info = get_router(router_name)
    loopback_ip = get_loopback_ip(router_name)

    ospf_networks = [f"network {loopback_ip} 0.0.0.0 area 0"]

    for link in get_links_for_router(router_name):
        peer = link["peer"]
        if not is_core_link(router_name, peer):
            continue

        mask = mask_from_prefix(link["subnet"])
        net_addr = get_network_address(link["subnet"])

        send(tn, f"interface {link['iface']}")
        send(tn, f" ip address {link['local_ip']} {mask}")
        send(tn, " mpls ip")
        send(tn, " no shutdown")
        send(tn, " exit")

        ospf_networks.append(f"network {net_addr} 0.0.0.3 area 0")

    send(tn, "router ospf 1")
    send(tn, f" router-id {router_info['routeurID']}")
    for net in ospf_networks:
        send(tn, f" {net}")
    send(tn, " exit")


# ---------------- PE config ----------------

def configure_pe_vrfs(tn, router_name):
    for vrf_name in get_pe_vrfs(router_name):
        rd = rd_for(vrf_name)
        rt = rt_for(vrf_name)

        send(tn, f"vrf definition {vrf_name}")
        send(tn, f" rd {rd}")
        send(tn, f" route-target export {rt}")
        send(tn, f" route-target import {rt}")
        send(tn, " address-family ipv4")
        send(tn, " exit-address-family")
        send(tn, " exit")


def configure_pe_ce_interfaces(tn, router_name):
    for link in get_links_for_router(router_name):
        peer = link["peer"]
        if get_router_type(peer) != "CE":
            continue

        vrf_name = get_router_as_name(peer)
        mask = mask_from_prefix(link["subnet"])

        send(tn, f"interface {link['iface']}")
        send(tn, f" vrf forwarding {vrf_name}")
        send(tn, f" ip address {link['local_ip']} {mask}")
        send(tn, " no shutdown")
        send(tn, " exit")


def configure_pe_bgp(tn, router_name):
    other_pe = "PE2" if router_name == "PE1" else "PE1"
    other_lb = get_loopback_ip(other_pe)

    send(tn, f"router bgp {CORE_BGP_AS}")
    send(tn, " bgp log-neighbor-changes")
    send(tn, f" neighbor {other_lb} remote-as {CORE_BGP_AS}")
    send(tn, f" neighbor {other_lb} update-source Loopback0")

    send(tn, " address-family vpnv4")
    send(tn, f"  neighbor {other_lb} activate")
    send(tn, f"  neighbor {other_lb} send-community extended")
    send(tn, " exit-address-family")

    for link in get_links_for_router(router_name):
        peer = link["peer"]
        if get_router_type(peer) != "CE":
            continue

        vrf_name = get_router_as_name(peer)
        ce_asn = get_router_asn(peer)

        send(tn, f" address-family ipv4 vrf {vrf_name}")
        send(tn, f"  neighbor {link['peer_ip']} remote-as {ce_asn}")
        send(tn, f"  neighbor {link['peer_ip']} activate")
        send(tn, " exit-address-family")

    send(tn, " exit")


# ---------------- CE config ----------------

def configure_ce_router(tn, router_name):
    ce_asn = get_router_asn(router_name)
    loopback_ip = get_loopback_ip(router_name)

    pe_link = None
    for link in get_links_for_router(router_name):
        if get_router_type(link["peer"]) == "PE":
            pe_link = link
            break

    if pe_link is None:
        return

    mask = mask_from_prefix(pe_link["subnet"])

    send(tn, f"interface {pe_link['iface']}")
    send(tn, f" ip address {pe_link['local_ip']} {mask}")
    send(tn, " no shutdown")
    send(tn, " exit")

    send(tn, f"router bgp {ce_asn}")
    send(tn, " bgp log-neighbor-changes")
    send(tn, f" neighbor {pe_link['peer_ip']} remote-as {CORE_BGP_AS}")
    send(tn, " address-family ipv4")
    send(tn, f"  network {loopback_ip} mask 255.255.255.255")
    send(tn, f"  neighbor {pe_link['peer_ip']} activate")
    send(tn, f"  neighbor {pe_link['peer_ip']} allowas-in")
    send(tn, " exit-address-family")
    send(tn, " exit")


# ---------------- Finalize ----------------

def finalize_config(tn):
    send(tn, "end")
    if data["parameters"]["write"]:
        send(tn, "write memory", delay=0.8)
    send(tn, "", delay=1)


# ---------------- Main router config ----------------

def configure_router(node, router_name, router_info):
    tn = telnetlib.Telnet(node.console_host, node.console)
    time.sleep(5)
    clear_prompt(tn)

    # au cas où IOS demande le setup initial
    send(tn, "no", delay=1)
    clear_prompt(tn)

    configure_common_base(tn, router_name)

    router_type = router_info["type"]

    if router_type in ("P", "PE"):
        configure_core_igp_and_mpls(tn, router_name)

    if router_type == "PE":
        configure_pe_vrfs(tn, router_name)
        configure_pe_ce_interfaces(tn, router_name)
        configure_pe_bgp(tn, router_name)

    if router_type == "CE":
        configure_ce_router(tn, router_name)

    finalize_config(tn)
    tn.close()


def configure_worker(router_name, router_info):
    node = Node(project_id=project.project_id, name=router_name, connector=server)
    node.get()
    ensure_started(node)
    configure_router(node, router_name, router_info)
    print(f"Configuration terminée pour {router_name}")


def main():
    with ThreadPoolExecutor(max_workers=5) as executor:
        for router_name, router_info in data["routeurs"].items():
            executor.submit(configure_worker, router_name, router_info)
            time.sleep(0.5)

    print("Configuration automatique terminée.")


if __name__ == "__main__":
    main()