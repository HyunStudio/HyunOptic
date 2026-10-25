"""All original INSPIRE stereo TIFF views; geometry/execution, not OD/OC accuracy."""
import hashlib,json,time
from pathlib import Path
from datetime import datetime,timezone
import numpy as np,torch
from PIL import Image
from hyunoptic.seg.bundle import verify_bundle,file_sha256
from hyunoptic.seg.inference import Predictor
from hyunoptic.seg import preprocess
from evaluate_universities import MODELS,score,summarize

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
DATA=ROOT/'data/university_20261025/iowa'

if __name__=='__main__':
    torch.set_num_threads(4)
    inventory=json.loads((HERE/'iowa_private_inventory.json').read_text())
    sources=[r for r in inventory if not r['depth']]
    depth=[r for r in inventory if r['depth']]
    assert len(sources)==30 and len(depth)==30 and all(r['frames']==2 for r in sources)
    for r in sources+depth:r['sha256']=file_sha256(DATA/r['path'])
    bundles={k:verify_bundle(ROOT/'models'/v) for k,v in MODELS.items()}
    protocol={'created_utc':datetime.now(timezone.utc).isoformat(),'runner_sha256':file_sha256(Path(__file__)),
      'archive_sha256':file_sha256(ROOT/'data/university_20261025/pamidataset.rar'),
      'source':'https://webeye.ophth.uiowa.edu/abramoff/pamidataset.rar',
      'selection':'All 30 original non-TransDepth TIFFs, both original frames in file/frame order (60 views). No image selection or stereo registration.',
      'n_stereo_files':30,'n_views':60,'n_depth_reference_files':30,
      'models':{k:v.weights_sha256 for k,v in bundles.items()},'no_retraining':True,
      'metrics':'Execution/geometry availability only; no OD/OC reference masks and no accuracy claim. Provided RGBA depth-reference visualizations are not binarized into invented disc/cup masks.',
      'input':'Original whole RGB frame, letterbox384, fixed normalization, existing largest_disc_component_v1, CUDA float32 batch8.',
      'research_only':True,'exploratory':True,'not_independent_views_or_patients':True}
    protocol_path=HERE/'iowa_protocol.json'
    assert not protocol_path.exists(),'Refuse duplicate Iowa experiment'
    protocol_path.write_text(json.dumps(protocol,indent=2))
    frames=[];ids=[]
    for r in sources:
        assert file_sha256(DATA/r['path'])==r['sha256']
        with Image.open(DATA/r['path']) as im:
            for frame in range(2):
                im.seek(frame);frames.append(im.convert('RGB').copy());ids.append(r['path']+f'#frame{frame}')
    (HERE/'iowa_source_private_manifest.json').write_text(json.dumps(sources+depth,indent=2))
    result={}
    for key,bundle in bundles.items():
        predictor=Predictor(bundle);network=predictor.model.to('cuda');rows=[]
        for start in range(0,len(frames),8):
            arrays=[];lbs=[]
            for im in frames[start:start+8]:
                a,lb=preprocess.image_array(im,bundle.image_size);arrays.append(preprocess.normalise(a));lbs.append(lb)
            with torch.inference_mode():raw=network(torch.from_numpy(np.stack(arrays)).to('cuda')).argmax(1).cpu().numpy().astype('uint8')
            for offset,(lab,lb) in enumerate(zip(raw,lbs)):
                label=preprocess.to_original(preprocess.postprocess(lab),lb)
                rows.append({'case':ids[start+offset],**score(label,None)})
        assert len(rows)==60
        (HERE/f'iowa_{key}_private.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
        result[key]=summarize(rows);print(key,json.dumps(result[key]),flush=True)
        assert verify_bundle(bundle.folder).weights_sha256==protocol['models'][key]
        del predictor,network;torch.cuda.empty_cache()
    final={'protocol':protocol,'summary':result,'all_model_hashes_unchanged':True,
      'source_inventory':{'stereo_tiff_files':30,'original_views':60,'rgba_depth_references':30,'top_level_group_directories':15,'patient_count_not_verified':True},
      'notes':['Two stereo frames are correlated views, not independent cases/patients.','Geometry-valid output can still be anatomically incorrect.','No accuracy, depth-prediction or clinical-validation claim.']}
    (HERE/'iowa_results.json').write_text(json.dumps(final,indent=2))
