"""Outcome-independent bounded OLIVES acquisition: both archive prefixes, not full cohort."""
import concurrent.futures, hashlib, io, json, struct, urllib.request, zipfile, zlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'data/university_20261025/olives_pilot'
OUT.mkdir(parents=True,exist_ok=True)
URL='https://zenodo.org/api/records/7105232/files/OLIVES.zip/content'
SIZE=33913178281
BUDGET=128*1024*1024
CHUNK=8*1024*1024

def ranged(a,b):
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(URL,headers={'Range':f'bytes={a}-{b}'}),timeout=120) as r:
                assert r.status==206
                assert r.headers['Content-Range']==f'bytes {a}-{b}/{SIZE}',dict(r.headers)
                data=r.read()
            assert len(data)==b-a+1
            return data
        except Exception:
            if attempt==3:raise

class Remote(io.RawIOBase):
    def __init__(self):self.pos=0
    def seekable(self):return True
    def readable(self):return True
    def tell(self):return self.pos
    def seek(self,o,w=0):
        self.pos=o if w==0 else self.pos+o if w==1 else SIZE+o
        return self.pos
    def read(self,n=-1):
        n=min(n if n>=0 else SIZE-self.pos,SIZE-self.pos)
        if n<=0:return b''
        data=ranged(self.pos,self.pos+n-1);self.pos+=n;return data

if __name__=='__main__':
    infos=zipfile.ZipFile(Remote()).infolist()
    protocol={'source':URL,'archive_bytes':SIZE,'budget_compressed_bytes_per_inner_archive':BUDGET,
              'selection':'All complete fundus TIFF entries in first 128 MiB of each of two inner ZIP deflate streams; fixed before prediction; archive order convenience pilot',
              'full_cohort':False,'accuracy_metrics_available':False,
              'full_archive_md5_verified':False,'source_archive_md5':'e08f4198aa919d6900bd30525c137933'}
    (OUT/'protocol.json').write_text(json.dumps(protocol,indent=2))
    extracted=[]
    for info in infos:
        if not info.filename.endswith('.zip'):continue
        h=ranged(info.header_offset,info.header_offset+29)
        fields=struct.unpack('<4s5H3L2H',h)
        offset=info.header_offset+30+fields[-2]+fields[-1]
        prefix=OUT/(Path(info.filename).stem+'.prefix.bin')
        parts=[]
        def fetch(i):
            part=OUT/(Path(info.filename).stem+f'.part{i:03d}')
            a=offset+i*CHUNK;b=a+CHUNK-1
            if not part.exists():part.write_bytes(ranged(a,b))
            assert part.stat().st_size==CHUNK
            print(info.filename,'chunk',i,'done',flush=True)
            return i,part
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            parts=list(pool.map(fetch,range(BUDGET//CHUNK)))
        dec=zlib.decompressobj(-15)
        with prefix.open('wb') as f:
            for _,p in sorted(parts):f.write(dec.decompress(p.read_bytes()))
        data=prefix.read_bytes();pos=0;count=0
        while pos+30<=len(data):
            assert data[pos:pos+4]==b'PK\x03\x04',pos
            h=struct.unpack('<4s5H3L2H',data[pos:pos+30])
            flags,method,crc,compressed,uncompressed,nlen,elen=h[2],h[3],h[6],h[7],h[8],h[9],h[10]
            if flags&8:raise ValueError('Unexpected inner data descriptor; do not guess sizes')
            name=data[pos+30:pos+30+nlen].decode('utf-8')
            start=pos+30+nlen+elen;end=start+compressed
            if end>len(data):break
            if 'fundus' in name.lower() and name.lower().endswith(('.tif','.tiff')):
                raw=data[start:end] if method==0 else zlib.decompress(data[start:end],-15)
                assert len(raw)==uncompressed and zlib.crc32(raw)==crc
                local=hashlib.sha256(name.encode()).hexdigest()[:20]+'.tif'
                (OUT/local).write_bytes(raw)
                extracted.append({'source_member':name,'container':info.filename,'local':local,'sha256':hashlib.sha256(raw).hexdigest(),'zip_crc32_verified':True})
                count+=1
            pos=end
        print('EXTRACTED',info.filename,count,flush=True)
    (OUT/'private_manifest.json').write_text(json.dumps({'protocol':protocol,'images':extracted},indent=2))
