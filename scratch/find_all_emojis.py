import os
import re

BASE_DIR = r"c:\Users\smdas\Downloads\B-19\B-19"

def is_emoji(char):
    cp = ord(char)
    return (
        (0x1F300 <= cp <= 0x1F9FF) or
        (0x1F600 <= cp <= 0x1F64F) or
        (0x1F680 <= cp <= 0x1F6FF) or
        (0x2600 <= cp <= 0x26FF) or
        (0x2700 <= cp <= 0x27BF) or
        (0x1FA00 <= cp <= 0x1FAFF) or
        (0x1F000 <= cp <= 0x1F02F) or
        (0x1F0A0 <= cp <= 0x1F0FF)
    )

emoji_matches = []

for root, dirs, files in os.walk(BASE_DIR):
    if '.git' in root or 'venv' in root or '__pycache__' in root or 'scratch' in root:
        continue
    for file in files:
        if file.endswith(('.html', '.js', '.css', '.py')):
            fpath = os.path.join(root, file)
            rel_path = os.path.relpath(fpath, BASE_DIR)
            try:
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                    for idx, line in enumerate(f, 1):
                        found = [ch for ch in line if is_emoji(ch)]
                        if found:
                            emoji_matches.append((rel_path, idx, repr(found), line.strip()))
            except Exception as e:
                pass

with open(os.path.join(BASE_DIR, 'scratch', 'emoji_list.txt'), 'w', encoding='utf-8') as out_f:
    out_f.write(f"TOTAL EMOJI MATCHES FOUND: {len(emoji_matches)}\n\n")
    for rel, line_no, found, text in emoji_matches:
        out_f.write(f"[{rel}:{line_no}] Found: {found} -> {text}\n")
print(f"Written {len(emoji_matches)} emoji matches to scratch/emoji_list.txt")
