# Advanced Statistical Modeling for Football Probabilities
## Current Implementation Overview

In our `MatchAnalyzer` engine (`matches/services/advanced_stats.py`), we currently use a hybrid approach to calculate probabilities:

### 1. Match Winner (1X2) & Double Chance
We use an advanced **Multi-Factor Weighted Model** (Predictive Analysis) that combines:
- **Specific Form** (Home/Away) (40%)
- **Poisson Distribution / xG Model** (35%): Calculates Expected Goals (xG) based on attack/defense strength and applies a Poisson distribution to predict score probabilities.
- **General Form** (15%)
- **Head-to-Head (H2H)** (10%)

*Note on Bookmaker Odds: We intentionally DO NOT include bookmaker odds in our calculation. If we include the bookie's odds in our model, we become biased by their margins and public hype. To find true "Value Bets" (apostas de valor), our model must be 100% pure and independent. We calculate our own "True Odds" and then compare them to the bookmaker's odds to find market errors.*

### 2. Over/Under, BTTS, and HT Goals
We currently use **Historical Frequency Analysis** (Descriptive Statistics).
- We look at a rolling window of recent matches (e.g., last 10 games for both teams).
- We count the absolute frequency of occurrences (e.g., "Out of 20 combined games, 14 ended with >2.5 goals = 70%").

## Evaluation: Is this the "Best" Method?

While Historical Frequency is excellent for showing "recent form" to the user, it is **not the best predictive method** for high-precision forecasting. Frequency analysis is backward-looking and heavily influenced by outliers or the specific opponents a team recently faced.

### The Industry Standard (The "Best" Method)
The most sophisticated sportsbooks and betting syndicates use **Bivariate Poisson Distribution** and the **Dixon-Coles Model** to predict Over/Under and BTTS.

Instead of counting past occurrences, this method:
1. Calculates the **Expected Goals (xG)** for the Home Team and Away Team for this specific matchup (adjusting for attack strength, defense weakness, and home advantage).
2. Runs a **Poisson Distribution Matrix** to calculate the exact mathematical probability of every possible correct score (0-0, 1-0, 0-1, 1-1, 2-1, etc., up to 7+ goals).
3. Sums these probabilities to find the exact market odds.
   - Example: **Over 2.5** is simply `100% - (Prob(0-0) + Prob(1-0) + Prob(0-1) + Prob(1-1) + Prob(2-0) + Prob(0-2))`.
   - Example: **BTTS** is the sum of all score probabilities where both teams score (1-1, 2-1, 1-2, etc.).

## Action Plan for Upgrading Statsfut
To upgrade Statsfut to a truly professional, high-precision forecasting tool, we need to transition the Over/Under and BTTS markets from "Historical Frequency" to a "Poisson Matrix Prediction".

**Step 1:** Extract the Expected Goals (xG) calculation currently used in `get_match_odds_probs`.
**Step 2:** Build a 2D Poisson Matrix to calculate all scoreline probabilities.
**Step 3:** Derive Over/Under (0.5 to 4.5), BTTS, and Clean Sheet probabilities directly from the Poisson Matrix.
**Step 4:** Blend this Poisson prediction with the Historical Frequency (e.g., 70% Poisson / 30% Recent Form) to create the ultimate, high-precision metric.

---
**Status**: Implemented on localhost (Hybrid Model 70/30 applied, Fair Odds integrated, Over 4.5 Goals added, Over 26.5 Shots removed). See skill `13-arquitetura_match_detail_e_motor_hibrido.md` for full details.
