# Solutions for Median Aggregation Dilemma

## Problem
When displaying growth of wealth charts with multiple portfolios:
- Individual portfolio medians can be displayed
- Aggregate median (correct) ≠ Sum of individual medians
- This creates visual inconsistency where aggregate line doesn't equal sum of parts

## Solution Options

### Option 1: Show Aggregate Median + Sum of Medians (Recommended)
**Display both values with clear labeling:**

- **Aggregate Median** (solid line, primary) - "Combined Portfolio Median"
- **Sum of Individual Medians** (dashed line, reference) - "Sum of Individual Medians (reference)"
- Individual portfolio medians (solid lines, different colors)

**Benefits:**
- Shows the correct aggregate value
- Shows what users might expect (sum of medians)
- Makes the difference visible and educational
- Users can see both perspectives

**Implementation:**
```javascript
// Add aggregate median (correct)
chartData.datasets.push({
    label: 'Aggregate Median (Combined)',
    data: result.aggregated.real.median,
    borderColor: 'rgb(0, 0, 0)',
    borderWidth: 3,
    pointRadius: 0
});

// Calculate and add sum of individual medians (reference)
const sumOfMedians = ageTimesteps.map((age, idx) => {
    return Object.values(result.individual_portfolios).reduce((sum, portfolio) => {
        return sum + (portfolio.real.median[idx] || 0);
    }, 0);
});

chartData.datasets.push({
    label: 'Sum of Individual Medians (Reference)',
    data: sumOfMedians,
    borderColor: 'rgb(128, 128, 128)',
    borderWidth: 2,
    borderDash: [10, 5],
    pointRadius: 0
});
```

### Option 2: Visual Explanation with Note
**Show aggregate median with explanatory note:**

- Display aggregate median as primary line
- Add a note/tooltip explaining: "The aggregate median represents the median of the combined portfolio wealth, not the sum of individual medians. This is mathematically correct because medians are not additive."

**Benefits:**
- Cleaner visualization
- Educational
- Focuses on correct value

**Implementation:**
Add a note in the chart area or legend:
```html
<div class="alert alert-info mt-2">
    <small>
        <strong>Note:</strong> The aggregate median represents the median of combined portfolio wealth, 
        not the sum of individual medians. This is mathematically correct because medians are not additive.
    </small>
</div>
```

### Option 3: Separate Charts
**Split into two visualizations:**

1. **Individual Portfolios Chart**: Show each portfolio's median trajectory
2. **Aggregate Chart**: Show only the aggregate median (with note explaining it's not the sum)

**Benefits:**
- No visual confusion
- Clear separation of concepts
- Can use different scales if needed

### Option 4: Hybrid - Mean for Aggregate, Median for Individual
**Use different metrics:**

- Individual portfolios: Show medians (less affected by outliers)
- Aggregate: Show mean (which IS additive: mean(X+Y) = mean(X) + mean(Y))

**Benefits:**
- Aggregate line equals sum of individual means
- Individual portfolios show robust median values
- Mathematically consistent

**Drawbacks:**
- Uses different metrics for different views
- May be confusing

### Option 5: Show Percentile Bands Instead
**Use percentile ranges instead of single median:**

- Show 25th-75th percentile bands for each portfolio
- Show aggregate 25th-75th percentile band
- This shows the distribution spread, not just a single point

**Benefits:**
- More informative
- Shows uncertainty
- Less focus on single point comparison

## Recommended Approach: Option 1

**Why Option 1 is best:**
1. Shows the correct value (aggregate median)
2. Shows what users might expect (sum of medians)
3. Educational - helps users understand why they differ
4. Transparent - no hidden calculations
5. Flexible - users can toggle reference line on/off

## Implementation Details

### Backend (if needed)
The backend already provides:
- `result.aggregated.real.median` - Correct aggregate median
- `result.individual_portfolios[portfolioId].real.median` - Individual medians

No backend changes needed - just calculate sum of medians in frontend.

### Frontend Changes
1. Switch from `mean` to `median` in chart data
2. Add aggregate median line
3. Calculate and add sum of individual medians as reference
4. Add legend entry explaining the difference
5. Optionally add toggle to show/hide reference line

### User Experience
- Primary focus: Aggregate median (correct value)
- Reference: Sum of medians (what users might expect)
- Individual: Each portfolio's median
- Legend: Clear labels distinguishing the lines
- Tooltip: Brief explanation on hover

## Example Chart Configuration

```javascript
{
    label: 'Portfolio 1 Median',
    data: portfolio1.real.median,
    borderColor: 'rgb(54, 162, 235)',
    borderWidth: 2,
    pointRadius: 0
},
{
    label: 'Portfolio 2 Median',
    data: portfolio2.real.median,
    borderColor: 'rgb(255, 99, 132)',
    borderWidth: 2,
    pointRadius: 0
},
{
    label: 'Aggregate Median (Combined)',
    data: aggregated.real.median,
    borderColor: 'rgb(0, 0, 0)',
    borderWidth: 3,
    pointRadius: 0
},
{
    label: 'Sum of Individual Medians (Reference)',
    data: sumOfMedians,
    borderColor: 'rgb(128, 128, 128)',
    borderWidth: 2,
    borderDash: [10, 5],
    pointRadius: 0,
    hidden: true  // Start hidden, user can toggle
}
```

