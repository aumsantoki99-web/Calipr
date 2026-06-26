with open("index.html", "r", encoding="utf-8") as f:
    c = f.read()

c = c.replace('href="/frontend/"', 'href="https://huggingface.co/spaces/Aumus/calipr" target="_blank"')

with open("index.html", "w", encoding="utf-8") as f:
    f.write(c)

print("Replaced all /frontend/ links with HF Space links.")
