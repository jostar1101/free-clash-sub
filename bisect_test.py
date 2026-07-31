import yaml, subprocess, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

cfg = yaml.safe_load(open('clash-merged-clean.yaml', encoding='utf-8'))
proxies = cfg['proxies']
mihomo = r"C:\Program Files\Clash Verge\verge-mihomo.exe"
testdir = r"C:\Users\11357\AppData\Local\Temp\opencode\mihomo-test"


def test_batch(subset, path):
    mini = {
        'mixed-port': 7897, 'mode': 'rule', 'log-level': 'silent',
        'proxies': subset,
        'proxy-groups': [{'name': 'P', 'type': 'select', 'proxies': [p['name'] for p in subset[:10]]}],
        'rules': ['MATCH,P'],
    }
    with open(path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(mini, f, allow_unicode=True, sort_keys=False, default_flow_style=False, width=4096)
    r = subprocess.run([mihomo, '-t', '-d', testdir, '-f', path], capture_output=True, text=True, timeout=120)
    return r.stdout + r.stderr


lo, hi = 0, len(proxies)
bad_set = proxies
while len(bad_set) > 1:
    mid = len(bad_set) // 2
    left, right = bad_set[:mid], bad_set[mid:]
    err = test_batch(left, 'bisect_l.yaml')
    if 'test failed' in err:
        bad_set = left
        print(f"左半失败 ({len(left)}), 继续细分")
    else:
        err2 = test_batch(right, 'bisect_r.yaml')
        if 'test failed' in err2:
            bad_set = right
            print(f"右半失败 ({len(right)}), 继续细分")
        else:
            print("两侧都通过，冲突在组合（组名/引用）？")
            break
    print("当前候选:", bad_set[0]['name'] if len(bad_set) == 1 else f"{len(bad_set)} 个")

if len(bad_set) == 1:
    p = bad_set[0]
    print("问题节点:", p['name'], p['type'], p.get('server'), p.get('port'))
    print(yaml.safe_dump(p, allow_unicode=True, width=200))
    err = test_batch([p], 'bisect_one.yaml')
    for line in err.splitlines():
        if 'error' in line.lower():
            print(line[:300])
else:
    for i, p in enumerate(bad_set):
        if i > 15:
            print("...")
            break
        print(i, p['name'], p['type'], p.get('server'), p.get('flow'), (p.get('reality-opts') or {}).get('short-id'))
