import json, math, re, sys, time, collections
S = sys.argv[1]; REPO = sys.argv[2]
hair = json.load(open(S + '/data/ausblick-friseure.json'))
gar = json.load(open(S + '/data/ausblick-garajes-caba.json'))
db = json.load(open(REPO + '/clientes.json'))
NOW = int(time.time() * 1000)
def tcase(s): return ' '.join(w[:1].upper() + w[1:] for w in s.lower().split())
def dist(a, b, c, d):
    k = math.pi / 180; return 6371000 * math.hypot((d - b) * k * math.cos((a + c) / 2 * k), (c - a) * k)
digits = lambda s: re.sub(r'\D', '', s or '')
existing_tel = {digits(v.get('tel'))[-8:] for v in db['c'].values() if len(digits(v.get('tel'))) >= 8}
stats = collections.Counter(); out = {}; seen_tel = {}
for hid, t, lat, lon in hair:
    if t.get('disused:shop'): stats['disused'] += 1; continue
    name = (t.get('name') or t.get('brand') or '').strip()
    if re.fullmatch(r'peluquer[ií]a( unisex)?|sal[oó]n( unisex| masculino)?|unisex|barber ?shop|barber[ií]a', name, re.I): generic = name; name = ''
    else: generic = ''
    phones = [p.strip() for k in ('phone', 'contact:phone', 'contact:mobile', 'contact:whatsapp') for p in re.split(r'[;,/]', t.get(k, '')) if p.strip()]
    phones = list(dict.fromkeys(phones))
    tel = phones[0] if phones else ''
    if tel and digits(tel)[-8:] in existing_tel: stats['tel-exists'] += 1; continue
    if tel and digits(tel)[-8:] in seen_tel:
        stats['dup-tel'] += 1; continue
    web = t.get('website') or t.get('contact:website') or t.get('contact:instagram') or t.get('contact:facebook') or ''
    street = re.sub(r'^\d+\s*-\s*', '', t.get('addr:street', '')).strip()
    addr = ' '.join(x for x in [street, t.get('addr:housenumber', '')] if x)
    city = t.get('addr:city', '').strip()
    caba = city == 'Ciudad Autónoma de Buenos Aires'
    barrio = t.get('addr:suburb') or t.get('addr:neighbourhood') or ''
    if not barrio or (not city):
        best, bd = None, 1e9
        for g in gar:
            if abs(g['lat'] - lat) > 0.008 or abs(g['lon'] - lon) > 0.01: continue
            d = dist(lat, lon, g['lat'], g['lon'])
            if d < bd: best, bd = g, d
        if best and bd < 500 and (caba or not city): caba = True; barrio = barrio or tcase(best['barrio'])
    if caba: place = ', '.join(x for x in [barrio, 'CABA'] if x)
    else: place = tcase(city) if city and city.islower() else city
    lugar = ', '.join(x for x in [addr, place] if x)
    barber = t.get('hairdresser') == 'barber' or re.search(r'barb', name + generic + ' ' + web, re.I)
    rubro = 'Barbería' if barber else 'Peluquería'
    n = name or (rubro + ' ' + addr if addr else rubro + ' sin nombre')
    notes = []
    if len(phones) > 1: notes.append('Otros teléfonos: ' + ', '.join(phones[1:]))
    if t.get('operator') and not re.fullmatch(r'\d+', t['operator']): notes.append('Operador: ' + t['operator'])
    notes.append('OpenStreetMap'); notes.append('Mapa: https://maps.google.com/?q=%.5f,%.5f' % (lat, lon))
    rid = 'osm-' + hid
    out[rid] = {'id': rid, 'n': n, 'r': rubro, 'tel': tel, 'lugar': lugar or 'AMBA (ver mapa en notas)', 'web': web, 'est': 'nuevo',
                'notas': ' · '.join(notes), 'cat': ['hair'], 'log': [], 'c': NOW, 't': NOW}
    if tel: seen_tel[digits(tel)[-8:]] = rid
clash = [k for k in out if k in db['c']]
assert not clash, clash
db['c'].update(out)
open(REPO + '/clientes.json', 'w').write(json.dumps(db, ensure_ascii=False, separators=(',', ':')) + '\n')
v = list(out.values())
print('added', len(v), 'tel', sum(1 for x in v if x['tel']), 'web', sum(1 for x in v if x['web']), 'barber', sum(1 for x in v if x['r'] == 'Barbería'),
      'caba', sum(1 for x in v if x['lugar'].endswith('CABA')), 'noname', sum(1 for x in v if 'sin nombre' in x['n']), dict(stats), file=sys.stderr)
for x in v[:3] + [x for x in v if x['tel']][:5]: print(' ', x['n'], '|', x['r'], '|', x['tel'], '|', x['lugar'], '|', x['web'][:40], file=sys.stderr)
