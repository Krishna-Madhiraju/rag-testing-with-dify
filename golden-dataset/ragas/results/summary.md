# RAGAS Evaluation Summary

Input: golden-dataset/runs/run-001.csv

Judge LLM: Claude (claude-haiku-4-5-20251001) | Embeddings: local sentence-transformers/all-MiniLM-L6-v2

Rows evaluated: 40 in-scope rows with actual answers


## Average Scores (in-scope rows)

Faithfulness                   0.906
Answer Relevancy               0.776
Context Precision              0.624
Context Recall                 0.933

## By Query Type


### adversarial (6 rows)
  Faithfulness                   n/a
  Answer Relevancy               n/a
  Context Precision              n/a
  Context Recall                 n/a

### factual (20 rows)
  Faithfulness                   0.987
  Answer Relevancy               0.887
  Context Precision              0.627
  Context Recall                 1.000

### fictitious-entity (6 rows)
  Faithfulness                   n/a
  Answer Relevancy               n/a
  Context Precision              n/a
  Context Recall                 n/a

### multi-hop (10 rows)
  Faithfulness                   0.705
  Answer Relevancy               0.648
  Context Precision              0.656
  Context Recall                 0.733

### out-of-scope (8 rows)
  Faithfulness                   n/a
  Answer Relevancy               n/a
  Context Precision              n/a
  Context Recall                 n/a

### paraphrase (10 rows)
  Faithfulness                   0.963
  Answer Relevancy               0.683
  Context Precision              0.587
  Context Recall                 1.000