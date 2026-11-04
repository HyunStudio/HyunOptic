"""Contest walkthrough regressions exercise rendered previews and error messages."""
import io
from pathlib import Path

import numpy as np
from PIL import Image
import pytest

from test_seg_contract import _page,_text
from test_review_queue_ui import _seed_session


@pytest.mark.parametrize('artifact',['input','labels'])
def test_preview_does_not_reopen_verified_paths(tmp_path,monkeypatch,artifact):
    import hyunoptic.ui.model_ui as model_ui
    store,sid,cid=_seed_session(tmp_path)
    row=store.cases(sid)[0]
    target=Path(row['input_path'] if artifact=='input' else row['predictions'][0]['labels_path'])
    replacement=io.BytesIO()
    if artifact=='input':Image.new('RGB',(32,32),'blue').save(replacement,format='PNG')
    else:Image.fromarray(np.zeros((32,32),np.uint8)).save(replacement,format='PNG')
    opened=Image.open
    def replace_path(fp,*args,**kwargs):
        if isinstance(fp,(Path,str)) and Path(fp)==target:target.write_bytes(replacement.getvalue())
        return opened(fp,*args,**kwargs)
    monkeypatch.setattr(Image,'open',replace_path)
    drawn=[]
    draw=model_ui.draw_prediction
    def observe(image,disc,cup,**kwargs):
        drawn.append((image.getpixel((0,0)),int(disc.sum()),int(cup.sum())))
        return draw(image,disc,cup,**kwargs)
    monkeypatch.setattr(model_ui,'draw_prediction',observe)
    app=_page(monkeypatch,tmp_path,'model_review_queue',models_dir=str(tmp_path/'missing'))
    assert not app.exception
    assert drawn[0]==((255,0,0),400,100)


def test_unreadable_case_keeps_failure_without_memory_or_path_noise(tmp_path,monkeypatch):
    from hyunoptic.review.store import ReviewStore
    store=ReviewStore(tmp_path/'.hyunoptic'/'review')
    models=[dict(folder=str(i),identity=str(i),run_id=str(i),weights_sha256=str(i)) for i in range(2)]
    store.create_session([('bad.png',b'not an image')],models)
    app=_page(monkeypatch,tmp_path,'model_review_queue',models_dir=str(tmp_path/'missing'))
    assert not app.exception
    messages=' '.join(x.value for x in [*app.error,*app.warning])
    assert 'BytesIO' not in messages and str(tmp_path) not in messages
    assert 'error 1' in _text(app)
    assert app.dataframe[0].value.iloc[0]['Reason']=='unsupported_input'
