# 논문 기반 코드 검수와 실제 영상 스트레스 실험

날짜: 2026-11-03. 대회 시작 전 탐색적 검토. 기관 이름은 논문의 소속·자료 출처를 설명하며 협업·승인을 의미하지 않는다.

## 1. 기관별 확인한 1차 자료

| 기관 연결 근거 | 논문·원문 | HyunOptic에 대조한 내용 | 이번 실행 범위 |
| --- | --- | --- | --- |
| Oxford OATML 및 Torr Vision Group 소속 명시 | Mukhoti et al., **Deep Deterministic Uncertainty for Semantic Segmentation** (2021, workshop/arXiv). [Oxford 연구실](https://oatml.cs.ox.ac.uk/publications/202110_MukhotiAmersfoort_DDU_Semantic_Segmentation.html), [원문](https://arxiv.org/abs/2111.00079) | 분할의 불확실성 추정과 연산 비용을 함께 평가. 하드 마스크 차이를 보정된 불확실성으로 부르면 안 됨 | 문헌 대조. DDU 재구현·Oxford 데이터 실행은 아님 |
| Harvard Ophthalmology AI Lab | Tian et al., **FairSeg: A Large-Scale Medical Image Segmentation Dataset for Fairness Learning Using Segment Anything Model with Fair Error-Bound Scaling** (ICLR 2024). [공식 원문](https://proceedings.iclr.cc/paper_files/paper/2024/file/bfdd520867b56af18dc9e80a8235b887-Paper-Conference.pdf), [저자 코드](https://github.com/Harvard-Ophthalmology-AI-Lab/FairSeg) | SLO의 OD/OC 기준 마스크와 공개 Test 구분. 색 안저와의 modality 차이 및 집단별 평가 필요 | 기존 Test 2,000장 평가 기록을 재검토. 이번에 재실행하지 않음 |
| Johns Hopkins 소속 저자, JHU 저자 서버 원문 | Xia et al., **Uncertainty-aware multi-view co-training for semi-supervised medical image segmentation and domain adaptation** (Medical Image Analysis, 2020). [저자 원문](https://www.cs.jhu.edu/~alanlab/Pubs20/xia2020uncertainty.pdf) | 다중 관점·불확실성·domain adaptation을 구분. 서로 다른 두 고정 모델의 비교를 UMCT 재현이라고 부를 수 없음 | 문헌 대조. 3D volumetric 학습·JHU 데이터 검증은 실행하지 않음 |
| 논문 저자 소속의 Harvard–MIT HST | Hoebel et al., **An Exploration of Uncertainty Information for Segmentation Quality Assessment** (SPIE Medical Imaging 2020). [DOI](https://doi.org/10.1117/12.2548722), [저자 원문](https://publications.hevs.ch/index.php/attachments/single/1483), [연구실 발표 기록](https://qtim-lab.github.io/) | 불확실성과 실제 분할 품질의 관계를 기준 마스크로 확인해야 함. 손실 함수·추정 방법 의존성을 일반화하면 안 됨 | 문헌 대조 및 자체 모델의 예측 차이/실제 오류 점검. MIT 단독 연구 또는 논문 재현으로 부르지 않음 |
| Duke BME·Ophthalmology 소속 명시 | Chiu et al., **Kernel regression based segmentation of optical coherence tomography images with diabetic macular edema** (Biomedical Optics Express, 2015). [출판 원문](https://pmc.ncbi.nlm.nih.gov/articles/PMC4399658/) | OCT 층·액체 분할은 fundus disc/cup과 타깃이 다름. 독자 간 차이와 algorithm-vs-reader를 분리 | 기존 10명 OCT supplied-boundary 재분석 기록 재검토. HyunOptic의 OCT 예측으로 바꾸어 표시하지 않음 |
| Cleveland Clinic Nakamura 연구실 목록의 저자·CalDiff 연구 연결 | Wang et al., **CalDiff: Calibrating Uncertainty and Accessing Reliability of Diffusion Models for Trustworthy Lesion Segmentation** (IEEE JBHI, DOI 2025; 2026권호). [DOI](https://doi.org/10.1109/JBHI.2025.3624331), [출판 초록](https://pubmed.ncbi.nlm.nih.gov/41129433/), [공식 연구실](https://www.lerner.ccf.org/biomedical-engineering/nakamura/) | 다중 주석의 변이를 다루는 방법과 calibration을 단순 모델 불일치와 구별 | 이번 검색에서 출판 초록·공식 목록 확인. PMC 본문은 접근 확인 화면으로 차단되어 전체 재현성·데이터 조건을 검증하지 못함. CalDiff 코드·데이터 실행 안 함 |

Harvard/Duke의 과거 실제 실행 내역은 [university-transfer 보고서](../2026-10-25-university-transfer/README.md)를 따른다. 이번에 새로 여섯 기관의 데이터로 테스트한 것처럼 합산하지 않는다. 저자 코드 또는 데이터의 현재 라이선스를 확인하지 않은 상태에서 추가 다운로드·배포·학습을 실행하지 않는다.

## 2. 공통 평가 근거

- [Lakshminarayanan et al., Deep Ensembles, NeurIPS 2017](https://proceedings.neurips.cc/paper_files/paper/2017/hash/9ef2ed4b7fd2c810847ffa5fa85bce38-Abstract.html): 여러 모델의 예측을 활용하는 근거. 현재 기능은 확률을 모아 보정한 ensemble uncertainty가 아니라 후처리 마스크의 비교다.
- [Geifman & El-Yaniv, Selective Classification, NeurIPS 2017](https://papers.nips.cc/paper_files/paper/2017/hash/4a8423d5e91fda00bb7e46540e2b0cf1-Abstract.html): 보류 비율/coverage와 남은 예측의 오류를 함께 봐야 한다. 해당 분류 연구의 위험 보장을 현재 영상 검수 도구에 이전하지 않는다.
- [Maier-Hein et al., Metrics Reloaded, Nature Methods 2024](https://www.nature.com/articles/s41592-023-02151-z): 목적에 맞는 여러 지표와 분모를 명시한다. 여기서는 disc/cup Dice, 조건부 vCDR MAE, geometry failure, execution failure를 분리한다.

논문의 관찰은 검수 항목을 정하는 참고 근거다. 아래 밝기·대비 0.6 및 blur radius 2는 HyunOptic의 자체 탐색 조건이며 각 논문의 설정이나 benchmark 재현이 아니다.

## 3. 정밀 코드 검수

검수 기준 commit: `7a20ebc`. `review/store.py`, `priority.py`, `runner.py`, `export.py`와 관련 측정·평가 계산을 재검토했다.

- 원본 해상도 PNG와 SHA256 검증 후 모델 간 마스크 Dice를 계산함을 확인.
- 빈 마스크·실행 실패·정상 두 예측의 차이를 다른 상태로 취급함을 확인.
- reference가 priority·inference에 들어가지 않고, 실패 사례가 전체 export 분모에서 사라지지 않음을 확인.
- vCDR가 정의되지 않는 사례는 해당 metric 분모에서 제외하되 실패 건수를 별도로 보존함을 확인.
- 독립 수치·저장 경계 검토에서 새로 재현된 제품 경로 차단 결함은 없었고 관련 38개 테스트가 통과했다.
- 남은 경계 제한: 내부 `record_prediction`에 호출자가 직접 넘긴 측정값은 저장 시 마스크에서 다시 계산하지 않는다. 운영 Predictor는 공용 측정 함수로 계산한다. 외부 prediction importer를 추가한다면 상태·측정값을 마스크에서 재계산하거나 비교 검증해야 한다.
- 현재 hard-label 출력만으로 ECE·NLL·Brier calibration을 측정하지 않았다. 그 지표를 추가하려면 확률 출력과 적절한 평가 프로토콜이 필요하다.

전체 소프트웨어 테스트를 새로 실행해 **274 passed, 2 warnings, 356.27초**를 확인했다. 경고는 기존 CUDA `nll_loss2d` 비결정적 연산 관련이다. 새 제품 코드 수정은 하지 않았다.

## 4. 추가 실제 데이터 실험

실행 코드: [stress_pilot.py](stress_pilot.py). 제품 코드는 수정하지 않는다.

- 기존 seed-43 baseline 및 photometric follow-up 모델을 동결하고 bundle 전체 identity 검증.
- 동일한 고정 PAPILA holdout에서 image ID 사전순으로 환자당 한 장, 처음 4명 선택. 결과를 보고 고르지 않음.
- 원본 / brightness ×0.6 / contrast ×0.6 / Gaussian blur radius 2 px. 위치 변환이 없어 원본 expert-1 마스크를 동일 좌표에 사용.
- 4명·4원본·16변형 사례·32모델 예측. 변형은 추가 환자나 독립 표본이 아님.
- 예측 완료 후에만 expert-1 주석을 불러 비교. 학습·checkpoint 선택·순위 임계값 조정 없음.
- 낮은 모델 차이(≤0.1)인데 기본 모델 Dice가 disc 또는 cup에서 <0.5인 사례도 기술 통계로 집계. 이 연구용 기준은 코드에 고정되며 임상 기준이 아님.
- [protocol.json](protocol.json)과 [summary.json](summary.json)에 조건·모델 identity·분모·집계 결과를 보존. 원본·주석·개별 식별자·로컬 DB·ZIP은 공개하지 않음.

재현 명령(허가받은 로컬 데이터와 기존 bundle 필요, 새 output 폴더 사용):

```powershell
python docs/experiments/2026-11-03-literature-audit/stress_pilot.py --output reports/literature_stress_new
```

**해석 제한:** 기존에 평가했던 holdout의 작은 재사용 분석이다. calibration, 새로운 기관에 대한 일반화, 검수 효율, 공정성, 논문 알고리즘 재현 또는 임상 유효성을 입증하지 않는다. 새로운 기관의 자료를 확보할 경우 modality·OD/OC reference·환자 분리·접근 조건이 호환되는지를 먼저 확인해야 한다.

## 5. 실제 결과와 해석

32개 예측을 CPU에서 77.34초에 실행했다. 각 조건의 Dice 분모는 모델별 4장이고, vCDR는 측정 가능한 사례만 분모에 포함한다. 실행 실패는 0건이며 밝기·대비 감소에서 모델별 각각 1건의 geometry failure가 있었다. 검토 export 검증도 통과했다.

| 조건 | baseline Disc/Cup Dice | photometric Disc/Cup Dice | baseline vCDR MAE (n) | photometric vCDR MAE (n) | geometry failure baseline/photo |
| --- | --- | --- | --- | --- | --- |
| 원본 | .7559 / .6461 | .7562 / .6231 | .1787 (4) | .2133 (4) | 0 / 0 |
| 밝기 ×.6 | .7207 / .6239 | .7346 / .6094 | .0534 (3) | .0545 (3) | 1 / 1 |
| 대비 ×.6 | .7240 / .6488 | .7469 / .6246 | .0566 (3) | .0625 (3) | 1 / 1 |
| blur radius 2 | .7563 / .6446 | .7566 / .6247 | .1787 (4) | .2045 (4) | 0 / 0 |

MAE만 보면 밝기·대비 감소가 좋아 보이지만, 측정 실패로 어려운 사례가 빠졌다. 이를 확인하기 위해 **실험 후 추가한 대응 비교**를 `posthoc_paired_vcdr`로 별도 표시했다. 새 추론 없이 보존된 예측과 같은 reference에서 계산했다.

| 같은 영상끼리 비교 | baseline MAE 원본→변형 | photometric MAE 원본→변형 | 공통 n |
| --- | --- | --- | --- |
| 밝기 감소 | .0432 → .0534 | .0577 → .0545 | 각 3 |
| 대비 감소 | .0432 → .0566 | .0577 → .0625 | 각 3 |
| 흐림 | .1787 → .1787 | .2133 → .2045 | 각 4 |

따라서 밝기 감소 후 baseline의 조건부 MAE .1787→.0534를 성능 향상으로 해석할 수 없다. 같은 세 영상에서는 오히려 오차가 증가했다. 실패 수·공통 사례·전체 Dice를 함께 보는 이유를 실제 예측으로 확인했다. 이 네 환자에서 관찰한 차이에 통계적 유의성이나 일반화 주장을 붙이지 않는다.

## 6. 보존과 변경 이력

공개 파일은 문헌 검토·실행 스크립트·프로토콜·익명 집계·SHA256 manifest뿐이다. `summary.json`의 protocol hash는 **원래 protocol.json 바이트**를 대상으로 한다. 스크립트의 대응 MAE 진단 및 누락 예측의 실패 집계 보완은 첫 실행 뒤 추가했다. 첫 실행에서 모든 32개 예측은 보존되어 있었으므로 누락 처리 보완은 관측 집계 수치를 바꾸지 않는다. 대응 비교는 보존된 결과에서 별도로 계산했으며 사전 지정 지표로 소급 표시하지 않는다.
