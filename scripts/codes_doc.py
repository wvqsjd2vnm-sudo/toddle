#!/usr/bin/env python3
"""Work with the codes .docx (no extra packages needed).

  codes_doc.py seed  CODES.docx            > seed.sql     # load the 100 codes into the database
  codes_doc.py sync  CODES.docx URL ADMIN  [-o OUT.docx]  # mark used codes as [USED ...] in the doc

`sync` asks the live site which codes were redeemed and writes "[USED <date>]" after each one.
Run it as often as you like; it is idempotent (old marks are replaced, resets are un-marked).
"""
import json, re, sys, zipfile, urllib.request, datetime

PARA = re.compile(r'<w:p[ >].*?</w:p>', re.S)
LINE = re.compile(r'^\s*\d+\.\s*:?\s*(\d{6})\b\s*:?\s*(.*)$')
MARK = '[USED '


def text_of(p):
    return ''.join(re.findall(r'<w:t[^>]*>(.*?)</w:t>', p, re.S))


def read_codes(path):
    xml = zipfile.ZipFile(path).read('word/document.xml').decode('utf8')
    out = []
    for p in PARA.findall(xml):
        t = text_of(p).split(MARK)[0].replace('&amp;', '&')
        m = LINE.match(t)
        if m:
            label = re.sub(r'\b7P FREE\b', '', m.group(2)).strip(' :')
            out.append((m.group(1), label))
    return out


def seed(path):
    codes = read_codes(path)
    assert len(set(c for c, _ in codes)) == len(codes), 'duplicate codes in doc'
    print('-- %d codes' % len(codes))
    for c, label in codes:
        print("INSERT OR IGNORE INTO codes (code, label) VALUES ('%s', '%s');" % (c, label.replace("'", "''")))
    sys.stderr.write('%d codes read\n' % len(codes))


def sync(path, url, admin, out):
    req = urllib.request.Request(url.rstrip('/') + '/api/admin/codes', headers={'x-admin-code': admin, 'user-agent': 'codes-sync'})
    used = {r['code']: r['used_at'] for r in json.load(urllib.request.urlopen(req))['codes'] if r['used_at']}
    zin = zipfile.ZipFile(path)
    xml = zin.read('word/document.xml').decode('utf8')

    def fix(m):
        p = m.group(0)
        p = re.sub(r'<w:r[ >](?:(?!</w:r>).)*?%s.*?</w:r>' % re.escape(MARK), '', p, flags=re.S)  # drop old mark
        lm = LINE.match(text_of(p).replace('&amp;', '&'))
        if not lm or lm.group(1) not in used:
            return p
        when = datetime.datetime.fromtimestamp(used[lm.group(1)] / 1000, datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        run = ('<w:r><w:rPr><w:rFonts w:ascii="Courier New" w:hAnsi="Courier New" w:cs="Courier New"/><w:b/>'
               '<w:color w:val="cc0000"/><w:sz w:val="21"/></w:rPr><w:t xml:space="preserve"> %s%s]</w:t></w:r>' % (MARK, when))
        return p[:-len('</w:p>')] + run + '</w:p>'

    new = PARA.sub(fix, xml)
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            zout.writestr(item, new.encode('utf8') if item.filename == 'word/document.xml' else zin.read(item.filename))
    print('%d of %d codes marked USED -> %s' % (len(used), len(read_codes(path)), out))


if __name__ == '__main__':
    a = sys.argv[1:]
    if len(a) == 2 and a[0] == 'seed':
        seed(a[1])
    elif len(a) >= 4 and a[0] == 'sync':
        out = a[a.index('-o') + 1] if '-o' in a else a[1]
        sync(a[1], a[2], a[3], out)
    else:
        sys.exit(__doc__)
