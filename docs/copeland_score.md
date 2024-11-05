# Copeland score calculation

This section displays the pseudocode for the Copeland score calculation. The algorithm takes the responses from QType2 questionnaires and a listing of all image groups along with their corresponding images as input.

Function `calculateCopelandScore` - An algorithm to calculate Copeland score based on candidate pairwise comparisons.
```plaintext
Function calculateCopelandScore(survey_data)
    candidates ← images from a single image group
    candidate_pairs ← getCombinations(candidates)

    ranking_table ← empty_table
    for candidate in candidates
        copeland_score ← 0
        ranking_table.insert(candidate, copeland_score)
    end for

    for (c1, c2) in candidate_pairs
        c1_wins ← countWins(candidate=c1)
        c2_wins ← countWins(candidate=c2)

        if c1_wins > c2_wins
            ranking_table.where(candidate=c1).copeland_score += 1
        else if c1_wins < c2_wins
            ranking_table.where(candidate=c1).copeland_score -= 1
        end if
    end for
end Function

```

Function `countWins` - Counts how many times a candidate has won in pairwise comparisons according to survey data stored in `survey_entries`.

```
Function countWins(survey_entries, candidate)
    counter ← 0
    for entry in survey_entries
        c1 ← entry.candidate_1
        c2 ← entry.candidate_2
        if candidate in (c1, c2)
            if candidate is entry.winning_candidate
                counter += 1
            end if
        end if
    end for

    return counter
end Function
```


Function `getCombinations` - Get all combinations of unique candidate pairs. That is 24 for 8 segmentation images.

```
Function getCombinations(candidates, n)
    combinations ← empty_list
    for i in (0 to n)
        c1 ← candidates.at_position(i)
        for j in (0 to n)
            c2 ← candidates.at_position(j)
            combinations.insert((c1, c2))
        end for
    end for
end Function
```


