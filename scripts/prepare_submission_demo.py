"""Prepare an isolated CPU demonstration from public source and synthetic data.

No patient data, downloaded weights, account or API key. These models demonstrate
software mechanics only. More epochs do not establish real-world accuracy.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def prepare_demo(output: Path, *, epochs: int = 80, patients: int = 10, image_size: int = 64) -> dict:
    output=Path(output).expanduser().resolve()
    if output.exists():raise FileExistsError('Choose a NEW demo folder; previous work is never overwritten')
    if type(epochs) is not int or not 1<=epochs<=200:raise ValueError('epochs must be 1..200')
    if type(patients) is not int or not 6<=patients<=50:raise ValueError('patients must be 6..50')
    if type(image_size) is not int or not 32<=image_size<=128 or image_size%4:
        raise ValueError('image_size must be 32..128 and divisible by 4')
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError('Install the optional dependencies first: pip install -e ".[ui,ml]"') from exc
    from hyunoptic.demo_data import make_papila,MARKER_TEXT
    from hyunoptic.seg.train import train
    from hyunoptic.seg.bundle import verify_bundle
    from hyunoptic.seg.inference import Predictor
    from hyunoptic.papila import discover_cases,load_image

    output.mkdir(parents=True,exist_ok=False)
    (output/'SYNTHETIC_DEMO_DATA.txt').write_text(MARKER_TEXT,encoding='utf-8')
    metadata={'synthetic':True,'partial':True,'state':'preparing','epochs':epochs,
              'patients':patients,'image_size':image_size,'device':'cpu','models':[]}
    metadata_path=output/'demo_setup.json'
    def save():metadata_path.write_text(json.dumps(metadata,indent=2,allow_nan=False),encoding='utf-8')
    save()
    old_threads=torch.get_num_threads()
    try:
        torch.set_num_threads(min(4,old_threads))
        data=make_papila(output/'PAPILA_SYNTHETIC',patients=patients,size=(512,384))
        for seed in [42,43]:
            print(f'Training synthetic CPU demonstration seed {seed}; {epochs} epochs',flush=True)
            folder=train(data,output/'models'/f'synthetic_{seed}',image_size=image_size,
                epochs=epochs,batch_size=4,base_channels=8,depth=2,lr=.003,seed=seed,device='cpu',allow_partial=True)
            bundle=verify_bundle(folder)
            metadata['models'].append({'identity':bundle.identity,'run_id':bundle.run_id,
                                       'weights_sha256':bundle.weights_sha256,'synthetic':bundle.synthetic})
            save()
        cases=discover_cases(data)[:4]
        inputs=output/'inputs'
        inputs.mkdir()
        for case in cases:shutil.copyfile(case.image_path,inputs/case.image_path.name)
        (inputs/'unreadable.png').write_bytes(b'Intentional unreadable synthetic demo input')
        predictions=[]
        for folder in sorted((output/'models').iterdir()):
            model=Predictor(verify_bundle(folder))
            predictions.append([model.predict(load_image(case)).status for case in cases])
        workspace=output/'workspace'
        workspace.mkdir()
        (workspace/'workspace.json').write_text(json.dumps({
            'papila_root':str(data),'models_dir':str(output/'models'),
            'reports_dir':str(output/'analysis_reports')},indent=2),encoding='utf-8')
        metadata.update(state='ready',fixed_four_example_prediction_statuses=predictions,
                        interpretation='Synthetic mechanics only; invalid geometry remains visible; no accuracy claim.')
        save()
        return metadata
    finally:
        torch.set_num_threads(old_threads)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('demo_data/submission'))
    parser.add_argument('--epochs',type=int,default=80)
    parser.add_argument('--launch',action='store_true',help='After preparation, start the actual app on localhost')
    args=parser.parse_args()
    try:result=prepare_demo(args.output,epochs=args.epochs)
    except (OSError,ValueError,RuntimeError) as exc:parser.error(str(exc))
    print(json.dumps(result,indent=2))
    folder=args.output.expanduser().resolve()
    print(f'Synthetic input examples: {folder / "inputs"}')
    print(f'Isolated workspace: {folder / "workspace"}')
    print('Open Review Queue. Synthetic images/models demonstrate workflow, not medical accuracy.')
    if args.launch:
        env=os.environ.copy()
        env['HYUNOPTIC_WORKSPACE']=str(folder/'workspace')
        repo=Path(__file__).resolve().parents[1]
        return subprocess.call([sys.executable,'-m','streamlit','run',str(repo/'app.py'),
                                '--server.address','127.0.0.1'],cwd=repo,env=env)
    print("PowerShell: $env:HYUNOPTIC_WORKSPACE = '" + str(folder/'workspace').replace("'", "''") + "'")
    print('Then: python -m streamlit run app.py --server.address 127.0.0.1')
    return 0


if __name__=='__main__':raise SystemExit(main())
