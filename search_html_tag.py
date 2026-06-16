import re

filepath = r"C:\Users\AUM\.gemini\antigravity\brain\ea31bfcd-7607-4cb4-96ef-b0cff71f6f82\.system_generated\steps\337\content.md"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# Let's search for the classes in the raw content and print the HTML around them
for cls in ['1jqwtxk', '49wjhl']:
    print(f"=== HTML occurrences of {cls} ===")
    matches = [m.start() for m in re.finditer(re.escape(cls), content)]
    for idx in matches:
        start = max(0, idx - 200)
        end = min(len(content), idx + 300)
        print(content[start:end])
        print("-" * 60)
