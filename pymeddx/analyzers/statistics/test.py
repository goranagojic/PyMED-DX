import numpy as np

# Set parameters
num_samples = 3000
difference_ratio = 0.1  # 10% differing elements
value_range = (-5, 5)

# Generate the first array with random values from -5 to 5
array1 = np.random.randint(value_range[0], value_range[1] + 1, num_samples)

# Copy array1 to create array2
array2 = np.copy(array1)

# Calculate the number of differing elements
num_differences = int(num_samples * difference_ratio)

# Randomly select indices to change in array2
indices_to_change = np.random.choice(num_samples, num_differences, replace=False)

# Modify values at selected indices in array2
for idx in indices_to_change:
    # Ensure the new value is different from the original value in array1
    new_value = array1[idx]
    while new_value == array1[idx]:
        new_value = np.random.randint(value_range[0], value_range[1] + 1)
    array2[idx] = new_value

print("Array 1:", array1)
print("Array 2:", array2)


from intraobserver import cronbachs_alpha

scores_per_observer = [
    list(array1),
    list(array2)
]
r = cronbachs_alpha(scores_per_observer)
print(f"Cronbach's alpha value:\n{r['alpha']}")
print(f"Cronbach's alpha 95-percent confidence interval:\n{r['95-percent-confidence-interval']}")
