# Position Bias Report (pairwise judge, order swapped)

Source: `results\position_bias_1792945160.jsonl`, prompt `prompts/pairwise_v1.txt`, model `openai/gpt-oss-120b`.

Each pair of replies to the same customer message is judged twice, with the
order swapped. A judge with no position bias picks the same reply both times.

## Summary

| Measure | Value |
|---|---|
| Pairs judged in both orders | 10 |
| Same reply picked in both orders | 10/10 (100%) |
| Verdict changed after swap | 0/10 (0%) |
| Calls where the first-shown reply (A) won | 10/20 (50%) of non-tie calls |
| Tie verdicts | 0/20 (0%) of calls |
| Failed calls (excluded) | 0 |
| Cost per call (paid-tier equivalent) | $0.000239 |
| Latency per call, p50 | 0.91s |

With no position bias, A should win about half of the non-tie calls, and
no verdict should change after the swap.

## Per pair

| Pair | Winner (first item shown as A) | Winner (swapped) | Result |
|---|---|---|---|
| G12|P13 | P13 | P13 | consistent |
| G41|G42 | G41 | G41 | consistent |
| G43|G44 | G44 | G44 | consistent |
| G49|G50 | G49 | G49 | consistent |
| G52|G53 | G52 | G52 | consistent |
| P01|P02 | P01 | P01 | consistent |
| P07|P08 | P07 | P07 | consistent |
| P09|P10 | P09 | P09 | consistent |
| P11|P12 | P11 | P11 | consistent |
| P17|P18 | P17 | P17 | consistent |
