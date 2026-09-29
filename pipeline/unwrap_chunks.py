# -*- coding: utf-8 -*-
"""Reassemble a JSON payload from persisted browser_console_evaluate result files.

Each input file is either the raw chunk text or a {"type":"string","value":"<json>"}
envelope. Chunks are concatenated in the order given, then parsed once to validate.

    python unwrap_chunks.py out.json chunk0.txt [chunk1.txt ...]
"""
import json, sys

def unwrap(path):
    raw = open(path, encoding="utf-8").read().strip()
    if raw.startswith('{"type":'):
        try:
            env = json.loads(raw)
            if isinstance(env, dict) and "value" in env:
                return env["value"]
        except json.JSONDecodeError:
            pass
    return raw

def main(dst, srcs):
    text = "".join(unwrap(p) for p in srcs)
    data = json.loads(text)                       # validate before writing
    json.dump(data, open(dst, "w", encoding="utf-8"), ensure_ascii=False)
    n = len(data.get("cars", [])) if isinstance(data, dict) else "n/a"
    print(f"wrote {dst}  chars={len(text)}  cars={n}")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
