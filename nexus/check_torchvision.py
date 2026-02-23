import urllib.request

url = "https://download.pytorch.org/whl/cu130/torchvision/"
try:
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0")
    resp = urllib.request.urlopen(req, timeout=10)
    html = resp.read().decode()
    matches = [l.split('"')[0] for l in html.split('href="') if "cp310" in l and "win" in l]
    if matches:
        print("torchvision cu130 builds for cp310+win:")
        for m in matches[:5]:
            print(f"  {m}")
    else:
        print("No torchvision cu130 for cp310+win")
except Exception as e:
    print(f"Error: {e}")
