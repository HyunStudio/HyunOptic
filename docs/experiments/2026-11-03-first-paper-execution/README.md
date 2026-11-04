# 처음 실행한 논문 코드·수식 검사

2026-11-03 · 제품 코드 변경 없음 · 의료 데이터 성능 재현 전 단계

이전 FairSeg/Duke 평가와 PAPILA 스트레스 실험은 이번 실행에 포함하지 않는다. 다음은 그동안 문헌으로만 다뤘던 연구의 **첫 저자 코드 또는 독립 수식 실행**이다. 학습된 논문 모델의 정량 성능을 재현했다는 뜻은 아니다.

## 실제 실행 결과

| 대상 | 이번에 실제 실행한 것 | 결과 | 범위 |
| --- | --- | --- | --- |
| Oxford DDU | 저자 GDA, spectral ResNet18, entropy/MI, singular covariance 경로 | 3 통과 / 1 실패 | 순정 저자 함수 + 제어 텐서·무작위 가중치. 2021 segmentation workshop과 연결된 **2023 CVPR DDU 일반 코드**이며 Pascal VOC 분할 모델 재현은 아님 |
| Cleveland 관련 CalDiff | 보정 분포/KL/역전파, reduced UNet, prior·loss, 호환성 진단 | 순정 4검사: 2 통과/2 실패. 어댑터 4검사: 2 통과/2 실패 | GPU 모듈 검사. 수정 전 실패를 보존하고 시험용 어댑터와 구분. 데이터·학습된 checkpoint 평가 없음 |
| JHU UMCT | 3D view 역변환, K=10 variance, inverse-uncertainty fusion, Dice gradient, toy dropout | 독립 구현 5/5 통과 | 공식 코드·checkpoint 확인 못함. 논문 수식의 독립 단위 검사이며 저자 코드 실행 아님 |
| Hoebel/Martinos/MIT 이메일 저자 관련 연구 | N=10 마스크의 printed CV·mean pairwise Dice·labelled entropy, toy 3D dropout | 독립 구현 4/4 통과 | 읽을 수 있는 **2019 ML4H 관련 논문**의 수식 검사. 앞서 소개한 SPIE 2020 논문의 전체 실험으로 대체하지 않음 |

총 21개 실행 검사 중 16개 통과·5개 실패다. 일부 검사는 동일 원인의 다른 경로를 검사하므로 ‘서로 다른 결함 5개’로 해석하지 않는다. 통과 수에는 독립 수식 구현과 시험용 어댑터가 포함된다. 성능 지표인 Dice/AUROC·임상 정확도로 변환하지 않는다.

## Oxford: 통과한 계산과 실패한 경로

저자 코드 [omegafragger/DDU](https://github.com/omegafragger/DDU), commit `f597744c65df4ff51615ace5e86e82ffefe1cd0f`를 고정했다. [CVPR 2023 원문](https://openaccess.thecvf.com/content/CVPR2023/papers/Mukhoti_Deep_Deterministic_Uncertainty_A_New_Simple_Baseline_CVPR_2023_paper.pdf), [2021 segmentation workshop 원문](https://arxiv.org/pdf/2111.00079)은 서로 구분한다.

- 제어된 세 Gaussian class에서 저자 밀도와 독립 NumPy 닫힌형 계산의 최대 오차 `2.8422e-13`.
- spectral ResNet18의 2×3×32×32 입력에서 2×10 logits·2×512 features 및 반복 결정적 출력 확인. 학습하지 않은 모델이다.
- uniform entropy `2.3025849`, 동일 모델들의 mutual information 0 확인.
- 영 공분산 입력에서 현재 PyTorch는 저자의 jitter 예외 처리와 맞지 않는 경로를 거쳐 `UnboundLocalError`가 재현됨.
- 초기 `tqdm` import 실패 후 `tqdm==4.67.1`만 별도 `--target` 폴더에 설치했다. 기본 HyunOptic 환경을 변경하지 않았다.

공개 README에서 학습·로컬 checkpoint 평가 절차는 확인했지만, 사용 가능한 학습된 segmentation checkpoint 다운로드는 확인하지 못했다. 이번 결과를 CIFAR/VOC 정확도나 OOD 성능으로 표시하지 않는다.

## CalDiff: 순정과 어댑터 결과를 분리

저자 코드 [xinwxin/CalDiff](https://github.com/xinwxin/CalDiff), commit `8b29be39e26eaf606a190a85cd1bbb90d93740bc`. [논문 DOI](https://doi.org/10.1109/JBHI.2025.3624331).

- 순정 보정 모듈의 forward/KL/backward와 축소 UNet forward는 통과.
- 원래 diffusion module import는 현 환경의 `torchvision` 부재로 실패. 누락 의존성을 논문 알고리즘 결함으로 부르지 않는다.
- factory의 1-channel prior에 loss가 image+prediction 2채널을 전달하는 경로에서 채널 오류 재현.
- import를 우회한 loss 본문에서도 같은 채널 실패. 이 경로는 순정 실행이 아니라 AST 기반 시험 어댑터다.
- prior만 2채널로 바꾸면 forward는 통과하나 backward에서 in-place autograd version 오류가 발생.
- 시험에 한정해 prior 채널과 정확히 두 `.clone()`을 적용하면 forward/backward가 통과. 저자 원본 파일은 수정하지 않았다.
- 추가 진단: encoder block이 일반 Python list에 보관되어 일부 가중치가 `parameters()/state_dict()`에 등록되지 않음과 mse/sa 텐서 alias가 관측됐다. 이 부분은 위 21개 실행 검사 수에 별도 합산하지 않았다.

이는 Windows/Python 3.12/PyTorch 2.13에서 고정된 공개 코드를 실행한 결과다. 저자가 안내한 과거 Python 3.9/PyTorch 1.x 환경의 전체 실험이 실패한다는 주장이 아니다. 모델을 검증 없이 HyunOptic에 통합하지 않았다.

README는 로컬 `savedmodel100000.pt`를 예시로 들지만 공개 checkpoint 다운로드는 확인하지 못했다. 연결된 LIDC 전처리 자료는 pickle이며 이번에는 다운로드/역직렬화하지 않았다. MS 데이터 접근 조건도 남아 있다. 따라서 논문 데이터 성능 재현은 완료되지 않았다.

## UMCT와 Hoebel: 독립 수식 검사

[Xia et al. JHU 저자 원문](https://www.cs.jhu.edu/~alanlab/Pubs20/xia2020uncertainty.pdf)의 Eqs.1–6,9 및 Algorithm1을 근거로 비정방형 volume의 view 정렬과 다른 view만의 fusion을 검사했다. K=10 분산에 따른 가중치 0.8/0.2, fused prediction 0.48, finite gradient와 작은 gradient step의 objective 감소를 확인했다. U=0에서 문자 그대로의 역수는 비유한 값이 되므로 독립 구현에 `1e-12` guard를 명시했다. 저자 프로그램의 오류로 주장하지 않는다. 저자 PDF·공식 홈페이지·계정의 공개 저장소를 점검했으나 검증된 UMCT 코드·가중치를 찾지 못했다.

[Hoebel et al. 2019 관련 원문](https://arxiv.org/pdf/1911.06357) p.2를 기준으로 수식을 독립 구현했다. CV는 관례적인 std/mean으로 바꾸지 않고 인쇄된 `Var(volume)/(E(volume)+1)`을 사용했다. 동일한 올바른 마스크 10개와 동일하게 잘못 위치한 마스크 10개는 모두 pairwise Dice 1·CV 0이었다. 따라서 샘플 일치가 정답을 보장하지 않는 반례가 실제 계산에서 확인됐다. 빈 labelled 영역의 평균은 null로 명시했다. 양쪽이 빈 mask pair는 평균 pairwise Dice에서 제외하고 실제 pair_count를 보고한다(독립 구현의 경계 처리 선택). SPIE 2020 전문은 다운로드 redirect loop가 지속되어 원래 lung-nodule 실험이나 checkpoint를 검증하지 못했다.

## 보존·재실행

- JSON 4개는 실제 실행 결과이며 로컬 traceback 경로를 제외한 CalDiff 결과만 공개용으로 정리했다.
- `harnesses/`는 이번 실행을 위해 작성한 독립 검사 코드다. 저자 저장소 전체, 데이터·가중치·PDF·개인정보는 포함하지 않는다.
- 실행 환경: Python 3.12.10, PyTorch 2.13.0+cu126, seed 20261103. CalDiff GPU: RTX 3070 Laptop, 나머지는 CPU. CalDiff harness는 CUDA를 요구한다.
- 재실행하려면 harness를 git-ignored 보고서 폴더에 복사한다. Oxford harness 옆 `DDU/`에 위 commit의 저자 코드를, `deps/`에 tqdm 4.67.1을 준비한다. CalDiff harness 옆 `source/`에 위 commit을 준비한다. UMCT harness는 같은 폴더에 `xia2020uncertainty.pdf`를 요구한다(원문 SHA는 결과 JSON 참조). 각 harness가 자신의 폴더에 출력하므로 공개 증거 폴더에서 직접 실행하지 않는다.
- 이번에는 기존 실제 모델로 PAPILA 스트레스 실험을 다시 실행하지 않았다. 제품 코드·학습 정책·기존 결과도 변경하지 않았다.

이 기록은 **실행 검사 시작 및 첫 결과**다. 논문 전체 성능 재현을 위해서는 일치하는 모델·전처리·데이터·split·환경과 평가 프로토콜을 추가 확보해야 한다.
