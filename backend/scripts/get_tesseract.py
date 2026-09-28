import urllib.request, re, os, subprocess, zipfile

def get_links():
    url = "https://www.7-zip.org/download.html"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode("utf-8")
    for m in re.finditer(r'href="(a/[^"]+)"', html):
        link = m.group(1)
        if "extra" in link or "7za" in link or "x64" in link:
            print("Candidate:", link)

if __name__ == "__main__":
    get_links()
