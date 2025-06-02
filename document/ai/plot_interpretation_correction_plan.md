# Plot Interpretation Correction Plan

## 1. Issue Overview

The previous implementation and documentation for x-P plots (e.g., n-P plots) were based on an interpretation where P1, P2, ..., Pr represented the "expected final rating of each account". The desired interpretation, however, is that P1, P2, ..., Pr should represent the "overall expected rating *if the next game is played with* account 1, account 2, ..., account r", respectively. This allows for a direct comparison of the strategic value of choosing each account for the next match.

This document outlines the changes made to align the implementation and documentation with this corrected interpretation.

## 2. Affected Files and Summary of Changes

The following files were modified:

*   **`src/core/dp.py`**:
    *   Added a new public function: `get_expected_values_for_each_action(n, state, params)`.
    *   This function calculates the expected value for playing a match with each specific account, given the current state (`n` games left, current `ratings`). It returns a list `[E_play_account_0, E_play_account_1, ...]`.

*   **`src/core/dp_wrapper.py`**:
    *   Renamed `evaluate_multi_account_expected_rating` to `get_expected_values_per_action`.
    *   This function now calls `dp.get_expected_values_for_each_action` and directly returns the list of action-specific expected values, removing the previous heuristic.

*   **`src/experiments/experiment_runner.py`**:
    *   Updated to import and use `get_expected_values_per_action` from `dp_wrapper.py`.
    *   Internal variable names were changed from `expected_ratings` to `action_specific_expected_values` to reflect the new meaning of the data being processed.

*   **`document/permanent/実験計画書.md` (Experiment Plan Document)**:
    *   **Section 3.1 ("x-Pプロット データフォーマット")**: The description of `P1～Pr` was changed from "各アカウントの期待レート" (expected rate for each account) to "アカウントiを選択してプレイした場合の期待値" (expected value when playing by selecting account i).
    *   **Section 3.4 ("期待値計算仕様")**: The text was updated to explain that `P1...Pr` are now the direct outputs of `get_expected_values_for_each_action`, representing the expected value if a game is played with the respective account.
    *   *(Note: Direct modification of this file by the AI agent failed due to tool limitations with non-ASCII filenames. These changes need to be manually applied by the user based on the provided details.)*

*   **`src/experiments/plotting.py`**:
    *   The default `y_label` in the `plot_xp` function was changed from "期待レート（整数形式）" (Expected Rate (integer format)) to "アカウント選択時期待値" (Expected Value when Selecting Account).

## 3. Impact

These changes ensure that the P-values in the generated plots accurately reflect the strategic decision-making process of choosing which account to play next. This provides a clearer basis for analyzing multi-account rating strategies.
