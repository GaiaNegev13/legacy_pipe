import matplotlib.pyplot as plt
import pandas as pd

def compare_dist(df, comparable_variable, differentiation_variable, bins=30, figsize=(8,5), alpha=0.5):
    """
    Compare the distributions of comparable_variable across groups defined by differentiation_variable.

    Shows overlaid histograms and prints summary statistics for each group.

    Parameters:
    - df: pandas DataFrame with the data
    - comparable_variable: str, column to compare (e.g. 'tiv')
    - differentiation_variable: str, grouping column (e.g. 'institute')
    - bins: int or sequence, number of histogram bins (default 30)
    - figsize: tuple, figure size
    - alpha: float, histogram transparency
    """
    unique_groups = df[differentiation_variable].dropna().unique()
    plt.figure(figsize=figsize)

    summary = {}

    for group in unique_groups:
        vals = df[df[differentiation_variable] == group][comparable_variable].dropna()
        plt.hist(vals, bins=bins, alpha=alpha, label=str(group))
        mean = vals.mean()
        sd = vals.std()
        rng = (vals.min(), vals.max())
        summary[group] = {
            'mean': round(mean,3),
            'sd': round(sd,3),
            'range': (round(rng[0],3), round(rng[1],3)),
            'n': len(vals)
        }

    plt.legend(title=differentiation_variable)
    plt.title(f"Distribution of {comparable_variable} by {differentiation_variable}")
    plt.xlabel(comparable_variable)
    plt.ylabel('Count')
    plt.tight_layout()
    plt.show()

    print(f"Summary statistics for {comparable_variable} by {differentiation_variable}:")
    for group, props in summary.items():
        print(f"  {group}: mean={props['mean']}, sd={props['sd']}, range={props['range']}, n={props['n']}")

    return summary
