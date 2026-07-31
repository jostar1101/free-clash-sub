import base64, json, urllib.request, urllib.parse, re, yaml

SOURCES = {
    "pawdroid": [
        "https://raw.githubusercontent.com/Pawdroid/Free-servers/main/sub",
        "https://mirror.v2gh.com/https://raw.githubusercontent.com/Pawdroid/Free-servers/main/sub",
    ],
    "zhuhaiuk": [
        "https://raw.githubusercontent.com/zhuhaiuk/free-nodes/main/clash_config.yaml",
        "https://gh-proxy.com/https://raw.githubusercontent.com/zhuhaiuk/free-nodes/main/clash_config.yaml",
    ],
    "yoyapai": [
        "https://cdn.jsdelivr.net/gh/xiaoji235/airport-free/clash/clashnodecc.txt",
        "https://raw.githubusercontent.com/xiaoji235/airport-free/main/clash/clashnodecc.txt",
    ],
    "mahdibland": "https://raw.githubusercontent.com/mahdibland/V2RayAggregator/master/sub/sub_merge.txt",
    "auto_proxy": "https://raw.githubusercontent.com/w1770946466/Auto_proxy/main/Long_term_subscription_num",
    "au1rxx": "https://raw.githubusercontent.com/Au1rxx/free-vpn-subscriptions/main/output/clash.yaml",
}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def fetch_any(urls):
    last = None
    for u in urls if isinstance(urls, list) else [urls]:
        try:
            return fetch(u)
        except Exception as e:
            last = e
    raise last


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


def parse_uri(line, frag_default="node"):
    line = line.strip()
    if "://" not in line:
        return None
    try:
        scheme, rest = line.split("://", 1)
        frag = urllib.parse.unquote(rest.rsplit("#", 1)[1]) if "#" in rest else frag_default
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
            return node
        if scheme == "vless":
            ui, _, params = rest.partition("?")
            params = params.split("#")[0]
            u, _, hp = ui.partition("@")
            host, _, port = hp.rpartition(":")
            port = port.split("/")[0]
            q = urllib.parse.parse_qs(params)
            node = {"name": frag, "type": "vless", "server": host, "port": int(port), "uuid": u,
                    "network": q.get("type", ["tcp"])[0]}
            if q.get("security", [""])[0] == "tls":
                node["tls"] = True
                node["sni"] = q.get("sni", [""])[0] or q.get("host", [""])[0]
            elif q.get("security", [""])[0] == "reality":
                node["tls"] = True
                node["servername"] = q.get("sni", [""])[0] or q.get("host", [""])[0]
                node["client-fingerprint"] = q.get("fp", [""])[0] or "chrome"
                node["reality-opts"] = {
                    "public-key": q.get("pbk", [""])[0],
                    "short-id": q.get("sid", [""])[0],
                }
            if q.get("type", [""])[0] == "ws":
                node["ws-opts"] = {"path": q.get("path", [""])[0]}
                if q.get("host"):
                    node["ws-opts"]["headers"] = {"Host": q["host"][0]}
            return node
        if scheme == "ss":
            ui, _, _ = rest.partition("?")
            b64part, _, frag2 = ui.partition("#")
            name = urllib.parse.unquote(frag2) if frag2 else "ss"
            if "@" in b64part:
                mp, _, hp = b64part.partition("@")
                host, _, port = hp.rpartition(":")
                if ":" in mp:
                    method, _, password = mp.partition(":")
                else:
                    mp2 = base64.b64decode(mp + "===").decode("utf-8")
                    method, _, password = mp2.partition(":")
            else:
                raw2 = base64.b64decode(b64part + "===").decode("utf-8")
                mp, _, hp = raw2.partition("@")
                host, _, port = hp.rpartition(":")
                method, _, password = mp.partition(":")
            return {"name": name, "type": "ss", "server": host, "port": int(port), "cipher": method, "password": password}
        if scheme == "trojan":
            ui, _, params = rest.partition("?")
            params = params.split("#")[0]
            pw, _, hp = ui.partition("@")
            host, _, port = hp.rpartition(":")
            q = urllib.parse.parse_qs(params)
            node = {"name": frag, "type": "trojan", "server": host, "port": int(port), "password": pw}
            if q.get("sni"):
                node["sni"] = q["sni"][0]
            if q.get("type", [""])[0] == "ws":
                node["network"] = "ws"
                node["ws-opts"] = {"path": q.get("path", ["/"])[0]}
            return node
    except Exception:
        return None
    return None


def parse_link_list(raw, suffix=""):
    n = 0
    text = raw
    stripped = text.replace("\n", "").replace("\r", "").replace(" ", "")
    if re.match(r"^[A-Za-z0-9+/=]{200,}$", stripped):
        try:
            text = base64.b64decode(stripped).decode("utf-8")
        except Exception:
            pass
    for line in text.splitlines():
        line = line.strip()
        if "://" not in line:
            continue
        node = parse_uri(line)
        if node and add_unique(node, suffix):
            n += 1
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


def parse_clash_proxies(raw):
    z = yaml.safe_load(raw)
    n = 0
    for p in z.get("proxies", []):
        if add_unique(p):
            n += 1
    return n


report = []
for key, urls in SOURCES.items():
    try:
        raw = fetch_any(urls)
        if key == "pawdroid":
            cnt = parse_link_list(raw, "_P")
        elif key in ("zhuhaiuk", "au1rxx"):
            cnt = parse_clash_proxies(raw)
        elif key == "yoyapai":
            cnt = parse_yoyapai(raw)
        else:
            cnt = parse_link_list(raw)
        report.append(f"{key}: {cnt}")
    except Exception as e:
        report.append(f"{key}: FAILED ({type(e).__name__}: {e})")

import re


def validate_nodes(nodes):
    valid = []
    for p in nodes:
        ro = p.get("reality-opts")
        if p.get("flow") or ro:
            ro = ro or {}
            sid = str(ro.get("short-id", ""))
            pk = str(ro.get("public-key", ""))
            if not pk or len(pk) != 44 or not re.fullmatch(r"[A-Za-z0-9+/_-]+", pk):
                continue
            if not sid or len(sid) % 2 != 0 or any(ch not in "0123456789abcdefABCDEF" for ch in sid):
                continue
        valid.append(p)
    return valid


names = {}
for p in proxies:
    if p["name"] in names:
        names[p["name"]] += 1
        p["name"] = f"{p['name']}_{names[p['name']]}"
    else:
        names[p["name"]] = 0

proxies = validate_nodes(proxies)
print(f"reality 过滤后: {len(proxies)}")

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
