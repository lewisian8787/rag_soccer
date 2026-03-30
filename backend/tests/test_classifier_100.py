import sys
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "retrieval"))
from query import classify_query

TEST_CASES = [
    # --- Pure tactical — rag only ---
    {"query": "How do Arsenal press high?",                                          "expected": {"rag"}},
    {"query": "How does Guardiola set up against a low block?",                      "expected": {"rag"}},
    {"query": "How do Liverpool defend set pieces?",                                 "expected": {"rag"}},
    {"query": "What formation does Arsenal use when they don't have the ball?",      "expected": {"rag"}},
    {"query": "How do Manchester City build out from the back?",                     "expected": {"rag"}},
    {"query": "How does Chelsea use their fullbacks in attack?",                     "expected": {"rag"}},
    {"query": "What is Liverpool's pressing trigger?",                               "expected": {"rag"}},
    {"query": "How do Tottenham transition from defence to attack?",                 "expected": {"rag"}},
    {"query": "How does Arsenal's back four hold their shape without the ball?",     "expected": {"rag"}},
    {"query": "What role does Rodri play in City's build-up?",                       "expected": {"rag"}},
    {"query": "How do Manchester United defend against teams that play out wide?",   "expected": {"rag"}},
    {"query": "How does Newcastle set up to defend crosses?",                        "expected": {"rag"}},
    {"query": "What is Aston Villa's structure in midfield?",                        "expected": {"rag"}},
    {"query": "How do Brighton play out of a press?",                                "expected": {"rag"}},
    {"query": "How does Spurs use the half-spaces in attack?",                       "expected": {"rag"}},
    {"query": "What does Arsenal do differently at home vs away?",                   "expected": {"rag"}},
    {"query": "How does Liverpool's midfield press coordinated with the forwards?",  "expected": {"rag"}},
    {"query": "How do Chelsea defend corners?",                                      "expected": {"rag"}},
    {"query": "What is Fulham's defensive shape?",                                   "expected": {"rag"}},
    {"query": "How do Brentford use long balls to bypass the press?",                "expected": {"rag"}},

    # --- Pure stat lookups — stats only ---
    {"query": "How many goals has Salah scored?",                                    "expected": {"stats"}},
    {"query": "Who has the most assists this season?",                               "expected": {"stats"}},
    {"query": "What was the score in Arsenal vs Chelsea?",                           "expected": {"stats"}},
    {"query": "How many yellow cards has Bruno Fernandes received?",                 "expected": {"stats"}},
    {"query": "Who has played the most minutes in the Premier League this season?",  "expected": {"stats"}},
    {"query": "Who are the top five scorers in the league?",                         "expected": {"stats"}},
    {"query": "How many goals has Haaland scored at home?",                          "expected": {"stats"}},
    {"query": "What was the result of Liverpool's last away game?",                  "expected": {"stats"}},
    {"query": "How many red cards have been issued this season?",                    "expected": {"stats"}},
    {"query": "Who has the highest average rating this season?",                     "expected": {"stats"}},
    {"query": "How many assists does Trent Alexander-Arnold have?",                  "expected": {"stats"}},
    {"query": "What is Arsenal's home record this season?",                          "expected": {"stats"}},
    {"query": "Who has scored the most headed goals?",                               "expected": {"stats"}},
    {"query": "How many goals has Chelsea conceded this season?",                    "expected": {"stats"}},
    {"query": "Did Salah score in the last derby?",                                  "expected": {"stats"}},
    {"query": "Who has the most clean sheets this season?",                          "expected": {"stats"}},
    {"query": "How many goals has Son scored against Arsenal?",                      "expected": {"stats"}},
    {"query": "What is Manchester City's points total?",                             "expected": {"stats"}},
    {"query": "Who scored first in Arsenal vs Spurs?",                               "expected": {"stats"}},
    {"query": "How many hat tricks have there been this season?",                    "expected": {"stats"}},

    # --- Player form — both ---
    {"query": "How has Salah been playing this season?",                             "expected": {"rag", "stats"}},
    {"query": "Is Bukayo Saka in good form right now?",                              "expected": {"rag", "stats"}},
    {"query": "How has Haaland been performing recently?",                           "expected": {"rag", "stats"}},
    {"query": "Has Bruno Fernandes been consistent this season?",                    "expected": {"rag", "stats"}},
    {"query": "How is Trent Alexander-Arnold performing this season?",               "expected": {"rag", "stats"}},
    {"query": "Has Martinelli been effective this season?",                          "expected": {"rag", "stats"}},
    {"query": "How has De Bruyne looked since returning from injury?",               "expected": {"rag", "stats"}},
    {"query": "Is Son Heung-min playing well this season?",                          "expected": {"rag", "stats"}},
    {"query": "How has Virgil van Dijk been at the back recently?",                  "expected": {"rag", "stats"}},
    {"query": "Has Palmer been as good as last season?",                             "expected": {"rag", "stats"}},
    {"query": "How is Rashford performing under the new manager?",                   "expected": {"rag", "stats"}},
    {"query": "Is Isak living up to expectations this season?",                      "expected": {"rag", "stats"}},
    {"query": "How has Watkins been since his injury return?",                       "expected": {"rag", "stats"}},
    {"query": "Has Salah looked as sharp as previous seasons?",                      "expected": {"rag", "stats"}},
    {"query": "Is Diogo Jota playing well when selected?",                           "expected": {"rag", "stats"}},

    # --- Fantasy — both ---
    {"query": "Is Saka worth picking for fantasy this week?",                        "expected": {"rag", "stats"}},
    {"query": "Should I start Haaland or Watkins this gameweek?",                   "expected": {"rag", "stats"}},
    {"query": "Which defenders are good fantasy picks right now?",                   "expected": {"rag", "stats"}},
    {"query": "Who is the best value striker in fantasy football?",                  "expected": {"rag", "stats"}},
    {"query": "Which goalkeeper should I pick for the next two gameweeks?",          "expected": {"rag", "stats"}},
    {"query": "Is Palmer a good captain choice this week?",                          "expected": {"rag", "stats"}},
    {"query": "Which Arsenal players are worth owning in fantasy?",                  "expected": {"rag", "stats"}},
    {"query": "Who should I transfer in for the next gameweek?",                     "expected": {"rag", "stats"}},
    {"query": "Which midfielders have the best upcoming fixtures?",                  "expected": {"rag", "stats"}},
    {"query": "Is Son a reliable fantasy asset this season?",                        "expected": {"rag", "stats"}},

    # --- Subjective quality — both ---
    {"query": "Who has been clinical in front of goal?",                             "expected": {"rag", "stats"}},
    {"query": "Which midfielders have been contributing recently?",                  "expected": {"rag", "stats"}},
    {"query": "Who has been the most creative player in the league?",                "expected": {"rag", "stats"}},
    {"query": "Which defenders have been the most commanding this season?",          "expected": {"rag", "stats"}},
    {"query": "Who has been the best player at Arsenal this season?",                "expected": {"rag", "stats"}},
    {"query": "Which striker has looked the most dangerous recently?",               "expected": {"rag", "stats"}},
    {"query": "Who has been the standout performer at Liverpool?",                   "expected": {"rag", "stats"}},
    {"query": "Which forwards have been threatening but unlucky in front of goal?",  "expected": {"rag", "stats"}},
    {"query": "Who has been the most consistent fullback in the league?",            "expected": {"rag", "stats"}},
    {"query": "Which players have improved the most this season?",                   "expected": {"rag", "stats"}},

    # --- Mixed / edge cases — both ---
    {"query": "Why has Haaland scored so many goals this season?",                   "expected": {"rag", "stats"}},
    {"query": "Is Arsenal's attack as effective without Saka?",                      "expected": {"rag", "stats"}},
    {"query": "How has Liverpool coped since Salah's injury?",                       "expected": {"rag", "stats"}},
    {"query": "Which team has the best attack in the league right now?",             "expected": {"rag", "stats"}},
    {"query": "Why are Chelsea struggling to score this season?",                    "expected": {"rag", "stats"}},
    {"query": "Has Spurs improved defensively under their new manager?",             "expected": {"rag", "stats"}},
    {"query": "How does Arsenal's goal threat compare to last season?",              "expected": {"rag", "stats"}},
    {"query": "Who is the best penalty taker in the league?",                        "expected": {"rag", "stats"}},
    {"query": "Which team creates the most chances from open play?",                 "expected": {"rag", "stats"}},
    {"query": "Is Manchester City as dominant as they were under peak Guardiola?",   "expected": {"rag", "stats"}},
    {"query": "How does Liverpool's press affect their opponents' passing?",         "expected": {"rag", "stats"}},
    {"query": "Which players tend to perform well in big matches?",                  "expected": {"rag", "stats"}},
    {"query": "Has Arsenal's defensive record improved since the new season?",       "expected": {"rag", "stats"}},
    {"query": "Who is the most important player for Man City right now?",            "expected": {"rag", "stats"}},
    {"query": "Which teams struggle the most away from home?",                       "expected": {"rag", "stats"}},
]

passed = 0
failed = 0

for case in TEST_CASES:
    result = classify_query(case["query"])
    ok = result == case["expected"]
    status = "PASS" if ok else "FAIL"
    if ok:
        passed += 1
    else:
        failed += 1
    print(f"[{status}] {case['query']}")
    print(f"       expected: {case['expected']}")
    print(f"       got:      {result}")
    print()

print(f"\n{passed}/{len(TEST_CASES)} passed")
sys.exit(0 if failed == 0 else 1)
