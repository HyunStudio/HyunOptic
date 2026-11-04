import zipfile,pathlib,json,io,collections
import numpy as np
from PIL import Image
out=pathlib.Path('reports/full_validation_20261104/new_external');rows=json.loads((out/'input_manifest.json').read_text());data=pathlib.Path('data/new_external_20261104');counts=collections.Counter();sizes=collections.Counter();records=[]
with zipfile.ZipFile(data/'segmentations.zip') as z:
 for row in rows:
  d=np.asarray(Image.open(io.BytesIO(z.read(row['disc_member']))))==255;c=np.asarray(Image.open(io.BytesIO(z.read(row['cup_member']))))==255
  outside=int(np.count_nonzero(c&~d));counts['cup_outside_disc_images']+=bool(outside);counts['cup_outside_disc_pixels']+=outside;sizes[(row['width'],row['height'])]+=1
  if outside:records.append(dict(source_image_id=row['source_image_id'],cup_outside_disc_pixels=outside))
report=dict(n_images=len(rows),raw_reference_validation=dict(counts),reference_geometry_failures=records,mask_repair=False,resolution_counts=[dict(width=w,height=h,n=n) for (w,h),n in sorted(sizes.items())])
(out/'independent_reference_audit.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='resolution_counts'},indent=2))
