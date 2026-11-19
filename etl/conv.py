import sys, re, html, zipfile, pandas as pd
sheet=int(sys.argv[1])
cols=['ANIO','MES','UBIGEO','DEPARTAMENTO','PROVINCIA','DISTRITO','COD_PRODUCTO','PRODUCTO','SIEMBRA','COSECHA','PRODUCCION','VERDE_ACTUAL','PRECIO_CHACRA']
rt=re.compile(r'<t[^>]*>(.*?)</t>'); rv=re.compile(r'<v>(.*?)</v>')
rows=[]
zf=zipfile.ZipFile('/mnt/user-data/uploads/SISAGRI.xlsx')
buf=''; rem=b''
with zf.open(f'xl/worksheets/sheet{sheet}.xml') as f:
    while True:
        chunk=f.read(1<<24)
        if not chunk: break
        chunk=rem+chunk
        try:
            s=chunk.decode('utf-8'); rem=b''
        except UnicodeDecodeError:
            s=chunk[:-3].decode('utf-8','ignore'); rem=chunk[-3:]
        buf+=s
        parts=buf.split('</row>'); buf=parts.pop()
        for p in parts:
            t=rt.findall(p); v=rv.findall(p)
            if len(t)==8 and len(v)==5 and t[0]!='AÑO':
                rows.append(t+v)
df=pd.DataFrame(rows,columns=cols)
for c in cols[8:]: df[c]=df[c].astype('float32')
for c in ['DEPARTAMENTO','PROVINCIA','DISTRITO','PRODUCTO']:
    df[c]=df[c].map(html.unescape)
df.to_parquet(f'raw/s{sheet}.parquet')
print(sheet,len(df))
