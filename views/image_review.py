"""Image Review: compare expert annotations on one image."""
import streamlit as st

from hyunoptic.ui.components import badge, note, page_title
from hyunoptic.ui.review import review_workspace, sensitivity_panel
from hyunoptic.ui.state import available_datasets

page_title("Image Review", "Review and compare retinal images with expert annotations.",
           [badge("Research only", "info"), badge("Not diagnostic", "warn")])
if available_datasets() == ["Synthetic demo"]:
    note("No dataset is connected, so the synthetic demo geometry (not patient data) is shown. "
         "Connect PAPILA or Chákṣu on the <b>Datasets</b> page.")
review_workspace("ir", default_mode="Expert comparison", compact=False)
sensitivity_panel("ir")
st.caption("PAPILA provides 2 experts' contours; Chákṣu Test provides 5 experts' binary masks "
           "(outlines are traced from the masks for display only).")
