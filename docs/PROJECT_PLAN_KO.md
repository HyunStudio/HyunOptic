# HyunOptic — 연구·개발 통합 기획서

**정식명:** HyunOptic: An Uncertainty-Aware Framework for Quantitative Optic Nerve Measurement Validation  
**부제:** 안저영상 기반 시신경 측정값의 불확실성·재현성·검수 우선순위 연구 플랫폼  
**버전:** v0.1 (기획 초안) · **기준일:** 2026-10-24  
**저장소:** https://github.com/HyunStudio/HyunOptic  
**프로젝트 유형:** 독립 연구 소프트웨어 / 오픈 연구 포트폴리오  
**대상:** JHU BME·Health Sciences Informatics 및 Oxford DPhil 연구역량 제시  
**현재 단계:** 기획. 데이터 분석·모델 학습·임상 검증 및 실제 성과는 아직 수행하지 않음.

> **중요:** HyunOptic은 녹내장을 진단하거나 치료를 권고하는 의료기기가 아니다. 연구 및 교육 목적으로 공개 데이터의 측정·검수 방법을 평가한다.

---

## 1. Executive Summary

### 1.1 문제 정의

안저영상에서 시신경유두(Optic Disc, OD)와 유두함몰(Optic Cup, OC) 경계를 추출한 뒤 cup-to-disc ratio(CDR)를 계산하는 방법은 널리 연구되어 있다. 그러나 동일한 영상에 대해 전문가마다 경계가 달라질 수 있고, **영상 분할의 겹침 점수(Dice/IoU)가 높다는 사실만으로 목적 측정값의 안정성을 자동 보증할 수는 없다.**

HyunOptic은 진단 정확도 경쟁이 아닌 **measurement assurance(측정 신뢰성 검수)**에 초점을 맞춘다. 영상과 단일 후보 분할 마스크만 보유한 상황에서 측정 불안정성 점수를 산출하고, 독립 전문가의 추가 판독값이 주어졌을 때 그 점수가 실제 판독 차이를 얼마나 잘 예측했는지 실험한다.

### 1.2 궁극 목표

- 공분산, 오차 전파, 부트스트랩, 형태학적 영상 분석을 재현 가능한 구현으로 연결한다.
- 학습에 관여하지 않은 전문가 주석을 기준으로 reference-free 검수 점수의 유용성을 평가한다.
- 외부 데이터셋과 촬영장비 차이에서도 성능이 유지되는지 검증한다.
- 코드·방법·실패사례·한계가 일치하는 연구 보고서와 공개 포트폴리오를 만든다.

### 1.3 비목표(Out of scope)

- 개인의 녹내장 유무 판정, 위험도 진단, 응급도 평가 및 치료 권고.
- 임상적 적용이나 규제 승인 주장.
- 단일 시점 안저사진만으로 진행 속도, 시야 손상 변화 또는 미래 질병 경과를 추정하는 주장.
- MRI/안저/OCT 데이터 종류를 무분별하게 혼합하는 멀티모달 모델.
- 초기 단계의 대규모 딥러닝 모델 학습.

## 2. 연구 질문·가설·신규성 검증

### 2.1 핵심 연구 질문(RQ1)

**후보 안저영상과 후보 OD/OC 주석만을 입력으로 하는 검수 점수가 독립된 전문가의 vCDR 측정과 큰 차이가 발생할 사례를 더 잘 식별할 수 있는가?**

- 입력 시점에 두 번째 전문가의 결과는 보지 않는다.
- 비교 대상은 **동일한 입력 가용성**을 갖는 단순 검수 규칙(예: cup/disc 구조적 유효성, 경계 복잡도, 영상 품질, 후보 마스크 교란에 대한 민감도 점수)이다.
- 정답에 해당하는 독립 전문가 측정값은 평가 때만 사용한다.

### 2.2 하위 질문

- RQ2: 경계 교란에 따른 vCDR 변화량과 분할 영역의 Dice/IoU 변화량은 언제 서로 다르게 움직이는가?
- RQ3: 점수 임계값을 개발 데이터에서 고정했을 때 외부 Chákṣu에서 검수 우선순위 성능이 유지되는가?
- RQ4: 촬영장비 및 CDR 범위별 성능과 오탐·누락 유형은 어떻게 다른가?

### 2.3 시험 가능한 가설

- **H1(탐색적):** 불확실성 및 형태학적 특징의 조합은 단순 reference-free 기준선보다 전문가 간 vCDR 불일치의 상위 사례를 더 효율적으로 검수 대상으로 선정한다.
- **H2(탐색적):** 외부 데이터셋에서 측정 편차의 일부 패턴은 재현되지만 점수의 크기·보정 정도는 달라질 수 있다.
- **H0:** 제안 점수가 적절한 기준선보다 유용하지 않다. 음성 결과 또한 연구 결과로 투명하게 보고한다.

### 2.4 독창성에 관한 정직한 경계

기존 연구에는 이미 OD/OC 분할, 전문가 간 Dice 및 CDR 비교, 전문의 주석 융합(STAPLE 등), 불확실성 측정이 있다. 따라서 **'공분산을 사용했다', 'CDR을 계산했다', 'Dice를 비교했다' 자체를 신규 기여로 주장하지 않는다.**

후보 기여는 **독립 판독 결과를 모르는 상태에서 사용할 수 있는 측정 전용 검수 점수 + 데이터 누출을 통제한 비교 + 외부 재현성 평가 + 실패 유형 분석**의 결합이다. 이것이 실제로 선행연구 대비 새롭고 의미 있는지는 체계적인 문헌 비교 후 결정한다. 문헌조사 결과 충분히 선행연구가 있다면 신규성 대신 강한 **재현성·일반화 검증 연구**로 기여를 재정의한다.

## 3. 데이터 활용 계획

| 단계 | 자료 | 확인된 특성 | 활용 방식 | 권리·제약 |
|---|---|---|---|---|
| 개발 | [PAPILA](https://figshare.com/articles/dataset/PAPILA/14798004) | 244명 양안 488영상, 2명 전문가 OD/OC 윤곽 및 임상 변수 | 환자 단위 개발/검증, 판독 편차 평가 | Figshare 표기 GPL 3.0+; 재배포와 개별 조건 재확인 |
| 외부 검증 | [Chákṣu](https://figshare.com/articles/dataset/Ch_k_u_A_glaucoma_specific_fundus_image_database/20123135) | 1,345영상, 3종 장비, 5명 전문가 주석, 다수 융합 마스크 | 독립 데이터셋 평가, 장비별 분석, 전문가 선택 민감도 | CC BY 4.0; 출처표기 필요 |
| 선택 확장 | [Harvard-GDP](https://github.com/Harvard-Ophthalmology-AI-Lab/Harvard-GDP) | 1,000명 OCT RNFL 두께 맵; 일부 진행 레이블 | 별도 OCT/RNFL 기반 후속 가설에 한정 | CC BY-NC-ND 4.0; 비상업 연구 전용, 환자 진료 금지 |

**데이터 분리 원칙:** PAPILA의 양안 자료는 같은 환자가 학습·검증 양쪽에 들어가면 안 된다. Chákṣu의 기존 train/test 경계를 존중하되, 외부 평가에 앞서 특징 선택·임계값 등을 PAPILA에서 고정한다. 동일 이미지·주석의 파생물이 분할 경계를 넘어가지 않도록 한다.

**데이터 관리 원칙:** 다운로드 전에 데이터셋 버전, DOI, 출처, 동의/IRB 및 이용약관을 기록한다. 원본 영상을 GitHub에 업로드하지 않는다. 개인 식별 정보·임상기록 원본을 업로드하지 않는다. 분석 보고서에는 재식별 위험이 있는 샘플을 무단 첨부하지 않는다. 개별 데이터 재배포 적법성은 라이선스 문서로 재확인한다.

## 4. 측정·통계 설계

### 4.1 측정값 정의

- **vCDR:** Cup의 수직 직경 / Disc의 수직 직경.
- **hCDR:** Cup의 수평 직경 / Disc의 수평 직경.
- **aCDR:** Cup 면적 / Disc 면적. vCDR과 혼용 금지.
- **Rim 영역:** Disc 영역에서 Cup 영역을 제외한 부분; 마스크 좌표계와 유효성 확인.
- **분할 비교:** OD/OC별 Dice·IoU 및 필요 시 95% Hausdorff distance.
- **측정 비교:** 전문가 간 ΔvCDR, 절대오차, Bland–Altman plot(설명적 분석) 등.

모든 측정값은 원본 픽셀 좌표계에서 정의한다. 잘못된 스케일링, 좌우 반전, 영역 누락, Cup이 Disc 경계 밖에 위치하는 사례를 오류로 로깅한다.

### 4.2 공분산과 오차 전파

두 양 A=Cup 측정값, B=Disc 측정값의 비 R=A/B에 대해, B의 평균이 0이 아니고 상대 오차가 충분히 작을 때 1차 델타 방법으로 다음을 근사한다.

Var(R) ≈ Var(A)/μB² + (μA²/μB⁴)Var(B) − 2μA Cov(A,B)/μB³

이 식은 **동일 종류의 분자·분모 측정에만 적용**한다. 수직 직경을 입력하면 vCDR 분산의 근사이고, 면적을 입력하면 aCDR 분산의 근사이다. 두 지표를 혼용하지 않는다.

실제 A와 B의 공분산은 임의로 가정하지 않고, 사전에 정의한 **쌍을 이룬 경계 교란 실험** 또는 복수 판독에서 추정한다. 강한 비선형성, 유두 경계 오류 또는 분모가 작은 경우에는 1차 근사 대신 경험적 부트스트랩 분포를 우선 보고한다.

### 4.3 Reference-free 후보 검수 점수

추가 전문가 레이블이 없어도 계산 가능한 특징만 사용한다.

1. OD/OC 마스크의 포함관계 및 연결성 같은 구조적 무결성.
2. 경계 위치·형태의 기하학적 민감도.
3. 사전에 고정한 여러 강도의 **쌍을 이룬** 경계 교란에 대한 vCDR 변화 분포.
4. 영상 초점·조명·대비 등 비식별 영상 품질 특징(유용성은 실험 검증).
5. 선택적으로 개발 세트에서만 학습한 간단한 통계 모델의 점수.

불확실성 점수는 **의학적 진단 확률이 아니다.** 경계 교란은 실제 전문가 변동성을 완벽히 재현한다고 가정하지 않고 별도로 보정한다.

### 4.4 일차 평가 지표와 편향 방지

- **일차 타깃:** 독립 전문가와 후보 주석의 절대 vCDR 차이가 사전 지정된 연구용 임계값 τ를 초과하는 사례. τ는 **임상 진단 경계가 아니며**, 개발 데이터에서 지정·잠근다. 권장 민감도 분석 후보: 0.05 및 0.10.
- **일차 비교:** 동일한 검수 예산(예: 상위 20% 재검토)에서의 high-disagreement 발견율 및 정밀도, PR-AUC. 실제 주 결과는 사전에 하나로 지정한다.
- **이차 비교:** ROC-AUC, 경고율 대비 누락률, 예측 불확실성 구간의 포괄률, 영상 품질 및 장비별 성능, 실패 사례 분류.
- **신뢰구간:** 환자 단위(cluster) 부트스트랩; 양안을 독립 샘플로 취급하지 않는다. 외부 데이터의 환자 식별자가 없을 경우 독립성 한계를 명시한다.
- **음성 대조·Ablation:** 공분산 항 제거, 교란 점수 제거, 영상 품질 점수 제거, 단순 품질 규칙만 적용한 기준선.
- **누출 방지:** 결과 변수인 독립 전문가 vCDR, 합의 마스크, 독립 전문가와의 Dice·IoU를 **검수 점수의 입력으로 사용하지 않는다.** 이들은 회고적 결과 분석에서만 쓴다.
- **임계값 잠금:** PAPILA에서만 모형 및 규칙 선택. Chákṣu 결과를 보고 임계값을 반복적으로 재조정하지 않는다.
- **사전 명시:** 탐색적 분석은 탐색적이라고 표기하고 확인적 결과처럼 서술하지 않는다.

전문가 판독 불일치 자체가 객관적 질병의 진실값은 아니다. 따라서 평가 결과는 **측정 재현성**에 관한 것이며 환자 진단 성능으로 확대 해석할 수 없다.

### 4.5 진행 분석과 미분방정식의 제외 조건

Harvard-GDP는 OCT RNFL 맵과 일부 진행 관련 레이블을 제공하지만, **기본 공개 구성만으로 모든 환자의 원시 종단 시계열 측정값이 제공된다고 가정하지 않는다.** 실제 환자별 반복 측정과 방문 시간축을 확보하고 검증하기 전에는 d(RNFL)/dt 또는 진행 속도 추정 모듈을 구현·홍보하지 않는다.

충분한 종단 자료를 확보한 후에만 혼합효과모형, 종단 회귀, 상태공간모형 및 해석 가능한 미분방정식 접근을 **별도 연구계획**으로 검토한다.

## 5. 사용자·기능 요구사항

**주사용자:** 연구자, 의료 AI 품질 검증 담당자, 알고리즘 평가자. **비대상:** 환자·일반 대중의 자가진단.

| ID | 기능 | 우선순위 | 완료 조건 |
|---|---|---|---|
| F01 | 공개 데이터 로딩·포맷 검증 | P0 | 영상/주석 짝, 환자 ID, 좌우 눈, 파일 변조·누락 오류를 로그로 재현 |
| F02 | OD/OC 전문가 윤곽 표시 | P0 | 원본/확대/중첩 표시가 좌표계에 맞음 |
| F03 | vCDR, hCDR, aCDR 및 유효성 검증 | P0 | 인공 마스크 단위테스트와 정답 일치 |
| F04 | 전문가 간 차이 분석 | P0 | ΔvCDR, Dice/IoU를 주석자별로 재현 |
| F05 | 교란 기반 불확실성 추정 | P1 | seed 고정, 교란 설정 기록, 95% 범위 출력 |
| F06 | Reference-free QC 점수 | P1 | 독립 전문가 정보가 입력 경로로 들어오지 않음 |
| F07 | 기준선과 외부 평가 | P1 | 사전 지정 지표, 부트스트랩 구간 및 실패 분석 |
| F08 | 연구 보고서(JSON/CSV/HTML) | P1 | 데이터 버전·코드 버전·설정·경고·재현법 포함 |
| F09 | 접근성 설정 | P1 | 키보드 조작, 확대, 큰 글자, 색상 이외 표시 |
| F10 | OCT/RNFL 확장 | P2 | 독립 데이터 프로토콜과 라이선스 승인 후 착수 |

**화면 구성(제안):** Dataset Overview → Image & Annotation Viewer → Measurement Panel → QC/Uncertainty Panel → Evaluation & Error Analysis → Export.

**접근성:** 최소 14–16pt 선택형 글자 크기, 확대/고대비, 키보드 중심 조작, 다양한 색에만 의존하지 않는 윤곽선 종류, 결과표의 숫자와 텍스트 동시 제공.

## 6. 기술 아키텍처

- **UI:** Streamlit(연구용 로컬 데모). 장기적으로 웹 API와 분리 가능.
- **Data layer:** 데이터셋 어댑터, 입력 schema validator, patient/eye ID 및 라이선스 기록.
- **Geometry layer:** contour→mask 변환, 직경/면적 산출, 좌표계 검증.
- **Uncertainty layer:** paired perturbation, 공분산, 델타법, bootstrap.
- **Evaluation layer:** 기준선 비교, 독립 판독 결과 평가, 외부 데이터 검증.
- **Reporting layer:** figure 생성, CSV/JSON/HTML 리포트와 재현 명령 기록.
- **Testing/CI:** pytest, 정적 검사, synthetic-mask unit test, deterministic seed, dependency pinning.

**권장 스택:** Python 3.12, NumPy, pandas, SciPy, scikit-image, OpenCV, scikit-learn, matplotlib, Streamlit, pytest. PyTorch는 필요성이 입증된 이후 선택 적용.

**권장 저장소 구조(계획안):**

    README.md
    docs/
      PROJECT_PLAN_KO.md
      RESEARCH_PROTOCOL_EN.md
    src/hyunoptic/
      data/
      geometry/
      uncertainty/
      evaluation/
      reporting/
    app/
    tests/
    configs/
    reports/examples/           # 합성·권리확인 완료 데이터만
    .github/workflows/
    .gitignore
    pyproject.toml

원본 데이터는 프로젝트 외부의 로컬 data 디렉터리에 별도 보관한다. 저장소에는 데이터 다운로드 경로와 입력 인터페이스만 남긴다.

## 7. WBS / 단계별 실행 계획

| 기간 | 작업 | 주요 산출물 | 통과 게이트 |
|---|---|---|---|
| 1주 | 자료·문헌 재점검, 데이터 권리 확인, 측정 정의 고정 | 문헌 비교표, 데이터 인벤토리, 평가 초안 | 신규성 주장을 보류하고 재현 가능한 질문 확정 |
| 2주 | PAPILA 어댑터, OD/OC 마스크, CDR·Dice 테스트 | 데이터 로더, 영상 오버레이, 테스트 | 양안/좌표계 정합성 및 인공 마스크 테스트 통과 |
| 3주 | 쌍 교란·오차 전파·bootstrap | 불확실성 모듈, 표준 출력 | seed 반복 재현, 파라미터 기록 |
| 4주 | 비교 기준선, PAPILA 환자 분리 평가 | 결과표 v0.1 | 기준선과 제안 방법의 동일 정보 조건 충족 |
| 5주 | 점수/임계값 잠금, 오류 분석 | locked protocol, ablation | 외부 데이터 결과 보기 전 설정 동결 |
| 6주 | Chákṣu 외부 검증, 장비별 분석 | 외부 검증 결과 및 실패 사례 | 데이터 누출 없음, 조건별 표본 수 명시 |
| 7주 | 한계/재현성/윤리 검토, 자동보고서 | 기술 보고서, 재현 절차 | 제3자가 동일 결과를 재생성 가능 |
| 8주 | 영어 연구 초록·포스터·포트폴리오 | PDF/데모 영상/영문 설명 | 실제 구현과 주장 간 일치, 공개 권리 확인 |

**일정은 목표일 뿐 실제 진척·성능을 의미하지 않는다.** 외부 데이터 접근이 지연되면 합성 마스크 및 PAPILA 재현성 분석을 우선 수행하고, 결과표에 외부 검증 미수행을 명확히 쓴다.

## 8. 성공기준과 Go/No-Go

**필수 완료(Engineering):**
- 합성 경계 정답으로 vCDR·hCDR·aCDR 계산 검증.
- PAPILA 양안에 대한 환자 기준 분할과 재현 가능한 분석.
- 점수 계산 시 평가 대상 독립 전문가 정보를 참조하지 않는 코드 테스트.
- 결과 JSON/CSV, 오류 로그, 데이터·코드 버전, 파라미터 기록.
- 의료기기 아님/비진단 목적 경고 및 라이선스·출처 문서화.

**연구 성공(Scientific):**
- 적어도 하나의 참조 없는 검수 기준선 대비 고정 예산 평가.
- 추정치뿐 아니라 불확실성 구간·효과 크기·음성 결과 공개.
- Chákṣu 외부 결과 또는 미완료 이유를 정확히 명시.
- 선행연구 대비 기여의 크기를 과장하지 않는 영문 요약.

**Stop/Pivot 규칙:** 검수 점수가 기준선보다 낫지 않거나 외부 성능이 무너지면 '새로운 검수 알고리즘 성공' 주장을 포기하고, 데이터셋 간 재현성/측정 오차 연구로 결과와 기여를 전환한다.

## 9. 위험·윤리·임상적 경계

| 위험 | 구체적 대응 |
|---|---|
| 진단으로 오인 | UI·README·보고서마다 Research-only, Not for clinical use 표시 |
| 임상 참값 오인 | 전문가 간 일치도는 재현성 평가이며 실제 질병 판정과 구분 |
| 데이터 누출 | 환자/눈 분리와 평가 레이블 차단, 잠금형 외부 검증 |
| 모집단·기기 편향 | 국가·카메라·품질별 결과 및 작은 표본의 불확실성 보고 |
| 라이선스 충돌 | 데이터와 코드 권리 분리 검토, 데이터 원본 비공개 |
| 근거 없는 신규성 | PAPILA/Chákṣu 및 최신 segmentation/QC 문헌 비교표 유지 |
| 소규모 데이터 과적합 | 간단한 모델 우선, 반복 튜닝 제한, 독립 외부 평가 |
| 민감 의료정보 | 새로운 환자데이터는 별도 승인·동의·보안 검토 없이는 수집 금지 |

## 10. 박사 지원 포트폴리오 전략

- **JHU BME:** 신뢰성 있는 수학 모델, 영상 geometry, 오차 전파, 독립 검증, 실험의 엄밀성.
- **JHU HSI:** 데이터 스키마, 의료 데이터 품질·감사 추적, 오류 감지와 인간 검토, 재현 가능한 검수 시스템.
- **Oxford DPhil:** 연구 질문과 방법론의 정합성, 편향/불확실성의 보고, 설명 가능한 음성 결과 및 근거 평가.

**포트폴리오 최종 패키지:** (1) 실제 실행 코드 (2) 재현성 문서 (3) 일차·외부 검증 결과표 (4) 연구 포스터/영문 technical report (5) 데모 영상 또는 설치 가능한 로컬 앱 (6) 기여·실패·제약의 투명한 설명.

**예상 포트폴리오 문장(완료 후 검증 시에만 사용):** “Designed and evaluated a reference-free quality-control framework for optic nerve measurements, including patient-disjoint experiments, uncertainty quantification, and external testing.” 실제 완료 전에는 “Designing…” 또는 “Planned…”로 기술한다.

## 11. 참고자료 / 선행연구

1. Kovalyk et al. (2022), PAPILA data descriptor, Scientific Data. https://doi.org/10.1038/s41597-022-01388-1
2. PAPILA dataset and license metadata. https://figshare.com/articles/dataset/PAPILA/14798004
3. Kumar et al. (2023), Chákṣu data descriptor, Scientific Data. https://doi.org/10.1038/s41597-023-01943-4
4. Chákṣu dataset and license metadata. https://figshare.com/articles/dataset/Ch_k_u_A_glaucoma_specific_fundus_image_database/20123135
5. Luo et al. (2023), Harvard-GDP / ICCV. https://github.com/Harvard-Ophthalmology-AI-Lab/Harvard-GDP
6. A Retrospective Comparison of Deep Learning to Manual Annotations for Optic Disc and Optic Cup Segmentation in Fundus Photographs (2020). https://pmc.ncbi.nlm.nih.gov/articles/PMC7414704/
7. TRIPOD+AI (2024), 연구가 예측 모델로 확장될 때 보고 지침. https://www.bmj.com/content/385/bmj-2023-078378
8. STARD-AI (2025), 진단 정확도 연구로 별도 발전한 경우에만 해당 보고 지침. https://www.nature.com/articles/s41591-025-03953-8
9. American Academy of Ophthalmology, POAG Suspect Preferred Practice Pattern(2026 publication page). https://www.aaojournal.org/article/S0161-6420%2825%2900814-0/fulltext

## 12. 구현 현황 (2026-10-24, 소프트웨어 v1.0.0)

| ID | 상태 | 구현 위치 |
|---|---|---|
| F01 데이터 로딩·검증 | 구현 | `hyunoptic-inventory`, `hyunoptic-verify-sources`, `hyunoptic-chaksu-audit` |
| F02 윤곽 표시 | 구현 | Streamlit 뷰어(원본/확대/중첩) |
| F03 vCDR·hCDR·aCDR | 구현 | `measure.py` + 합성 마스크 테스트 |
| F04 전문가 간 차이 | 구현 | Dice, ΔvCDR, Bland–Altman(`hyunoptic-reader-check`) |
| F05 교란 기반 불확실성 | 구현 | `uncertainty.py`(seed 고정, 공분산·델타법) |
| F06 Reference-free QC 점수 | 구현 | exp1 전용 마스크 특징, exp2 변경 시 점수 불변 테스트 |
| F07 기준선·외부 평가 | 구현(실데이터 미실행) | `hyunoptic-source-check`, `hyunoptic-external test` |
| F08 연구 보고서 JSON/CSV/HTML | 구현 | `hyunoptic-pipeline`, `hyunoptic-report`(집계 전용 HTML) |
| F09 접근성 | 구현 | 글자 크기, 고대비, 점선 cup 윤곽, 선 굵기; 보고서는 PASS/FAIL 문자 표기 |
| F10 OCT/RNFL 확장 | 미착수(P2) | 별도 프로토콜·라이선스 승인 후 |

**남은 일:** 실제 PAPILA·Chákṣu 원본으로 `hyunoptic-pipeline` 전체 실행 → 결과(음성 결과 포함) 검토 → 영문 보고서·포스터 작성 → 소프트웨어 라이선스 선택. 실행 방법은 [v1.0 runbook](V10_RUNBOOK.md) 참조. 이 시점까지 실제 데이터 성능 결과는 없다.

---

**검토 상태:** 계획 문서 v0.1. 임상적 유효성, 새로운 방법의 참신성, 데이터셋 라이선스의 최종 법률 해석은 확인된 사실로 주장하지 않음. 문헌·실험·권리 검수에 따라 업데이트 예정.
