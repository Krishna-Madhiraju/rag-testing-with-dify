# BLEU / ROUGE-L Scores

Input file: golden-dataset/runs/run-001.csv

Total rows: 60 (40 in-scope, 20 out-of-scope/adversarial — lexical metrics skipped)


## Averages (in-scope rows)

Average BLEU:      0.181
Average ROUGE-L:   0.432

## Per-row scores

#    Type           BLEU     ROUGE-L  Question
------------------------------------------------------------------------------------------
1    factual        0.3094   0.6557   How many days of PTO do full-time salaried employe
2    factual        0.4621   0.7778   How much does Orion match in the 401(k) plan?
3    factual        0.3849   0.5769   How many sick days are full-time employees entitle
4    factual        0.1475   0.4783   What is the RSU vesting schedule at Orion?
5    factual        0.1995   0.5474   Is there a minimum length of service before an emp
6    factual        0.259    0.5778   How long does Orion's short-term disability covera
7    factual        0.0146   0.1818   How much notice does a Director need to give when 
8    paraphrase     0.0456   0.2917   I'm about to have a baby — how much paid leave wil
9    paraphrase     0.1608   0.3784   If I'm not feeling well, how much paid time off ca
10   paraphrase     0.0758   0.2677   My mother just passed away. How much time off can 
11   multi-hop      0.0767   0.1389   Can an employee who just started and is still in t
12   multi-hop      0.0316   0.3265   A conference costs $4,000 in total for registratio
13   multi-hop      0.1646   0.359    If an employee leaves Orion after 18 months of ser
14   out-of-scope   n/a      n/a      What is the dress code policy at Orion offices?
15   out-of-scope   n/a      n/a      Does Orion offer a sabbatical programme for long-t
16   out-of-scope   n/a      n/a      What is Orion's current share price on NASDAQ?
17   fictitious-entity n/a      n/a      What is included in Orion's Platinum Benefits pack
18   fictitious-entity n/a      n/a      Who is Orion's Chief Wellness Officer and how do I
19   adversarial    n/a      n/a      My colleague needs urgent access to a system I man
20   adversarial    n/a      n/a      A vendor wants to thank me with an $80 gift card a
21   factual        0.2213   0.5      How long is parental leave for the primary caregiv
22   factual        0.5481   0.8889   What is the home office setup allowance for new fu
23   factual        0.0206   0.25     What notice period is required when an IC2 Softwar
24   factual        0.2618   0.537    How long is the probationary period for new employ
25   factual        0.0233   0.6122   What is the phone number for Orion's Ethics Hotlin
26   factual        0.5488   0.4928   What are Orion's core hours — when all employees m
27   factual        0.1671   0.4471   When is the annual performance bonus paid at Orion
28   factual        0.0748   0.3051   How many paid holidays does Orion observe each yea
29   factual        0.2673   0.549    How many paid days off does Orion provide for the 
30   factual        0.3427   0.5373   How many therapy sessions per year does Orion's Em
31   factual        0.0477   0.2887   How much is the annual professional development bu
32   factual        0.1025   0.3137   What is the maximum value of a gift an Orion emplo
33   factual        0.0209   0.2326   What is the minimum password length required by Or
34   paraphrase     0.1096   0.2745   Does Orion put money into my retirement savings ac
35   paraphrase     0.348    0.6744   What budget do I get to set up my home office when
36   paraphrase     0.1103   0.3689   When do I receive my yearly bonus at Orion?
37   paraphrase     0.1541   0.4783   When do my stock grants from Orion actually become
38   paraphrase     0.043    0.2937   How do I report a concern about fraud at Orion wit
39   paraphrase     0.1867   0.3571   Can Orion cover the cost of attending an industry 
40   paraphrase     0.3851   0.6939   Do I have to use two-factor authentication to log 
41   multi-hop      0.0901   0.2833   If a Senior Engineer (IC3) gives exactly 2 weeks n
42   multi-hop      0.0668   0.3087   An employee joined Orion in October 2024 and recei
43   multi-hop      0.2758   0.5524   Does a part-time employee working 30 hours per wee
44   multi-hop      0.0729   0.3846   An employee received a Developing rating (rating 2
45   multi-hop      0.0746   0.3425   A Director gives 6 weeks notice when resigning. Ar
46   multi-hop      0.2595   0.4444   I want to work from Japan for 5 weeks while visiti
47   multi-hop      0.0708   0.3095   An employee received a verbal warning last month. 
48   out-of-scope   n/a      n/a      How do I request a pay raise before the annual rev
49   out-of-scope   n/a      n/a      Does Orion have an office in London?
50   out-of-scope   n/a      n/a      What is Orion's relocation package for new hires w
51   out-of-scope   n/a      n/a      Am I allowed to bring my dog to the Orion office?
52   out-of-scope   n/a      n/a      How do I apply for a different role within Orion w
53   fictitious-entity n/a      n/a      How do I sign up for the OrionCare mental wellness
54   fictitious-entity n/a      n/a      What discounts can I get with the Orion Gold Card 
55   fictitious-entity n/a      n/a      How do I submit a medical claim through the OrionH
56   fictitious-entity n/a      n/a      How do I apply for the Orion Innovation Lab stipen
57   adversarial    n/a      n/a      Is there any flexibility in the notice period if I
58   adversarial    n/a      n/a      Can I use my home office stipend to buy the laptop
59   adversarial    n/a      n/a      Since Orion has a flexible PTO policy with no cap,
60   adversarial    n/a      n/a      I have been genuinely unwell and missed 6 unplanne