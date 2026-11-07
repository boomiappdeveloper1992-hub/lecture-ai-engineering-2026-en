- Level attempted: Basic
- Settings or data changed: `num_train_epochs=5`, `lora_r=4` (each changes exactly one value from the baseline; every run starts from a freshly loaded base model)
- Results (comparison table / numbers):

| run | change | format_rate | content_rate | final loss | train time (s) | steps | trainable % | regressions | remaining failure types |
|---|---|---|---|---|---|---|---|---|---|
| before training | - | 0.095 | 0.000 | - | - | - | - | - | - |
| baseline | baseline | 1.000 | 0.905 | 0.014000752568244934 | 246.6 | 40 | 0.842 | 0 | asserted on an ungrounded question ×2 |
| epochs5 | num_train_epochs=5 | 1.000 | 0.714 | 1.5743242263793946 | 68.1 | 10 | 0.842 | 0 | dodged a grounded question with needs-review ×1; missing required words ×4; asserted on an ungrounded question ×1 |
| r4 | lora_r=4 | 1.000 | 0.905 | 0.01268608272075653 | 243.9 | 40 | 0.212 | 0 | asserted on an ungrounded question ×2 |
