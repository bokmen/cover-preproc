import os, sys, time, tempfile, subprocess, requests, runpod
from urllib.parse import urlparse, parse_qs

def should_send_content_type(put_url: str) -> bool:
    q = parse_qs(urlparse(put_url).query)
    signed = q.get("X-Amz-SignedHeaders", [""])[0]
    return "content-type" in signed.lower()

def ffmpeg_encode_to_mp3(wav_path: str) -> bytes:
    out_mp3 = wav_path + ".mp3"
    subprocess.check_call(
        ["ffmpeg", "-y", "-i", wav_path, "-codec:a", "libmp3lame", "-b:a", "192k", out_mp3],
        stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT
    )
    with open(out_mp3, "rb") as f:
        return f.read()

def find_instrumental(out_dir: str) -> str:
    # Try common Demucs output filenames
    for name in ("no_vocals.wav", "instrumental.wav", "vocals.wav"):  # last is fallback
        p = os.path.join(out_dir, name)
        if os.path.exists(p):
            return p
    # Fallback: any .wav in folder
    for f in os.listdir(out_dir):
        if f.endswith(".wav"):
            return os.path.join(out_dir, f)
    raise FileNotFoundError("No Demucs output WAV found.")

def handler(event):
    i = event.get("input", {})
    src_url = i["src_url"]
    put_url = i["put_url"]
    model   = i.get("model", "htdemucs")
    stems   = int(i.get("stems", 2))

    # Download source audio
    t0 = time.time()
    r = requests.get(src_url, timeout=600); r.raise_for_status()
    dl_ms = round((time.time() - t0) * 1000)

    work = tempfile.mkdtemp(prefix="demucs_")
    inp_mp3 = os.path.join(work, "in.mp3")
    with open(inp_mp3, "wb") as f:
        f.write(r.content)

    out_root = os.path.join(work, "out")

    # Demucs on CUDA
    cmd = [sys.executable, "-m", "demucs.separate", "-n", model, "--device", "cuda", "--out", out_root]
    if stems == 2:
        cmd += ["--two-stems", "vocals"]

    t1 = time.time()
    subprocess.check_call(cmd + [inp_mp3])
    demucs_ms = round((time.time() - t1) * 1000)

    base = os.path.splitext(os.path.basename(inp_mp3))[0]
    band_dir = os.path.join(out_root, model, base)
    wav_path = find_instrumental(band_dir)

    # Encode to mp3
    mp3_bytes = ffmpeg_encode_to_mp3(wav_path)

    # Upload to R2 (respect presigned header policy)
    headers = {"Content-Type": "audio/mpeg"} if should_send_content_type(put_url) else {}
    t2 = time.time()
    pr = requests.put(put_url, data=mp3_bytes, headers=headers, timeout=600)
    up_ms = round((time.time() - t2) * 1000)

    return {
        "ok": pr.status_code in (200, 204),
        "status_code": pr.status_code,
        "bytes_uploaded": len(mp3_bytes),
        "download_ms": dl_ms,
        "demucs_ms": demucs_ms,
        "upload_ms": up_ms,
        "total_ms": dl_ms + demucs_ms + up_ms,
        "model": model,
        "stems": stems,
        "sent_content_type": bool(headers)
    }

runpod.serverless.start({"handler": handler})