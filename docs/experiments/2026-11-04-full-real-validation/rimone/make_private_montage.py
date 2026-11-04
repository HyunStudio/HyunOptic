"""Private visual QA only: dataset images/masks may not be redistributed."""
import io,json,pathlib,zipfile
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from scipy.ndimage import binary_erosion
BASE=pathlib.Path(__file__).resolve().parent;OUT=BASE/'supplemental_verification';rows=json.loads((BASE/'input_manifest.json').read_text())[:3];names=['papila_real_seed43_20261025','papila_camera_robust_seed43_20261025'];data=BASE.parents[2]/'data/new_external_20261104'
def render(im,d,c,colors):
 a=np.array(im).astype(float)
 for mask,color in [(d,colors[0]),(c,colors[1])]:
  a[mask]=.78*a[mask]+.22*np.array(color);edge=mask&~binary_erosion(mask,iterations=2);a[edge]=color
 return Image.fromarray(np.uint8(a))
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',15)
width=400;height=430;canvas=Image.new('RGB',(width*4,height*3+95),(18,22,28));draw=ImageDraw.Draw(canvas)
draw.text((15,8),'PRIVATE DATASET QA - no redistribution - first3 lexicographic hospital-test images',font=font,fill='white')
draw.text((15,37),'GT: disc green, cup yellow. Predictions: disc magenta, cup cyan. Raw official crop; no new crop.',font=small,fill='white')
meta={name:json.loads((OUT/name/'predictions.json').read_text()) for name in names}
with zipfile.ZipFile(data/'images.zip') as iz,zipfile.ZipFile(data/'segmentations.zip') as sz:
 for k,row in enumerate(rows):
  im=Image.open(io.BytesIO(iz.read(row['image_member']))).convert('RGB');d=np.asarray(Image.open(io.BytesIO(sz.read(row['disc_member']))))==255;c=np.asarray(Image.open(io.BytesIO(sz.read(row['cup_member']))))==255
  panels=[('Original supplied ROI',im),('Official GT',render(im,d,c,[(0,255,60),(255,235,0)]))]
  for name in names:
   a=np.asarray(Image.open(meta[name][k]['labels_path']));panels.append((('Baseline' if name==names[0] else 'Camera robust')+' / '+meta[name][k]['status'],render(im,a>=1,a==2,[(255,50,230),(0,245,255)])))
  for col,(title,panel) in enumerate(panels):
   thumb=panel.copy();thumb.thumbnail((390,390));x=col*width+(width-thumb.width)//2;y=95+k*height+28;canvas.paste(thumb,(x,y));draw.text((col*width+10,95+k*height),title,font=small,fill='white')
  draw.text((8,95+k*height+413),f'Private row{k+1}: {row["source_image_id"]}',font=small,fill=(200,205,215))
path=OUT/'private_visual_qa_first3.png';canvas.save(path);print(path)
