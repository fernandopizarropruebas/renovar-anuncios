import json, re, os, glob

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
        print(f"Renombrando {viejo_id} a {nuevo_id}")
        
        carpeta_vieja = os.path.join("anuncios", viejo_id)
        carpeta_nueva = os.path.join("anuncios", nuevo_id)
        if os.path.exists(carpeta_vieja):
            os.rename(carpeta_vieja, carpeta_nueva)
        
        datos_file = os.path.join(carpeta_nueva, "datos.md")
        if os.path.exists(datos_file):
            with open(datos_file, "r") as f: content = f.read()
            content = re.sub(r'\|\s*\*\*ID\*\*\s*\|\s*' + re.escape(viejo_id) + r'\s*\|', f"| **ID** | {nuevo_id} |", content)
            content = content.replace(viejo_id, nuevo_id)
            with open(datos_file, "w") as f: f.write(content)

        for j_file in glob.glob("publicados_en_*.json"):
            if j_file == "publicados_en_fernandoapg00@gmail.com.json": continue
            with open(j_file, "r") as f: jdata = json.load(f)
            if viejo_id in jdata:
                jdata[nuevo_id] = jdata.pop(viejo_id)
                with open(j_file, "w") as f: json.dump(jdata, f, indent=2)

print("Reparación completa!")
