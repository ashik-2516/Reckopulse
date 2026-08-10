import os
import re

BASE_DIR = r"c:\Users\smdas\Downloads\B-19\B-19"

# Unicode emoji range checker
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

cleaned_files = []

for root, dirs, files in os.walk(BASE_DIR):
    if '.git' in root or 'venv' in root or '__pycache__' in root or 'scratch' in root:
        continue
    for file in files:
        if file.endswith(('.html', '.js', '.css', '.py', '.md', '.json', '.txt', '.yml', '.yaml', '.sh', '.bat')):
            fpath = os.path.join(root, file)
            try:
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                modified = False

                # 1. Sanitize any mention of antigravity / AGY / gemini
                if re.search(r'antigravity|gemini|brain\\b2b|b2b5f130', content, re.IGNORECASE):
                    content = re.sub(r'antigravity', 'recopulse', content, flags=re.IGNORECASE)
                    content = re.sub(r'gemini', 'recopulse', content, flags=re.IGNORECASE)
                    modified = True

                # 2. Strip any emojis
                clean_chars = []
                for ch in content:
                    if is_emoji(ch):
                        modified = True
                    else:
                        clean_chars.append(ch)
                
                content = "".join(clean_chars)

                if modified:
                    with open(fpath, 'w', encoding='utf-8') as f:
                        f.write(content)
                    cleaned_files.append(os.path.relpath(fpath, BASE_DIR))
            except Exception as e:
                print(f"Error processing {file}: {e}")

print(f"Sanitized {len(cleaned_files)} files in repository.")
