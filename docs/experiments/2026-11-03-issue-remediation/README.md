# 이슈 보고서 검토와 개선 결과

2026-11-03. 기준: [첫 논문 실행 보고서](../2026-11-03-first-paper-execution/README.md), HyunOptic `67dced4`. 원래 실패 기록과 원본 저자 소스는 유지했다. GitHub issue 검색에서 별도 등록 이슈는 확인되지 않아 보존된 실행 보고서를 기준으로 삼았다.

## 1. HyunOptic 저장 경계 보완

기존 운영 Predictor는 공용 함수로 올바르게 측정하지만, ReviewStore는 호출자가 넘긴 측정값을 그대로 저장했다. 외부 adapter가 추가될 경우 마스크와 다른 수치 또는 실패 상태에 붙은 측정값이 표시될 수 있었다.

`record_prediction`을 다음과 같이 개선했다.

- 정상 예측의 vCDR·hCDR·면적·pixel span을 저장할 class map에서 `measure_masks`로 다시 계산.
- `measurement_source=recomputed_from_saved_labels_v1`로 계산 출처 기록.
- disc/cup이 비었는데 호출자가 `ok`라고 해도 `invalid_geometry`로 낮추고 수치 제거.
- `error`/`invalid_geometry` 상태의 전달 측정값 제거. 실패를 자동으로 성공으로 승격하지 않음.
- `errors`가 문자열 목록인지 artifact 쓰기 전에 검증.

10개 회귀 테스트가 수정 전 실패했고 수정 후 통과했다. 잘못된 vCDR .99, NaN, 누락 수치, 빈 disc/cup, 실패 상태의 수치, 잘못된 errors 형식을 포함한다. export에서도 마스크에서 다시 계산한 값이 사용됨을 확인했다. 과거 검토 기록이나 모델·학습 정책·공개 실험 수치는 다시 쓰지 않았다.

**검증:** 관련 테스트 52개 통과. 최종 전체 제품 테스트 **284 passed, 2 warnings, 323.06초**. 경고는 기존 CUDA 비결정적 `nll_loss2d` 연산 관련이다. 독립 코드 검토에서도 수정 경로에 차단 결함이 없음을 확인했다.

## 2. Oxford DDU 별도 수치 안정성 패치

대상: [저자 코드](https://github.com/omegafragger/DDU) `f597744c65df4ff51615ace5e86e82ffefe1cd0f`, `utils/gmm_utils.py`. [패치](ddu/patch.diff), [결과](ddu/results.json), [원본 대조군](ddu/original_results.json).

현재 PyTorch의 covariance 예외 문구와 저자의 문자열 비교가 맞지 않아 `gmm` 미정의 상태로 반환되는 원인을 확인했다. 격리된 패치에서 예외 문자열 의존을 없애고 Cholesky 상태 검사·dtype/크기 기반 jitter·반복 상한·명확한 입력 검증을 적용했다.

- 이 이슈를 겨냥한 동일한 경계 검사 집합: 원본 2/17, 패치 17/17 통과.
- float32/64의 영 공분산·rank deficiency·큰 feature scale에서도 유한한 밀도 확인.
- 충분한 full-rank 입력은 jitter 0을 유지하고 원래 unbiased covariance 추정과 일치. 최대 covariance 복원 오차 float32 `1.1921e-7`, float64 `2.2204e-16`.
- 누락 class·한 개 샘플·NaN/Inf·잘못된 label/shape는 명확한 오류, 반복 한도 초과는 명시적 실패.

이 17개는 결함을 겨냥한 합성 경계 검사이며 일반적인 저자 프로그램 성공률이나 논문 성능이 아니다. 원본 checkout에는 패치를 적용하지 않았고 `git apply --check`로 적용 가능성만 확인했다. DDU를 HyunOptic 추론에 통합하지 않았다. GPU·학습 embedding·OOD 정확도·calibration은 검증 범위 밖이다.

## 3. CalDiff 별도 실행·학습 경로 패치

대상: [저자 코드](https://github.com/xinwxin/CalDiff) `8b29be39e26eaf606a190a85cd1bbb90d93740bc`. [최소 3파일 패치](caldiff/patched.patch), [결과](caldiff/patched_results.json), [원본 대조군](caldiff/original_results.json).

격리된 사본에만 적용했다.

1. `Encoder.blocks`를 `ModuleList`로 등록하여 optimizer·state_dict에 encoder 가중치를 포함.
2. hard-coded CUDA 이동을 입력 device 추종으로 바꾸고 등록된 가중치 dtype에 입력을 맞춤.
3. loss의 image+prediction 입력과 prior 채널 수를 일치시킴.
4. 두 consecutive-step 입력을 `.clone()`해 caller 입력과 역전파 그래프의 in-place 변경 방지.
5. SA 누적을 MSE의 clone에서 시작하여 원래 MSE 항이 바뀌지 않게 함. 기존 계수와 `/4` 정규화는 유지.
6. 파일 안에서 실행 사용이 없는 `save_image`, `visualize`, `transforms` import를 제거. 해당 diffusion 모듈은 현재 환경에서 AST 우회 없이 직접 import됨.

**최종 11/11 통과:** 직접 module import 1개, CPU 5개, GPU 5개. 입력 보존, 유한 forward/backward, 독립적인 MSE/SA와 수동 산술 일치, encoder optimizer 갱신, encoder를 포함한 정확한 state 저장·복원을 확인했다. 등록된 UNet 110개·prior 30개·posterior 30개 parameter tensor에 유한 gradient가 있었고 calibration gradient는 nonzero였다. 원본·채널 수정만·clone 추가·최종 단계의 실패/통과 로그는 로컬에 보존했다.

원본 byte hash는 바뀌지 않았다. 최종 패치는 세 파일만 바꾸고 `git apply --check`를 통과했다. 이전의 AST import 우회를 제거한 직접 모듈 검사와 전체 학습 CLI는 구분한다.

**호환성 제한:** encoder 등록은 state_dict 구조를 바꾼다. 기존 checkpoint에는 필요한 encoder 값이 없을 수 있으며 strict load를 우회해 검증된 모델처럼 사용하면 안 된다. MSE/SA alias 수정은 과거 학습 궤적도 바꿀 수 있다. 따라서 재학습과 완전한 성능 검증이 필요하다. 데이터·공식 checkpoint·전체 CLI/DDP 학습·논문 지표는 아직 검증하지 않았다. CalDiff의 재배포 license를 확인하지 못했으므로 전체 사본을 공개하거나 제품에 통합하지 않았다.

## 4. 재실행과 증거

`ddu/`와 `caldiff/`에는 최소 diff, 이번에 작성한 build/check harness, 정리한 JSON 결과만 제공한다. 저자 저장소·의료 데이터·가중치·로컬 traceback 경로는 포함하지 않는다. 실행 환경은 Python 3.12.10/PyTorch 2.13.0+cu126이며 CalDiff GPU는 RTX 3070 Laptop이다.

Harness는 git-ignored `reports/paper_remediation_20261103/{ddu,caldiff}/`로 복사해 사용한다. 원본 저자 코드는 각각 `reports/paper_execution_20261103/oxford_mit/DDU` 및 `reports/paper_execution_20261103/caldiff/source`에 위 commit으로 준비한다. DDU의 별도 tqdm 의존성도 이전 보고서 구조를 따른다. CalDiff는 `apply_private_patch.py --stage patched`, `run_regressions.py --help`의 경로·label 인자를 확인한다. 원본 대조군은 의도적으로 nonzero exit할 수 있다. 공개 증거 폴더에서 실행해 frozen 결과를 덮어쓰지 않는다.

`manifest.json`은 본 보고서·patch·harness·JSON의 byte 길이와 SHA256을 기록한다. 원래 첫 실행의 21개 검사 결과는 수정하지 않았다. 패치 검사의 통과를 임상 신뢰성·모델 정확도 개선으로 해석하지 않는다.
