import json, re

def extraer_id_url2(url):
    match = re.search(r'-(\d+)\?', url)
    if not match: match = re.search(r'/item/(\d+)', url)
    return match.group(1) if match else None

with open("publicados_en_fernandoapg00@gmail.com.json", "r") as f:
    data = json.load(f)

for viejo_id, meta in list(data.items()):
    nueva_url = meta.get("nueva_url", "")
    nuevo_id = extraer_id_url2(nueva_url)
    if nuevo_id and nuevo_id != viejo_id:
        data[nuevo_id] = data.pop(viejo_id)
        
with open("publicados_en_fernandoapg00@gmail.com.json", "w") as f:
    json.dump(data, f, indent=2)

print("Master JSON reparado!")
