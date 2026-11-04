"""Persistent, local-only research review; review completion is not an accuracy certificate."""
from __future__ import annotations

import io
import sqlite3
from pathlib import Path

import numpy as np
import streamlit as st
from PIL import Image

from hyunoptic.review.store import ReviewStore
from hyunoptic.review.runner import run_next
from hyunoptic.review.validation import order_cases
from hyunoptic.review.inputs import MAX_FILE_BYTES, decode_image
from hyunoptic.provenance import source_commit
from hyunoptic.review.export import export_session, verify_export
from hyunoptic.seg.bundle import BundleError, find_bundles, verify_bundle
from hyunoptic.ui.components import badge, note, page_title
from hyunoptic.ui.model_ui import draw_prediction
from hyunoptic.ui.state import workspace
from hyunoptic.ui.workspace import workspace_dir

page_title('Review Queue', 'Inspect predictions, record decisions, resume and export local evidence.',
           [badge('Research only · experimental', 'warn')])
note('Model agreement is not accuracy. A review record is not clinical approval. '
     'Inputs are copied to this computer and retained until you delete the session. No upload service is used.')

try:
    store = ReviewStore(workspace_dir() / 'review')
except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
    st.error(f'Cannot open local review storage: {exc}')
    st.stop()

with st.expander('Create a review session', expanded=not store.sessions()):
    verified, rejected = {}, []
    for folder in find_bundles(workspace().models_dir):
        try:
            bundle = verify_bundle(folder)
            verified[str(folder)] = bundle
        except BundleError as exc:
            rejected.append(f'{folder.name}: {exc}')
    for message in rejected:
        st.warning(f'Bundle rejected: {message}')
    if len(verified) < 2:
        st.info('Choose two verified, distinct local models to create a session. Configure the models folder on Model Inference.')
    else:
        with st.form('rq_create'):
            options = list(verified)
            label = lambda x: f'{Path(x).name} · {verified[x].run_id}'
            primary = st.selectbox('Primary model', options, format_func=label)
            comparison = st.selectbox('Comparison model', options, index=1, format_func=label)
            modality = st.selectbox('Input modality', ['color_fundus', 'slo', 'oct', 'unknown'])
            st.caption('Color fundus does not establish compatibility: cropped optic-disc (ROI) inputs '
                       'and other imaging domains require separate evaluation.')
            uploads = st.file_uploader('Local images (PNG, JPEG, single-frame TIFF)',
                                      type=['png', 'jpg', 'jpeg', 'tif', 'tiff'], accept_multiple_files=True,
                                      max_upload_size=MAX_FILE_BYTES // (1024 * 1024))
            st.caption('Up to 500 images per session, 30 MB per file, 2 GB total; single-frame images only.')
            consent = st.checkbox('Keep local input copies for resuming this research session')
            create = st.form_submit_button('Create session', type='primary')
        if create:
            if not uploads or not consent or primary == comparison:
                st.error('Select images, two distinct models, and confirm local retention.')
            else:
                try:
                    models = [{'folder': str(b.folder.resolve()), 'identity': b.identity, 'run_id': b.run_id,
                               'weights_sha256': b.weights_sha256,
                               'data_status': {'synthetic': b.synthetic, 'partial': b.partial}}
                              for b in (verified[primary], verified[comparison])]
                    commit = source_commit()
                    session_id = store.create_session([(u.name, u.getvalue()) for u in uploads], models,
                                                      modality=modality, software_commit=commit)
                    st.session_state['rq_session'] = session_id
                except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
                    st.error(f'Session was not created: {exc}')
                else:
                    st.rerun()

sessions = store.sessions()
if not sessions:
    st.info('No review sessions. Create one with two verified models and local research images.')
    st.stop()
ids = [s['id'] for s in sessions]
if st.session_state.get('rq_session') not in ids:
    st.session_state['rq_session'] = ids[0]
sid = st.selectbox('Review session', ids, key='rq_session')
session = store.session(sid)
# Consent belongs to the active selection, including A -> B -> A transitions.
if st.session_state.get('rq_delete_session') != sid:
    st.session_state['rq_delete_confirm'] = False
    st.session_state['rq_delete_session'] = sid
declared_modality = session.get('modality', 'color_fundus')
domain_prefix = '' if declared_modality == 'color_fundus' else f'Declared modality {declared_modality}: exploratory only. '
st.warning(domain_prefix + 'Domain limits: cropped optic-disc (ROI), SLO and OCT inputs have no established '
           'reliable transfer here. File integrity and nonempty geometry do not establish segmentation accuracy. '
           'Inspect the full source and overlays; hold unresolved results.')
with st.expander('Known model limits and real-data evidence'):
    st.markdown('In the published RIM-ONE DL cropped-ROI experiment, two frozen PAPILA-trained research '
                'models returned invalid geometry on **160/174** and **132/174** images. All-image Cup Dice '
                'was **0.0018** and **0.0065**. This evidence concerns those research bundles, not a validation '
                'of every model that can be loaded. The app does not automatically recognize an input domain.')
    st.markdown('[Methods, denominators and limitations]('
                'https://github.com/HyunStudio/HyunOptic/blob/main/docs/experiments/'
                '2026-11-04-full-real-validation/README.md)')
st.caption('Models: ' + ' vs '.join(m['run_id'] for m in session['models']))
if any(m.get('data_status', {}).get('synthetic') for m in session['models']):
    st.warning('Synthetic-data model: demonstrates mechanics only, not real-data model performance.')

c1, c2 = st.columns(2)
with c1:
    chunk = st.number_input('Images per processing step', min_value=1, max_value=10, value=5, step=1)
    if st.button('Process next images', type='primary', key='rq_process'):
        try:
            with st.spinner('Processing locally; completed cases are saved after each image…'):
                for _ in range(int(chunk)):
                    if not run_next(store, sid):
                        break
        except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
            st.error(f'Processing stopped; saved work is retained: {exc}')
        else:
            st.rerun()
with c2:
    st.caption('A processing step is bounded. Stop between steps; completed results remain stored.')
    if st.button('Recover interrupted cases', key='rq_recover'):
        store.recover(sid)
        st.rerun()

rows = store.list_case_metadata(sid)
counts = {s: sum(r['status'] == s for r in rows) for s in ['pending', 'processing', 'complete', 'error', 'interrupted']}
st.write(f"Total {len(rows)} · " + ' · '.join(f'{s} {n}' for s, n in counts.items()))
st.caption('Queue status and priority are last recorded metadata, not a fresh integrity audit. '
           'Opening a case checks its evidence; saving and exporting verify evidence again.')
notice = st.session_state.pop('rq_notice', None)
if notice:
    st.success(notice)
show_names = st.toggle('Show local filenames', value=False,
                       help='Local display only. Filenames remain excluded from evidence exports.')
labels = {r['id']: f"Case {r['ordinal'] + 1:03d}" +
          (f" · {str(r.get('original_name', '')).replace(chr(92), '/').rsplit('/', 1)[-1]}" if show_names else '')
          for r in rows}
review_filter = st.selectbox('Show cases', ['All', 'Unreviewed', 'Held', 'Processing errors'])
order = st.radio('Order', ['Review priority', 'Input order'], horizontal=True)
visible = [r for r in rows if review_filter == 'All' or
           (review_filter == 'Unreviewed' and r.get('review_state') == 'unreviewed') or
           (review_filter == 'Held' and r.get('review_state') == 'held') or
           (review_filter == 'Processing errors' and r['status'] == 'error')]
if order == 'Review priority':
    visible = order_cases(visible)
st.dataframe([{'Case': labels[r['id']], 'Processing': r['status'], 'Review': r.get('review_state'),
               'Reason': ('unsupported_input' if r['status']=='error' and not r.get('pixel_sha256')
                          else '; '.join(r['priority'].get('reasons', []))),
               'Disagreement': r['priority'].get('score'),
               'Evidence': 'Not checked in list'} for r in visible], hide_index=True)

if visible:
    selection_key = f'rq_case_{sid}_{review_filter}'
    next_selection = st.session_state.pop('rq_next_selection', None)
    visible_ids = [r['id'] for r in visible]
    if next_selection and next_selection['session'] == sid and next_selection['filter'] == review_filter:
        if next_selection['case'] in visible_ids:
            st.session_state[selection_key] = next_selection['case']
    if st.session_state.get(selection_key) not in visible_ids:
        st.session_state.pop(selection_key, None)
    selected = st.selectbox('Inspect case', visible_ids, format_func=labels.get, key=selection_key)
    case = store.verified_case(sid, selected)
    terminal_input = not case.get('pixel_sha256')
    integrity_failed = bool(case.get('integrity_error'))
    if case.get('error'):
        if terminal_input:
            st.error('Unsupported input. Use a complete RGB or grayscale PNG, JPEG or single-frame TIFF. '
                     'This failed case remains recorded. Import a corrected file in a new session.')
        elif integrity_failed:
            st.error('Evidence integrity check failed. Previews and review controls are withheld. '
                     'Restore the original evidence or create a new session.')
        else:
            st.error(case['error'])
            if st.button('Retry failed case', key=f"rq_retry_{case['id']}"):
                try:
                    store.retry(case['id'])
                except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
                    st.error(f'Cannot retry: {exc}')
                else:
                    st.rerun()
    if not terminal_input and not integrity_failed:
        st.caption('Full source view is the default. A measurable prediction can still locate the wrong structure.')
        try:
            # Render the exact verified byte snapshot, never reopen its file path.
            image = decode_image(case['source_bytes'])
            predictions = {p['model_identity']: p for p in case.get('predictions', [])}
            layout = st.radio('Comparison layout', ['Aligned comparison', 'Full-size view'], horizontal=True)

            def show_source():
                st.markdown('**Source image**')
                st.image(image, caption='Source image · local copy', width='stretch')

            def show_model(index):
                model = session['models'][index]
                pred = predictions.get(model['identity'])
                role = 'Primary' if index == 0 else 'Comparison'
                st.markdown(f"**{role} model**")
                if pred is None:
                    st.caption(model['run_id'])
                    st.info('No prediction recorded for this model.')
                    return
                status_label = {'ok': 'Measurable geometry · accuracy unverified',
                                'invalid_geometry': 'Measurement unavailable',
                                'error': 'Prediction failed'}.get(pred['status'], pred['status'])
                if pred.get('labels_bytes'):
                    with Image.open(io.BytesIO(pred['labels_bytes'])) as mask:
                        label_map = np.asarray(mask)
                    overlay, _ = draw_prediction(image, label_map >= 1, label_map == 2,
                        show_disc=True, show_cup=True,
                        thickness=st.session_state.get('pref_thickness', 2),
                        high_contrast=st.session_state.get('pref_high_contrast', False),
                        dashed_cup=st.session_state.get('pref_dashed_cup', True))
                    st.image(overlay, caption=f'{role} prediction · research only', width='stretch')
                st.caption(model['run_id'])
                st.write(status_label)
                if pred.get('measurement'):
                    st.write({'Predicted vCDR': pred['measurement'].get('vertical_cdr')})
                else:
                    st.caption('No valid measurement. ' + '; '.join(pred.get('errors', [])))

            if layout == 'Aligned comparison':
                source_col, primary_col, comparison_col = st.columns(3)
                with source_col: show_source()
                with primary_col: show_model(0)
                with comparison_col: show_model(1)
            else:
                pane = st.radio('Full-size panel', ['Source image', 'Primary model', 'Comparison model'], horizontal=True)
                if pane == 'Source image': show_source()
                else: show_model(0 if pane == 'Primary model' else 1)
        except (OSError, ValueError) as exc:
            st.warning(f'Cannot display this case: {exc}')
    states = ['unreviewed', 'reviewed', 'held']
    reason_options = ['wrong_location', 'boundary_mismatch', 'image_quality', 'unsupported_modality', 'uncertain', 'other']
    if case.get('prediction_set_hash'):
        cid = case['id']
        rev_key = f'rq_revision_{cid}'
        field_keys = [f'rq_state_{cid}', f'rq_reasons_{cid}', f'rq_note_{cid}']
        if st.session_state.pop(f'rq_reset_{cid}', False):
            for key in [rev_key, *field_keys]:
                st.session_state.pop(key, None)
        displayed_revision = st.session_state.setdefault(rev_key, case.get('revision', 0))
        if st.button('Refresh review record', key=f'rq_refresh_{cid}'):
            st.session_state[f'rq_reset_{cid}'] = True
            st.rerun()
        with st.form(f'rq_decide_{cid}'):
            decision = st.selectbox('Review record (not correctness certification)', states,
                                    index=states.index(case.get('review_state', 'unreviewed')), key=field_keys[0])
            reasons = st.multiselect('Reasons (required for held)', reason_options,
                                     default=case.get('reasons', []), key=field_keys[1])
            memo = st.text_area('Private local note (excluded from exports)', value=case.get('note', ''), key=field_keys[2])
            save_col, next_col = st.columns(2)
            with save_col:
                save = st.form_submit_button('Save review record')
            with next_col:
                save_next = st.form_submit_button('Save and next case', type='primary',
                    help='All/Unreviewed: next unreviewed case. Held: next held case. Advances only after saving.')
        if save or save_next:
            try:
                store.decide(case['id'], decision, reasons, memo, displayed_revision)
            except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
                st.error(f'Review was not saved: {exc}')
            else:
                st.session_state[f'rq_reset_{cid}'] = True
                if save_next:
                    # Use the pre-save visible order, so filtering out this case cannot reset to the top.
                    later = visible_ids[visible_ids.index(cid) + 1:]
                    fresh = {r['id']: r for r in store.list_case_metadata(sid)}
                    wanted_state = 'held' if review_filter == 'Held' else 'unreviewed'
                    target = next((c for c in later if c in fresh and
                                   fresh[c].get('review_state') == wanted_state), None)
                    if target:
                        st.session_state['rq_next_selection'] = dict(session=sid, filter=review_filter, case=target)
                    else:
                        st.session_state['rq_notice'] = 'Saved. No later eligible cases in this view.'
                st.rerun()

with st.expander('Export and local retention'):
    st.caption('Export excludes original files, names, paths, masks and private notes. Hashes are not a guarantee of anonymity.')
    if st.button('Build and verify evidence ZIP', key='rq_export'):
        try:
            target = store.root / 'exports' / f'{sid}.zip'
            target.parent.mkdir(parents=True, exist_ok=True)
            path = export_session(store, sid, target)
            verify_export(path)
            st.download_button('Download verified ZIP', Path(path).read_bytes(), file_name=f'{sid}.zip',
                               mime='application/zip')
        except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
            st.error(f'Export failed: {exc}')
    confirm = st.checkbox(f'Delete this session ({sid[:8]}), {len(rows)} input copies, predictions and review records',
                          key='rq_delete_confirm')
    if st.button('Delete local session', disabled=not confirm):
        try:
            store.delete_session(sid)
        except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
            st.error(f'Session was not deleted: {exc}')
        else:
            st.session_state.pop('rq_session', None)
            st.session_state.pop('rq_delete_confirm', None)
            st.session_state.pop('rq_delete_session', None)
            st.rerun()
