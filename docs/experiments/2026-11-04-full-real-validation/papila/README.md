# Full reused PAPILA holdout

All 98 eyes from 49 preserved holdout patients received 13 fixed conditions and two frozen models: 2,548 predictions. All predictions and image-only priorities were saved before expert contours were interpreted. No training or policy promotion occurred. Transforms preserve image coordinates; original references remain unchanged, even where visibility is degraded.

The table gives image-weighted means against expert 1. Both readers, exact availability, equal-patient bootstrap estimates/intervals and common-eye paired original/condition changes are in [summary.json](summary.json). Do not attach the patient-weighted intervals to these image-weighted means. vCDR is conditional on measurable geometry.

| Condition | Model | Disc Dice | Cup Dice | Invalid geometry / 98 | vCDR MAE (n) |
| --- | --- | ---: | ---: | ---: | ---: |
| original | Baseline | 0.8936 | 0.6883 | 6 | 0.0728 (92) |
| original | Photometric | 0.9154 | 0.6939 | 2 | 0.0820 (96) |
| brightness_low | Baseline | 0.8426 | 0.6610 | 10 | 0.0764 (88) |
| brightness_low | Photometric | 0.8873 | 0.6654 | 6 | 0.0789 (92) |
| brightness_high | Baseline | 0.8728 | 0.6609 | 7 | 0.0773 (91) |
| brightness_high | Photometric | 0.9143 | 0.6941 | 3 | 0.0781 (95) |
| contrast_low | Baseline | 0.8270 | 0.6479 | 11 | 0.0725 (87) |
| contrast_low | Photometric | 0.8754 | 0.6459 | 8 | 0.0820 (90) |
| contrast_high | Baseline | 0.8809 | 0.6750 | 7 | 0.0757 (91) |
| contrast_high | Photometric | 0.9202 | 0.6938 | 2 | 0.0789 (96) |
| grayscale | Baseline | 0.1339 | 0.3581 | 42 | 0.5975 (56) |
| grayscale | Photometric | 0.9162 | 0.7003 | 1 | 0.0859 (97) |
| gamma_low | Baseline | 0.8710 | 0.6731 | 8 | 0.0744 (90) |
| gamma_low | Photometric | 0.9100 | 0.6886 | 3 | 0.0818 (95) |
| gamma_high | Baseline | 0.8777 | 0.6772 | 5 | 0.0736 (93) |
| gamma_high | Photometric | 0.9137 | 0.6859 | 4 | 0.0753 (94) |
| blur | Baseline | 0.8937 | 0.6880 | 6 | 0.0727 (92) |
| blur | Photometric | 0.9155 | 0.6939 | 2 | 0.0809 (96) |
| noise | Baseline | 0.8914 | 0.6888 | 6 | 0.0720 (92) |
| noise | Photometric | 0.9170 | 0.6951 | 2 | 0.0811 (96) |
| jpeg | Baseline | 0.8871 | 0.6814 | 6 | 0.0739 (92) |
| jpeg | Photometric | 0.9074 | 0.6934 | 2 | 0.0815 (96) |
| downsample | Baseline | 0.8891 | 0.6586 | 6 | 0.0789 (92) |
| downsample | Photometric | 0.9045 | 0.6784 | 2 | 0.0822 (96) |
| rgb_shift | Baseline | 0.8154 | 0.6397 | 5 | 0.1964 (93) |
| rgb_shift | Photometric | 0.9132 | 0.6935 | 4 | 0.0763 (94) |

[Independent all-mask/aggregate verification](independent_verification.json) and [exact original-only comparison with the earlier 196 predictions](original_crossrun_verification.json). No independent new patients or clinical efficacy conclusion follows from this reused cohort.
