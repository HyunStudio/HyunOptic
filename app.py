"""HyunOptic research workspace (Streamlit). Local research data only; NOT for clinical use."""
from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="HyunOptic — Research Workspace", page_icon="👁️", layout="wide",
                   initial_sidebar_state="auto")

from hyunoptic.ui import state  # noqa: E402  (page config must come first)

state.init_prefs()

pages = {
    "Measurements & experts": [
        st.Page("views/overview.py", title="Overview", icon=":material/home:", default=True),
        st.Page("views/image_review.py", title="Image Review", icon=":material/visibility:"),
        st.Page("views/datasets.py", title="Datasets", icon=":material/database:"),
    ],
    "Model (experimental)": [
        st.Page("views/model_inference.py", title="Model Inference", icon=":material/neurology:"),
    ],
    "Research reports": [
        st.Page("views/reliability.py", title="Reliability (QC)", icon=":material/bar_chart:"),
        st.Page("views/source_holdout.py", title="Source Holdout (QC)", icon=":material/verified_user:"),
        st.Page("views/external_validation.py", title="External Validation (QC)", icon=":material/hub:"),
        st.Page("views/model_experiment.py", title="Model Experiment", icon=":material/science:"),
        st.Page("views/reports.py", title="Reports", icon=":material/description:"),
    ],
    "Tools": [
        st.Page("views/model_settings.py", title="QC Model Lock", icon=":material/tune:"),
        st.Page("views/evidence_check.py", title="Evidence Check", icon=":material/shield:"),
        st.Page("views/batch_analysis.py", title="Batch Analysis", icon=":material/play_arrow:"),
    ],
    "Legacy studies": [
        st.Page("views/legacy_study_results.py", title="v0.3–0.4 Study Results", icon=":material/history:"),
        st.Page("views/legacy_dataset_quality.py", title="v0.4 Dataset Quality", icon=":material/history:"),
        st.Page("views/legacy_reader_roles.py", title="v0.6 Reader Roles", icon=":material/history:"),
    ],
}
page = st.navigation(pages, expanded=True)
state.shell()
page.run()
