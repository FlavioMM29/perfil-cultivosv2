import zipfile,re,pandas as pd,html
zf=zipfile.ZipFile('/mnt/user-data/uploads/DATA_VBP.xlsx')
ss=[html.unescape(x) for x in re.findall(r'<t[^>]*>(.*?)</t>',zf.read('xl/sharedStrings.xml').decode('utf-8'),flags=re.S)]
rc=re.compile(r'<c r="([A-I])\d+"([^>]*?)(?:/>|>(?:<v>([^<]*)</v>)?</c>)')
rows=[];buf='';rem=b''
with zf.open('xl/worksheets/sheet1.xml') as f:
    while True:
        ch=f.read(1<<24)
        if not ch: break
        ch=rem+ch
        try: s=ch.decode('utf-8'); rem=b''
        except UnicodeDecodeError: s=ch[:-3].decode('utf-8','ignore'); rem=ch[-3:]
        buf+=s; parts=buf.split('</row>'); buf=parts.pop()
        for p in parts:
            d={}
            for col,at,v in rc.findall(p):
                if v=='' : continue
                d[col]=ss[int(v)] if 't="s"' in at else float(v)
            rows.append(d)
df=pd.DataFrame(rows)
df.columns=[ss[i] if False else c for i,c in enumerate(df.columns)]
print(df.head(3)); 
hdr=df.iloc[0].tolist(); df=df.iloc[1:]; df.columns=hdr
df.to_parquet('raw/vbp.parquet'); print(len(df)); print(df.dtypes)
