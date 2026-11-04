# AI disclosure

## AI in the product

The optional segmentation model is a small U-Net implemented in PyTorch. It receives an image only, applies fixed whole-image letterboxing and normalization, and predicts background/rim/cup. Largest-disc-component postprocessing is predeclared. Reference masks do not enter inference or the review priority.

The review queue compares two explicitly selected frozen local models. Their disagreement is a descriptive ordering feature, not an error probability or diagnosis. Both models can agree on a wrong structure. The original photometric follow-up did not meet its success criteria; selecting it for comparison does not promote it to the default training policy.

No LLM/API receives uploaded images or review notes. The application does not generate medical advice.

## AI-assisted development

OpenAI Codex assisted the design, Python implementation, tests, code review and documentation. Task-focused agents were used for persistence, inference regressions and export/runner implementation. Test results and review findings are retained in the development record. AI-produced code must be treated as fallible; passing tests establish checked software behavior, not clinical validity.

Concrete review-driven decisions: stale source caching and partial bundle cache identity were reproduced and targeted by regressions; incompatible preprocessing contracts must be rejected rather than silently ignored; multi-frame TIFF must not silently drop frames. The development log and tests show the checking procedure and outcomes.

The repository owner requested and reviewed the design discussion. Automated agent review is not independent human clinical review. No human acceptance study, clinician sign-off, or final frozen-manuscript approval is claimed for this release. The submitter should inspect the final diff, demonstration and validation before personally attesting to them. Do not count this disclosure alone as satisfying a rubric item requiring evidence of human checking.
