"""Builds clientes.json for the Ausblick app from
   - GCBA register "Garajes Comerciales" (CABA, all entries)
   - OpenStreetMap parkings in AMBA (phone/web enrich the register; commercial ones outside the register are added)
"""
import json, math, re, sys, time, unicodedata, collections

SRC = sys.argv[1]
OUT = sys.argv[2]
gar = json.load(open(SRC + '/ausblick-garajes-caba.json'))
osm = json.load(open(SRC + '/ausblick-osm-amba.json'))
NOW = int(time.time() * 1000)

SMALL = {'de', 'del', 'la', 'las', 'los', 'y', 'e'}
def tcase(s):
    words = re.split(r'(\s+|-)', s.strip().lower())
    out = []
    for i, w in enumerate(words):
        if not w.strip() or w == '-': out.append(w); continue
        if i and w in SMALL: out.append(w); continue
        out.append(w[:1].upper() + w[1:])
    return ''.join(out)

def street(calle):
    s = re.sub(r'\s+', ' ', calle or '').strip()
    av = False
    m = re.search(r'\s+AV\.?$', s, re.I)
    if m: av = True; s = s[:m.start()]
    parts = [p.strip() for p in s.split(',') if p.strip()]
    if len(parts) > 1: parts = list(reversed(parts[1:])) + [parts[0]]
    s = tcase(' '.join(parts))
    s = re.sub(r'\b(Dr|Gral|Cnel|Tte|Pres|Alte|Grl)\b\.?', lambda m: m.group(1) + '.', s)
    return ('Av. ' if av else '') + s

def dist(a, b, c, d):
    k = math.pi / 180
    x = (d - b) * k * math.cos((a + c) / 2 * k); y = (c - a) * k
    return 6371000 * math.hypot(x, y)

def norm(s):
    return unicodedata.normalize('NFD', (s or '').lower()).encode('ascii', 'ignore').decode()

# ---------- register ----------
recs = {}
by_addr = {}
for g in gar:
    key = (g['calle'], g['num'])
    if key in by_addr:
        r = by_addr[key]
        if g['nombre'] and not r['_nombre']: r['_nombre'] = g['nombre']
        continue
    rid = 'gcba-' + re.sub(r'[^0-9A-Za-z]', '', g['smp'] or '') + '-' + str(g['num'])
    addr = street(g['calle']) + ' ' + str(g['num'])
    barrio = tcase(g['barrio'] or '')
    r = {'id': rid, '_nombre': g['nombre'] or '', '_addr': addr, 'lugar': addr + ', ' + barrio + ', CABA',
         'r': 'Garaje / estacionamiento', 'tel': '', 'web': '', 'est': 'nuevo', 'log': [], 'c': NOW, 't': NOW,
         '_lat': g['lat'], '_lon': g['lon'], '_barrio': barrio,
         '_notes': ['Registro GCBA 2019' + (', %s pisos' % g['pisos'] if g.get('pisos') and g['pisos'] > 1 else '')]}
    by_addr[key] = r; recs[rid] = r
print('register unique', len(recs), file=sys.stderr)

# ---------- OSM ----------
def phone(t): return t.get('phone') or t.get('contact:phone') or t.get('contact:mobile') or ''
def web(t): return t.get('website') or t.get('contact:website') or t.get('url') or ''
NOT_SMB = re.compile(r'universidad|club|colegio|disco\b|carrefour|sodimac|megatlon|aeropuerto|aa2000|aeropuertos argentina|estaci[oó]n de trenes|municipalidad|hospital|shopping|dot baires|lourdes|encomiendas|campos? de deportes|centro asturiano|en construcci|parking (sur|r[ií]o)|multinivel e2|estacionamiento e4|el palomar', re.I)
GENERIC = re.compile(r'^(garage|garaje|estacionamiento|parking|playa)$', re.I)
reg_list = list(recs.values())
added = enriched = skipped = 0
stats = collections.Counter()
for e in osm:
    t = e['tags']; lat, lon = e['lat'], e['lon']
    name = (t.get('name') or t.get('operator') or '').strip()
    ph, wb = phone(t).strip(), web(t).strip()
    label = name + ' ' + t.get('operator', '')
    if NOT_SMB.search(label) or NOT_SMB.search(wb): stats['no-smb'] += 1; continue
    # nearest register garage
    best, bd = None, 1e9
    for r in reg_list:
        if abs(r['_lat'] - lat) > 0.01 or abs(r['_lon'] - lon) > 0.012: continue
        d = dist(lat, lon, r['_lat'], r['_lon'])
        if d < bd: best, bd = r, d
    if best and bd <= 45:
        if name and not GENERIC.match(name) and (not best['_nombre'] or norm(best['_nombre']) in norm(name)): best['_nombre'] = name
        if ph and not best['tel']: best['tel'] = ph
        if wb and not best['web']: best['web'] = wb
        if name or ph or wb:
            best['_notes'].append('OSM'); enriched += 1
        stats['matched'] += 1
        continue
    private = re.search(r'private|customers|no\b|permit', t.get('access', ''))
    commercial = t.get('fee') == 'yes' or t.get('parking') in ('multi-storey', 'underground', 'garage_boxes')
    if not (ph or wb or (commercial and name and not private)): stats['not-commercial'] += 1; continue
    a = ' '.join(x for x in [t.get('addr:street', ''), t.get('addr:housenumber', '')] if x)
    a = re.sub(r'^\d+\s*-\s*', '', a)  # "56 - Domingo Matheu 3958"
    place = t.get('addr:suburb') or t.get('addr:city') or ''
    if place == 'Ciudad Autónoma de Buenos Aires': place = ''
    in_caba = best is not None and bd < 700
    if in_caba: place = (place + ', ' if place and place != best['_barrio'] else '') + best['_barrio'] + ', CABA'
    lugar = ', '.join(x for x in [a, place] if x)
    rid = 'osm-' + e['id'].replace('/', '-')
    nm = name if name and not GENERIC.match(name) else ''
    recs[rid] = {'id': rid, '_nombre': nm, '_addr': a, 'lugar': lugar or 'AMBA (ver mapa en notas)', 'r': 'Garaje / estacionamiento',
                 'tel': ph, 'web': wb, 'est': 'nuevo', 'log': [], 'c': NOW, 't': NOW, '_lat': lat, '_lon': lon,
                 '_notes': ['OpenStreetMap']}
    added += 1
print('osm enriched', enriched, 'added', added, dict(stats), file=sys.stderr)

# ---------- final records ----------
out = {}
for r in recs.values():
    phones = [p.strip() for p in re.split(r'[;,/]', r['tel']) if p.strip()]
    tel = phones[0] if phones else ''
    notes = r['_notes'][:]
    if len(phones) > 1: notes.insert(0, 'Otros teléfonos: ' + ', '.join(phones[1:]))
    notes.append('Mapa: https://maps.google.com/?q=%.5f,%.5f' % (r['_lat'], r['_lon']))
    n = r['_nombre'] and tcase(r['_nombre']) if r['_nombre'] and r['_nombre'].isupper() else r['_nombre']
    if not n: n = 'Garaje ' + r['_addr'] if r['_addr'] else 'Estacionamiento sin nombre'
    out[r['id']] = {'id': r['id'], 'n': n, 'r': r['r'], 'tel': tel, 'lugar': r['lugar'], 'web': r['web'], 'est': 'nuevo',
                    'notas': ' · '.join(notes), 'log': [], 'c': r['c'], 't': r['t']}
data = {'v': 1, 'c': out}
s = json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n'
open(OUT, 'w').write(s)
vals = list(out.values())
print('total', len(vals), 'with tel', sum(1 for v in vals if v['tel']), 'with web', sum(1 for v in vals if v['web']),
      'named', sum(1 for v in vals if not v['n'].startswith('Garaje ')), 'outside register', sum(1 for v in vals if v['id'].startswith('osm-')),
      'bytes', len(s.encode()), file=sys.stderr)
