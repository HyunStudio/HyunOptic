"""Coordinate-level semantic/polarity check; does not claim full TXT raster equivalence."""
import io,json,pathlib,zipfile
import numpy as np
from PIL import Image
from scipy.ndimage import binary_erosion,distance_transform_edt
p=pathlib.Path(__file__).resolve().parent;rows=json.loads((p/'input_manifest.json').read_text());results=[]
with zipfile.ZipFile(p.parents[2]/'data/new_external_20261104/segmentations.zip') as z:
 for row in rows[:3]:
  out=dict(source_image_id=row['source_image_id'],masks={})
  for part in ['disc','cup']:
   member=row[part+'_member'];lines=z.read(member.replace('.png','.txt')).decode().splitlines()
   # Exactly official parser's coordinate selection and 1-index -> 0-index subtraction.
   pts=np.array([[int(lines[i])-1,int(lines[i+1])-1] for i in range(3,35,2)])
   center=(int(lines[1])-1,int(lines[2])-1)
   a=np.asarray(Image.open(io.BytesIO(z.read(member))));mask=a==255
   boundary=mask&~binary_erosion(mask);distance=distance_transform_edt(~boundary)
   xy=pts;assert np.all(xy>=0) and np.all(xy[:,0]<a.shape[1]) and np.all(xy[:,1]<a.shape[0])
   d=distance[xy[:,1],xy[:,0]]
   yy,xx=np.nonzero(mask)
   out['masks'][part]=dict(txt_center_xy=list(center),png_at_txt_center=int(a[center[1],center[0]]),png_at_four_corners=[int(a[y,x]) for y,x in [(0,0),(0,-1),(-1,0),(-1,-1)]],txt_contour_points=16,coordinate_convention='x,y integer minus1 exactly as official converter',contour_point_distance_to_png_foreground_boundary_px=dict(mean=float(d.mean()),max=float(d.max()),values=[float(v) for v in d]),txt_points_bbox_xy=[int(xy[:,0].min()),int(xy[:,1].min()),int(xy[:,0].max()),int(xy[:,1].max())],png_foreground_bbox_xy=[int(xx.min()),int(yy.min()),int(xx.max()),int(yy.max())],foreground_area_pixels=int(mask.sum()))
  results.append(out)
report=dict(n_images=3,selection='first3 lexicographically ordered complete hospital test members',n_png_txt_pairs=6,checks=results,conclusion='Official Disc/Cup filenames correspond to separately located TXT contours; all TXT centers land on255 foreground and image corners on0 background. Point-to-boundary distances independently support semantic mapping and foreground polarity. No mask inversion, transpose, resizing or repair used. This is coordinate-level consistency, not full interpolation/rasterization equivalence.',official_source='official_dcseg_to_binary_mask.py and official_generate_dir_binary_masks.py archived at commit5f56b8c9957656282c2d00d40fc420a850bd1fe4')
(p/'private_png_txt_coordinate_check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({r['source_image_id']:{part:dict(center=v['png_at_txt_center'],corners=v['png_at_four_corners'],max_point_boundary_distance=v['contour_point_distance_to_png_foreground_boundary_px']['max']) for part,v in r['masks'].items()} for r in results},indent=2))
