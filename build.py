import base64, json, urllib.request, urllib.parse, re, yaml

SOURCES = {
    "pawdroid": "https://raw.githubusercontent.com/Pawdroid/Free-servers/main/sub",
    "zhuhaiuk": "https://raw.githubusercontent.com/zhuhaiuk/free-nodes/main/clash_config.yaml",
    "yoyapai": "https://raw.githubusercontent.com/xiaoji235/airport-free/main/clash/clashnodecc.txt",
}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


proxies = []
seen_addr = set()


def add_unique(node, suffix=""):
    if suffix:
        node = dict(node)
        node["name"] = node["name"] + suffix
    key = (node.get("server"), node.get("port"), node.get("type"))
    if key in seen_addr:
        return False
    seen_addr.add(key)
    proxies.append(node)
    return True


def parse_pawdroid(raw):
    decoded = base64.b64decode(raw.replace("\n", "").replace("\r", "")).decode("utf-8")
    n = 0
    for line in decoded.splitlines():
        line = line.strip()
        if not line or "://" not in line:
            continue
        try:
            scheme, rest = line.split("://", 1)
            frag = urllib.parse.unquote(rest.rsplit("#", 1)[1]) if "#" in rest else scheme
            if scheme == "vmess":
                d = json.loads(base64.b64decode(rest).decode("utf-8"))
                node = {"name": d.get("ps", frag), "type": "vmess", "server": d["add"], "port": int(d["port"]),
                        "uuid": d["id"], "alterId": int(d.get("aid", 0)), "cipher": d.get("scy", "auto")}
                if d.get("tls"):
                    node["tls"] = True
                    node["sni"] = d.get("sni") or d.get("host")
                if d.get("net") == "ws":
                    node["network"] = "ws"
                    node["ws-opts"] = {"path": d.get("path", "")}
                    if d.get("host"):
                        node["ws-opts"]["headers"] = {"Host": d["host"]}
            elif scheme == "vless":
                ui, _, params = rest.partition("?")
                u, _, hp = ui.partition("@")
                host, _, port = hp.rpartition(":")
                port = port.split("/")[0]
                q = urllib.parse.parse_qs(params)
                node = {"name": frag, "type": "vless", "server": host, "port": int(port), "uuid": u,
                        "network": q.get("type", ["tcp"])[0]}
                if q.get("security", [""])[0] == "tls":
                    node["tls"] = True
                    node["sni"] = q.get("sni", [""])[0] or q.get("host", [""])[0]
                if q.get("type", [""])[0] == "ws":
                    node["ws-opts"] = {"path": q.get("path", [""])[0]}
                    if q.get("host"):
                        node["ws-opts"]["headers"] = {"Host": q["host"][0]}
            elif scheme == "ss":
                ui, _, _ = rest.partition("?")
                b64part, _, frag2 = ui.partition("#")
                name = urllib.parse.unquote(frag2) if frag2 else "ss"
                if "@" in b64part:
                    mp, _, hp = b64part.partition("@")
                    host, _, port = hp.rpartition(":")
                    method, _, password = mp.partition(":")
                else:
                    raw2 = base64.b64decode(b64part + "===").decode("utf-8")
                    mp, _, hp = raw2.partition("@")
                    host, _, port = hp.rpartition(":")
                    method, _, password = mp.partition(":")
                node = {"name": name, "type": "ss", "server": host, "port": int(port), "cipher": method, "password": password}
            elif scheme == "trojan":
                ui, _, params = rest.partition("?")
                pw, _, hp = ui.partition("@")
                host, _, port = hp.rpartition(":")
                q = urllib.parse.parse_qs(params)
                node = {"name": frag, "type": "trojan", "server": host, "port": int(port), "password": pw}
                if q.get("sni"):
                    node["sni"] = q["sni"][0]
                if q.get("type", [""])[0] == "ws":
                    node["network"] = "ws"
                    node["ws-opts"] = {"path": q.get("path", ["/"])[0]}
            else:
                continue
            if add_unique(node, "_P"):
                n += 1
        except Exception:
            pass
    return n


def parse_yoyapai(raw):
    lines = raw.splitlines()
    n = 0
    i = 0
    while i < len(lines):
        if re.match(r"^  - (?:\{|name:)", lines[i]):
            block = [lines[i]]
            j = i + 1
            while j < len(lines) and lines[j].startswith("    "):
                block.append(lines[j])
                j += 1
            try:
                node = yaml.safe_load("\n".join(block))
                if isinstance(node, list) and node and isinstance(node[0], dict) and "name" in node[0] and "server" in node[0]:
                    if add_unique(node[0]):
                        n += 1
            except Exception:
                pass
            i = j
        else:
            i += 1
    return n


def parse_zhuhaiuk(raw):
    z = yaml.safe_load(raw)
    n = 0
    for p in z.get("proxies", []):
        if add_unique(p):
            n += 1
    return n


report = []
for key, url in SOURCES.items():
    try:
        raw = fetch(url)
        if key == "pawdroid":
            cnt = parse_pawdroid(raw)
        elif key == "zhuhaiuk":
            cnt = parse_zhuhaiuk(raw)
        else:
            cnt = parse_yoyapai(raw)
        report.append(f"{key}: {cnt}")
    except Exception as e:
        report.append(f"{key}: FAILED ({e})")

names = {}
for p in proxies:
    if p["name"] in names:
        names[p["name"]] += 1
        p["name"] = f"{p['name']}_{names[p['name']]}"
    else:
        names[p["name"]] = 0

config = {
    "mixed-port": 7897,
    "allow-lan": False,
    "mode": "rule",
    "log-level": "info",
    "proxies": proxies,
    "proxy-groups": [
        {"name": "PROXY", "type": "select", "proxies": ["AUTO", "DIRECT"] + [p["name"] for p in proxies[:60]]},
        {"name": "AUTO", "type": "url-test", "url": "http://www.gstatic.com/generate_204", "interval": 300,
         "tolerance": 50, "proxies": [p["name"] for p in proxies]},
    ],
    "rules": ["MATCH,PROXY"],
}

with open("clash-merged-clean.yaml", "w", encoding="utf-8") as f:
    yaml.safe_dump(config, f, allow_unicode=True, sort_keys=False, default_flow_style=False, width=4096)
yaml.safe_load(open("clash-merged-clean.yaml", encoding="utf-8"))
print(" | ".join(report), f"| total: {len(proxies)} | OK")
