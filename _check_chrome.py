import os
local = os.environ.get("LOCALAPPDATA", "")
base = os.path.join(local, "ms-playwright")
print(f"Base: {base}")
print(f"Exists: {os.path.exists(base)}")
if os.path.exists(base):
    for root, dirs, files in os.walk(base):
        for f in files:
            if 'chrome' in f.lower() and f.endswith('.exe'):
                print(os.path.join(root, f))
else:
    print("No ms-playwright folder")
    print(f"LOCALAPPDATA: {local}")
