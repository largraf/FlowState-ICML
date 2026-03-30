# Additional material for rebuttal

<a id="datasets"></a>
## Performance evaluation on standard datasets
Comparison table of various models on standard time series datasets. The best MAE or MSE values are markd in ***bold*** and second best <u>underlined</u>

| Dataset | Metric | FlowState-10M(4k) | LightGTS-mini | MOIRAI-Large (2024) | iTransformer (2024) | PatchTST (2024) |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| ETTm1 | MSE | <u>0.346</u> | ***0.327*** | 0.390 | 0.407 | 0.387 |
| | MAE | ***0.354*** | <u>0.370</u> | 0.389 | 0.410 | 0.400 |
| ETTm2 | MSE | <u>0.258</u> | ***0.247*** | 0.276 | 0.288 | 0.281 |
| | MAE | ***0.299*** | <u>0.316</u> | 0.320 | 0.332 | 0.326 |
| ETTh1 | MSE | <u>0.393</u> | ***0.388*** | 0.510 | 0.454 | 0.469 |
| | MAE | ***0.403*** | <u>0.419</u> | 0.469 | 0.448 | 0.455 |
| ETTh2 | MSE | 0.364 | ***0.348*** | <u>0.354</u> | 0.383 | 0.387 |
| | MAE | <u>0.384</u> | 0.395 | ***0.376*** | 0.407 | 0.407 |
| Traffic | MSE | ***0.381*** | <u>0.561</u> | - | - | - |
| | MAE | ***0.234*** | <u>0.381</u> | - | - | - |
| Weather | MSE | <u>0.211</u> | ***0.208*** | 0.259 | 0.258 | 0.259 |
| | MAE | ***0.236*** | <u>0.256</u> | 0.275 | 0.278 | 0.281 |
| Exchange | MSE | <u>0.349</u> | ***0.347*** | - | - | - |
| | MAE | <u>0.396</u> | ***0.396*** | - | - | - |
| Electricity | MSE | ***0.155*** | 0.213 | 0.188 | <u>0.178</u> | 0.216 |
| | MAE | ***0.240*** | 0.308 | 0.273 | <u>0.270</u> | 0.304 |