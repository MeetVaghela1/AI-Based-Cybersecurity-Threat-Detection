"""attack_info.py — plain-language explanations of every attack type.

This file is "static knowledge": it powers the GET /attack-info endpoint so
the frontend can show a beginner-friendly explanation of whatever the model
flags.  Everything here is written for someone who has never heard of these
attacks before.

The keys match the coarse categories our models predict:
  NSL-KDD:      Normal, DoS, Probe, R2L, U2R
  CICIDS2017:   Normal, DDoS, PortScan, Brute Force, Web Attack, Botnet,
                Infiltration, Heartbleed
"""

from __future__ import annotations

ATTACK_INFO = {
    "Normal": {
        "name": "Normal traffic",
        "category": "Normal",
        "description": "Regular, benign network traffic — a user browsing the web, "
                       "checking email, or transferring files. No attack behaviour detected.",
        "how_it_works": "The model compares the connection's characteristics "
                        "(duration, bytes sent, ports used, ...) against the patterns it "
                        "learned for normal traffic. When nothing unusual stands out, it "
                        "classifies the flow as normal.",
        "indicators": "No red flags: ordinary sizes, timings and protocol usage.",
        "impact": "None — this is the traffic we want to let through.",
        "defense": "Keep monitoring; normal flows are the baseline every alarm is "
                   "compared against.",
        "example": "A user opening a website and downloading a PDF.",
    },
    "DoS": {
        "name": "Denial of Service (DoS)",
        "category": "DoS",
        "description": "One source floods a service with so many requests that it "
                       "becomes too busy to answer legitimate users.",
        "how_it_works": "The attacker fires a huge number of connection attempts at "
                        "the victim. The server spends all its resources answering "
                        "junk, so real customers time out.",
        "indicators": "Thousands of short connections from one address, unusually "
                      "high packet counts, many connections that never complete "
                      "properly.",
        "impact": "Websites and services go down; lost revenue and customers. The "
                  "classic 'make it unusable' attack.",
        "defense": "Rate limiting, connection throttling, firewalls, and — for big "
                   "attacks — CDN/blackhole filtering.",
        "example": "SYN flood: the attacker sends 'let's connect' messages but never "
                   "completes the handshake, exhausting the server's queue.",
    },
    "Probe": {
        "name": "Probe / Network Scan",
        "category": "Probe",
        "description": "Reconnaissance: an attacker maps out what hosts, services and "
                       "open ports exist on your network before deciding how to attack.",
        "how_it_works": "The scanner sends probes to many addresses and ports and "
                        "watches who responds. This builds a map of your attack surface.",
        "indicators": "One source connecting to many different ports or hosts, "
                      "unusual port-sweeping patterns.",
        "impact": "By itself harmless, but it is the recon step that enables nearly "
                  "every other attack — a warning sign of intent.",
        "defense": "Intrusion detection that flags scan patterns, blocking IPs that "
                   "scan, keeping only necessary ports open.",
        "example": "Port sweep: trying port 22, 80, 443, ... on every machine in a "
                   "subnet in seconds.",
    },
    "R2L": {
        "name": "Remote-to-Local (R2L)",
        "category": "R2L",
        "description": "An attacker who does NOT have an account gains access to a "
                       "local machine from across the network, e.g. by guessing "
                       "passwords or exploiting a remote service.",
        "how_it_works": "The attacker targets a service (mail, FTP, web) and either "
                        "breaks into it directly or cracks weak credentials until "
                        "they get a local foothold.",
        "indicators": "Bursts of failed logins followed by success, logins from "
                      "unexpected addresses, unusual remote access.",
        "impact": "The attacker now has a machine on your network from which they "
                  "can move laterally to reach more valuable systems.",
        "defense": "Strong passwords, multi-factor authentication, patching remote "
                   "services, monitoring login behaviour.",
        "example": "Dictionary attack against an FTP login that eventually succeeds.",
    },
    "U2R": {
        "name": "User-to-Root (U2R)",
        "category": "U2R",
        "description": "A user who already has a normal account escalates their "
                       "privileges to root/administrator.",
        "how_it_works": "The attacker exploits a software bug (classic: buffer "
                        "overflow) to run code with higher privileges, or tricks the "
                        "system into giving admin rights.",
        "indicators": "Behaviour typical of exploits (overlong inputs, unusual "
                      "system calls), commands run with elevated rights.",
        "impact": "Full compromise: the attacker controls the machine and can read "
                  "anything, install backdoors, or attack the rest of the network.",
        "defense": "Keep software patched, run services with least privilege, "
                   "kernel/system hardening, log privilege changes.",
        "example": "A malformed login request that overflows a buffer and executes "
                   "code as root.",
    },
    "DDoS": {
        "name": "Distributed Denial of Service (DDoS)",
        "category": "DDoS",
        "description": "Like DoS, but the flood comes from MANY machines at once "
                       "(often a botnet), so blocking a single IP does nothing.",
        "how_it_works": "Thousands of infected devices (a botnet) send traffic to "
                        "the victim simultaneously, saturating bandwidth and servers.",
        "indicators": "Traffic arriving from many distinct sources, all aimed at "
                      "one target, huge and sudden volume spikes.",
        "impact": "Services knocked offline at scale; one of the hardest attacks to "
                  "defend because the traffic looks distributed and legitimate.",
        "defense": "Traffic scrubbing services (cloud DDoS protection), anycast "
                   "routing, rate limiting per source.",
        "example": "A reflection attack that amplifies small queries into a "
                   "giant flood aimed at the victim.",
    },
    "PortScan": {
        "name": "Port Scan",
        "category": "PortScan",
        "description": "Systematically probing which TCP/UDP ports are open on a "
                       "machine to discover what services it runs.",
        "how_it_works": "The scanner sends a connection attempt to each port; an "
                        "open port answers, revealing the service behind it.",
        "indicators": "A source trying many ports on the same host in a short time, "
                      "including uncommon ports.",
        "impact": "Reconnaissance that hands the attacker a list of services to "
                  "attack — the opening move of most intrusions.",
        "defense": "Firewall rules that block scanning IPs, shutting unused ports, "
                   "intrusion detection on scan signatures.",
        "example": "nmap scanning 1-1000 ports of a server to find an open SSH port "
                   "to brute-force.",
    },
    "Brute Force": {
        "name": "Brute Force",
        "category": "Brute Force",
        "description": "Repeatedly guessing usernames and passwords until one works "
                       "(here: FTP and SSH login attacks).",
        "how_it_works": "An automated script tries thousands of password "
                        "combinations against a login service as fast as the server "
                        "allows.",
        "indicators": "Very many failed logins in a short window from one or few "
                      "addresses, sometimes followed by a success.",
        "impact": "If a password is cracked, the attacker logs in as a real user — "
                  "data theft or a foothold to escalate.",
        "defense": "Account lockout, rate limiting, multi-factor authentication, "
                   "strong passwords, key-based SSH instead of passwords.",
        "example": "SSH-Patator: an automated flood of 'root / password123', "
                   "'root / admin', ...",
    },
    "Web Attack": {
        "name": "Web Attack",
        "category": "Web Attack",
        "description": "Attacks aimed at web applications (SQL injection, XSS, "
                       "brute-forcing web logins) that misuse the site itself.",
        "how_it_works": "The attacker sends malicious input to the website — "
                        "e.g. SQL that the database runs, or scripts that run in "
                        "another visitor's browser.",
        "indicators": "Malformed or oversized HTTP requests, URL patterns containing "
                      "SQL or script payloads, many failed web logins.",
        "impact": "Data breaches (stealing the database), hijacked sessions, or a "
                  "site turned into a malware distributor.",
        "defense": "Input validation and parameterised queries, web application "
                   "firewall (WAF), patching web frameworks.",
        "example": "SQL injection: ' OR 1=1 -- in a login field to bypass "
                   "authentication.",
    },
    "Botnet": {
        "name": "Botnet",
        "category": "Botnet",
        "description": "A network of compromised machines ('bots') secretly "
                       "controlled by an attacker, often used to launch DDoS attacks "
                       "or send spam.",
        "how_it_works": "Each bot runs a hidden program that waits for commands from "
                        "a command-and-control (C&C) server. The attacker can then "
                        "order thousands of bots to act together.",
        "indicators": "Regular, periodic connections to known C&C addresses, "
                      "unusual outbound traffic, machines behaving the same way at "
                      "the same time.",
        "impact": "Your machines become weapons used to attack others; the botnet "
                  "powers the largest DDoS attacks on the internet.",
        "defense": "Keep systems patched, block known C&C domains, monitor "
                   "unexpected outbound connections, network segmentation.",
        "example": "A home PC quietly phoning home to a C&C server every 30 seconds "
                   "while infected.",
    },
    "Infiltration": {
        "name": "Infiltration",
        "category": "Infiltration",
        "description": "A slow, stealthy attack that works its way inside the "
                       "network over a long period instead of striking loudly.",
        "how_it_works": "The attacker exploits a weak point (e.g. a vulnerable "
                        "software version), gets in, and then moves quietly between "
                        "machines, keeping activity low to avoid detection.",
        "indicators": "Unusual internal traffic between machines that never talk, "
                      "small amounts of odd data transfer, compromised-looking "
                      "services responding oddly.",
        "impact": "The attacker can stay hidden for months, exfiltrating data "
                  "slowly — the nightmare 'we were breached and didn't know' "
                  "scenario.",
        "defense": "Network segmentation, endpoint detection, monitoring internal "
                   "traffic (not just the edge), timely patching.",
        "example": "An intruder on a LAN using an internal image-upload service to "
                   "stage malware and pivot to other machines.",
    },
    "Heartbleed": {
        "name": "Heartbleed",
        "category": "Heartbleed",
        "description": "An exploit of the Heartbleed bug in OpenSSL (2014): a "
                       "malformed 'heartbeat' request made the server read out "
                       "chunks of its own memory.",
        "how_it_works": "A server normally echoes data you send in a heartbeat "
                        "message. The bug let an attacker ask for more data than "
                        "they sent, so the server leaked whatever was in its "
                        "memory — keys, passwords, session tokens.",
        "indicators": "Oddly sized TLS heartbeat requests and responses.",
        "impact": "Massive data exposure: private keys and user passwords could be "
                  "stolen from millions of servers without leaving traces.",
        "defense": "Update OpenSSL (the bug is fixed), rotate keys and passwords "
                   "after exposure.",
        "example": "Sending a tiny 1-byte heartbeat but claiming a 64,000-byte "
                   "response, causing the server to dump 64 KB of memory.",
    },
}


# Lookup map: lowercase name -> real key, so "dos", "DoS", "DDOS" all work.
# (str.title() is NOT used — it would corrupt "DoS" into "Dos".)
_LOOKUP = {key.lower(): key for key in ATTACK_INFO}


def get_attack_info(attack_type: str) -> dict | None:
    """Return the explanation dict for an attack type (case-insensitive)."""
    key = _LOOKUP.get(attack_type.strip().lower())
    return ATTACK_INFO.get(key) if key else None


def list_attack_types() -> list[str]:
    """All attack types the API can explain."""
    return sorted(ATTACK_INFO.keys())
