import urllib.request

# Check what CUDA variants are available for PyTorch 2.10
for cuda_ver in ["cu128", "cu130", "cu126"]:
    url = f"https://download.pytorch.org/whl/{cuda_ver}/torch/"
    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0")
        resp = urllib.request.urlopen(req, timeout=10)
        html = resp.read().decode()
        # Find cp310 + win + 2.10
        matches = [l.split('"')[0] for l in html.split('href="') if "cp310" in l and "win" in l and "2.10" in l]
        if matches:
            print(f"\n{cuda_ver} — FOUND for Python 3.10 + Windows:")
            for m in matches[:3]:
                print(f"  {m}")
        else:
            print(f"\n{cuda_ver} — no 2.10 builds for cp310+win")
    except Exception as e:
        print(f"\n{cuda_ver} — error: {e}")
