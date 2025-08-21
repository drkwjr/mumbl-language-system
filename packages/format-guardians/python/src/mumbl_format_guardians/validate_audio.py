import csv, wave, contextlib, os
from mumbl_format_guardians.common import ValidationReport

TARGET_SR = {22050, 24000}
MIN_S = 1.5
MAX_S = 14.0

def _wav_meta(path: str):
    with contextlib.closing(wave.open(path, 'rb')) as wf:
        sr = wf.getframerate()
        ch = wf.getnchannels()
        nframes = wf.getnframes()
        dur = nframes / float(sr)
        sampwidth = wf.getsampwidth()
        return sr, ch, dur, sampwidth

def validate_audio_dataset(clips_dir: str, csv_path: str) -> ValidationReport:
    rep = ValidationReport(ok=True, checked=0)
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=2):
            rel = row.get("audio_file")
            if not rel:
                rep.fail("CSV_FIELD", "audio_file missing", path=f"line {i}")
                continue
            wav = os.path.join(clips_dir, os.path.basename(rel))
            if not os.path.exists(wav):
                rep.fail("MISSING_WAV", f"{wav} not found", path=f"line {i}")
                continue
            try:
                sr, ch, dur, sw = _wav_meta(wav)
            except Exception as e:
                rep.fail("WAV_READ", f"{wav}: {e}", path=f"line {i}")
                continue
            if sr not in TARGET_SR:
                rep.fail("SR", f"{wav}: sample rate {sr} not in {TARGET_SR}", path=f"line {i}")
            if ch != 1:
                rep.fail("CHANNELS", f"{wav}: channels {ch} != 1", path=f"line {i}")
            if not (MIN_S <= dur <= MAX_S):
                rep.fail("DURATION", f"{wav}: duration {dur:.2f}s outside [{MIN_S},{MAX_S}]", path=f"line {i}")
            if sw != 2:
                rep.fail("BIT_DEPTH", f"{wav}: must be 16-bit PCM (sampwidth=2)", path=f"line {i}")
            rep.checked += 1
    return rep
