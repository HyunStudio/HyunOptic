# HyunOptic

**Quantitative Ophthalmic Measurement & Reliability Validation**

*An uncertainty-aware research software project for optic nerve and retinal image measurement.*

> **Project status:** Research planning (v0.1; 2026-10-24). No clinical validation or completed software is claimed.

HyunOptic is an independent research software initiative to examine how optic disc/cup segmentation uncertainty propagates into measurements such as vertical cup-to-disc ratio (vCDR), and whether reference-free quality-control scores can help prioritize unstable measurements for expert review.

**It is NOT a medical device, clinical decision-support product, glaucoma diagnostic application, or substitute for an ophthalmologist.** Public research datasets will be used only within their permitted terms.

## Documentation

- [한국어 프로젝트 기획서 / Korean project plan](docs/PROJECT_PLAN_KO.md)
- [English research concept & evaluation protocol](docs/RESEARCH_PROTOCOL_EN.md)

## Proposed research question

Can a quality-control method, using only the candidate fundus image and its optic disc/cup segmentation, flag cases likely to show large **independent-reader vCDR disagreement** more effectively than feasible reference-free baselines, and remain useful on a distinct dataset?

This is a **hypothesis to be tested**, not an established novelty or performance claim.

## Planned scope

1. Reproducible ingestion of public fundus images and expert annotations.
2. Calculation of vertical/horizontal/area CDR and geometry sanity checks.
3. Reference-free uncertainty/instability scores based on bounded segmentation perturbations and image/shape signals.
4. Patient-disjoint evaluation against a genuinely held-out expert annotation.
5. External evaluation on Chákṣu, including camera-stratified results where feasible.
6. Research-only visualization, report export, and documented limitations.

## Candidate research datasets

| Dataset | Use | Access/terms |
|---|---|---|
| [PAPILA](https://figshare.com/articles/dataset/PAPILA/14798004) | Development; 488 images from 244 patients and two readers | Figshare listing: GPL 3.0+; review conditions and attribution |
| [Chákṣu](https://figshare.com/articles/dataset/Ch_k_u_A_glaucoma_specific_fundus_image_database/20123135) | External evaluation; 1,345 images, five readers, three cameras | Figshare listing: CC BY 4.0 |
| [Harvard-GDP](https://github.com/Harvard-Ophthalmology-AI-Lab/Harvard-GDP) | Optional later OCT/RNFL work | CC BY-NC-ND 4.0; non-commercial research only; no patient care |

**Raw images and annotations must not be committed to this repository** merely because the dataset is publicly downloadable. Keep user-supplied and protected health information out of source control.

## Planned stack

Python 3.12 · NumPy · SciPy · OpenCV · pandas · scikit-image · scikit-learn · Streamlit · pytest

PyTorch is optional and should only be introduced if a trained segmentation model is scientifically needed.

## Roadmap

- **Weeks 1–2:** ingestion, contour parsing, CDR, image overlay, initial benchmark.
- **Weeks 3–4:** reference-free QC scores, covariance/bootstrap analysis, leakage-safe testing.
- **Weeks 5–6:** locked external evaluation and ablations.
- **Weeks 7–8:** reproducible report, limitations, research poster, English portfolio narrative.

Timelines are plans, not completed milestones.

## Scientific integrity

Previous literature already studies expert disagreement, Dice/IoU, CDR error, annotation fusion, and segmentation uncertainty. HyunOptic does **not** claim these ideas are new. A defensible contribution would require a documented literature gap, a fixed protocol, strong baselines, independent assessment, and transparent positive **or negative** results.

## Project & use restrictions

- Research and education only; no clinical deployment.
- Do not infer glaucoma diagnoses or patient-specific treatment advice from CDR alone.
- No dataset included in the GitHub repository.
- Software licensing remains **undecided** pending dependency and data-license review.
- Any study with new clinical/patient data will require relevant ethics, privacy, and access review.

See the linked project plan and protocol for definitions, evaluation procedures, and bibliography.
