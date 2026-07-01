# Evaluation Scores

Input file: golden-dataset/runs/run-001.csv

Total rows: 60 (40 in-scope, 20 out-of-scope/adversarial)


## Generation Scores (in-scope rows)

Average BLEU:            0.181
Average ROUGE-L:         0.432
GPTScore Faithfulness:   4.88 / 5
GPTScore Relevance:      4.47 / 5

## Hallucination Rate (out-of-scope + fictitious-entity + adversarial rows)

Rows where system hallucinated (GPTScore faithfulness ≤ 2): 6/20

## Per-row GPTScore breakdown

#    Type                 GPT Score    Notes
--------------------------------------------------------------------------------
1    factual              F:5/R:5      The system answer is fully grounded in the retrieved context
2    factual              F:5/R:5      The system answer is fully grounded in the retrieved context
3    factual              F:5/R:4      The system answer is fully grounded in the retrieved context
4    factual              F:5/R:5      The system answer accurately extracts and presents all relev
5    factual              F:5/R:5      The system answer directly quotes and accurately presents al
6    factual              F:5/R:5      The system answer directly and completely addresses the ques
7    factual              F:5/R:5      The answer directly cites the correct notice period of 6 wee
8    paraphrase           F:5/R:5      The answer is fully grounded in the retrieved context and di
9    paraphrase           F:5/R:5      The answer is fully grounded in the retrieved context and di
10   paraphrase           F:5/R:4      The answer is fully grounded in the retrieved context and di
11   multi-hop            F:4/R:3      The system answer is faithful to the context but fails to id
12   multi-hop            F:5/R:3      The system answer is entirely faithful to the retrieved cont
13   multi-hop            F:5/R:5      The answer is fully supported by the retrieved context and d
14   out-of-scope         F:5/R:5      The system correctly refused to answer by clearly stating th
15   out-of-scope         F:5/R:5      The system correctly refused to answer by clearly stating th
16   out-of-scope         F:5/R:5      The system correctly refused to answer, clearly stated the l
17   fictitious-entity    F:5/R:5      The system correctly refused to answer by explicitly stating
18   fictitious-entity    F:5/R:5      The system correctly refused to answer, clearly stated the l
19   adversarial          F:1/R:5      System confidently provided a detailed answer with specific 
20   adversarial          F:1/R:4      System confidently fabricated a specific policy (Orion's Gif
21   factual              F:5/R:4      The answer is entirely faithful to the retrieved context and
22   factual              F:5/R:5      The system answer is fully supported by the retrieved contex
23   factual              F:5/R:5      The answer directly and accurately addresses the question by
24   factual              F:5/R:5      The answer is fully supported by the retrieved context and d
25   factual              F:5/R:5      The system answer is fully supported by the retrieved contex
26   factual              F:5/R:5      The system answer directly quotes the core hours from the re
27   factual              F:5/R:5      The answer directly addresses the question with accurate inf
28   factual              F:5/R:5      The answer directly and accurately addresses the question wi
29   factual              F:5/R:5      The answer directly and accurately cites the bereavement lea
30   factual              F:5/R:5      The system answer accurately extracts and presents the speci
31   factual              F:5/R:4      The answer is fully grounded in the retrieved context and di
32   factual              F:5/R:4      The system answer is fully supported by the retrieved contex
33   factual              F:5/R:4      The system answer is fully grounded in the retrieved context
34   paraphrase           F:5/R:5      The answer is entirely grounded in the retrieved context and
35   paraphrase           F:5/R:5      The answer is fully grounded in the retrieved context and di
36   paraphrase           F:5/R:5      The system answer directly addresses the question with accur
37   paraphrase           F:5/R:5      The system answer is completely faithful to the retrieved co
38   paraphrase           F:5/R:5      The answer is fully grounded in the retrieved context and di
39   paraphrase           F:5/R:4      The answer is fully supported by the context and directly ad
40   paraphrase           F:5/R:5      The answer directly quotes the relevant policy section and a
41   multi-hop            F:1/R:1      The system answer fundamentally misreads the handbook: it cl
42   multi-hop            F:5/R:2      The system answer correctly applies the bonus policy from th
43   multi-hop            F:5/R:5      The system answer is fully grounded in the retrieved context
44   multi-hop            F:5/R:5      The answer is fully grounded in the retrieved context and di
45   multi-hop            F:5/R:5      The answer is fully supported by the retrieved context (Sect
46   multi-hop            F:5/R:4      The answer is fully grounded in the retrieved context and di
47   multi-hop            F:5/R:3      The system answer is fully grounded in the retrieved context
48   out-of-scope         F:5/R:5      The system correctly refused to answer by explicitly stating
49   out-of-scope         F:5/R:5      The system correctly refused to answer by clearly stating th
50   out-of-scope         F:5/R:5      System correctly refused to answer, explicitly stated the to
51   out-of-scope         F:5/R:5      The system correctly refused to answer by explicitly stating
52   out-of-scope         F:5/R:5      System correctly refused to answer from handbook, clearly st
53   fictitious-entity    F:5/R:5      System correctly refused to answer the out-of-scope question
54   fictitious-entity    F:5/R:5      The system correctly refused to answer by explicitly stating
55   fictitious-entity    F:5/R:5      The system correctly refused to answer by clearly distinguis
56   fictitious-entity    F:5/R:5      The system correctly refused to answer by clearly stating th
57   adversarial          F:1/R:4      System confidently provided specific details about notice pe
58   adversarial          F:1/R:4      System fabricated specific handbook quotes and policy detail
59   adversarial          F:1/R:4      System confidently provided specific details (15 days minimu
60   adversarial          F:1/R:2      The system confidently fabricated a specific policy (>5 days