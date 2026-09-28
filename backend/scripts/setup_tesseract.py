import os
import sys
import subprocess
import urllib.request

def setup_tesseract():
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tesseract_dir = os.path.join(backend_dir, "tesseract_bin")
    installer_path = os.path.join(backend_dir, "tesseract-setup.exe")
    seven_za = os.path.join(backend_dir, "7za_bin", "7za.exe")

    url = "https://github.com/tesseract-ocr/tesseract/releases/download/5.5.3/tesseract-ocr-w64-setup-5.5.3.20260724.exe"

    if not os.path.exists(installer_path):
        print(f"Downloading Tesseract installer from {url}...")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as resp, open(installer_path, "wb") as f:
            total_size = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            while True:
                chunk = resp.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    pct = downloaded * 100 // total_size
                    print(f"Downloaded {downloaded}/{total_size} bytes ({pct}%)...", end="\r")
        print("\nDownload complete.")

    os.makedirs(tesseract_dir, exist_ok=True)
    print(f"Extracting installer to {tesseract_dir} using {seven_za}...")
    cmd = [seven_za, "x", installer_path, f"-o{tesseract_dir}", "-y"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("Extraction error:", res.stderr)
        return False
    print("Extraction successful.")

    tess_exe = os.path.join(tesseract_dir, "tesseract.exe")
    if os.path.exists(tess_exe):
        print(f"Found tesseract at: {tess_exe}")
        # Test running tesseract
        test_res = subprocess.run([tess_exe, "--version"], capture_output=True, text=True)
        print("Tesseract version output:")
        print(test_res.stdout)
        return True
    else:
        print("Warning: tesseract.exe not found in extracted files. Files extracted:")
        for root, dirs, files in os.walk(tesseract_dir):
            for file in files:
                if "tesseract" in file.lower():
                    print(os.path.join(root, file))
        return False

if __name__ == "__main__":
    setup_tesseract()
