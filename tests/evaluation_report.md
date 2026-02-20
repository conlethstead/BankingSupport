
======================================================================
📊 EVALUATION REPORT
======================================================================

## Overall Results
- Total tests: 55
- Passed: 52 (94.5%)
- Failed: 3
- Errors: 0

## Accuracy Metrics
- Classification accuracy: 100.0% (55/55)
- Handler routing accuracy: 94.5% (52/55)
- Escalation accuracy: 40.0% (2/5)
- Confidence calibration: 100.0% (47/47)

## Performance
- Avg processing time: 4899 ms
- P50 processing time: 4254 ms
- P95 processing time: 8483 ms

## Accuracy by Classification Type
- negative_feedback: 100.0% (20/20)
- positive_feedback: 100.0% (15/15)
- query: 100.0% (20/20)

## Pass Rate by Tag (top 10)
- positive: 100.0% (15/15)
- negative: 100.0% (15/15)
- query: 100.0% (15/15)
- edge_case: 70.0% (7/10)
- mixed_sentiment: 66.7% (2/3)
- product_praise: 100.0% (2/2)
- ticket_lookup: 100.0% (2/2)
- gratitude: 100.0% (1/1)
- simple: 100.0% (1/1)
- service_praise: 100.0% (1/1)

## Failed Cases (3)

### EDGE002
- Input: "The service was okay I guess, but there were some issues tha..."
- Expected: negative_feedback → NegativeFeedbackAgent
- Actual: negative_feedback → EscalationAgent (conf: 0.70)

### EDGE004
- Input: "?"
- Expected: query → QueryAgent
- Actual: query → EscalationAgent (conf: 0.70)

### EDGE007
- Input: "ticket 999999"
- Expected: query → QueryAgent
- Actual: query → EscalationAgent (conf: 0.70)

======================================================================