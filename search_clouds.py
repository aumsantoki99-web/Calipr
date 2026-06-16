import os
import re

scratch_dir = r"C:\Users\AUM\.gemini\antigravity\brain\ea31bfcd-7607-4cb4-96ef-b0cff71f6f82\scratch"
for filename in ["style_1.css", "style_2.css", "style_3.css"]:
    filepath = os.path.join(scratch_dir, filename)
    if not os.path.exists(filepath):
        print(f"Path not found: {filepath}")
        continue
    
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    print(f"=== {filename} ===")
    
    # Search for occurrences of classes
    for term in ['1jqwtxk', '49wjhl', 'framer-cetu8x', '15ri48v']:
        matches = [m.start() for m in re.finditer(re.escape(term), content)]
        print(f"Matches for {term}: {len(matches)}")
        for idx in matches[:2]:
            start = max(0, idx - 50)
            end = min(len(content), idx + 150)
            print(f"  Snippet: ... {content[start:end]} ...")
            print("-" * 30)
