# Observer agreement measurements

The tool focuses on assessing the reliability of observer-based evaluations by implementing various inter- and intra-observer agreement algorithms. These measures are crucial for validating the consistency and accuracy of repeated or multiple assessments in research studies.

Intra-Observer agreement methods:
 - Guttman’s $\lambda$ (1, 2, 3, 5, and 6)
 - Cronbach's $\alpha$ 
 - Intercorrelation Agreement (ICC)

Inter-Observer agreement methods

- Cohen’s $\kappa$
- Krippendorff’s $\alpha$

## Inter-observer measures
Inter-observer measures evaluate the agreement between different observers when assessing the same set of questions. PyMED-DX provides several inter-observer agreement algorithms to quantify this reliability.

#### Data preparation
The algorithms are applied to the responses given to non-redundant questions for each observer involved in the comparison. For *QType1*, these responses correspond to diagnostic value scores, while for $QType2$, the responses are identifiers of images deemed to have better quality within a given image pair associated with the responded question.

[**Cohen’s kappa**](https://journals.sagepub.com/doi/10.1177/001316446002000104): A statistical measure of inter-observer agreement for categorical variables. It accounts for the agreement occurring by chance and provides a more accurate assessment of reliability between two observers. For multiple observer setup it is applied for pairs of observers.

[**Krippendorff’s alpha**](https://www.asc.upenn.edu/sites/default/files/2021-03/Computing%20Krippendorff%27s%20Alpha-Reliability.pdf): A metric used to assess the agreement among multiple observers, suitable for various types of data, including nominal, ordinal, interval, and ratio. It adjusts for chance agreement and is widely applicable across different measurement scales. The tool provides a final score that summarizes agreement across all observers, as well as scores for individual observer pairs.


## Intra-observer measures
Intra-observer measures assess the consistency of an observer when responding to the same questions multiple times. PyMED-DX implements the following intra-observer agreement algorithms.

#### Data preparation
The algorithms are applied to pairs of repeated and corresponding non-repeated responses. The data is prepared consistently for each observer, and the algorithms are executed on this standardized dataset. For $QType1$, the responses consist of diagnostic score values. For $QType2$, the responses are identifiers of images deemed to have better quality within a given image pair associated with the responded question.

[**Guttman’s lambda**](https://psycnet.apa.org/record/1946-01740-001): A set of reliability coefficients that include:
- $\lambda_{1}$: A measure of reliability based on the difference between observed and total variances.
- $\lambda_{2}$: An extension of $\lambda_{1}$, improving reliability estimates by adjusting for test length.
- $\lambda_{3}$: Equivalent to Cronbach's $\alpha$, assessing the internal consistency of the measurements.
- $\lambda_{5}$: Focuses on the reliability of split-half tests.
- $\lambda_{6}$: Adjusts reliability based on the variance of the errors.

> [!NOTE]
> Note: Although $\lambda_{4}$ exists, it is not included in the current implementation of the tool, as it is computationally demanding for larger response sample sizes. 

[**Cronebach's alpha**](https://scholarworks.indianapolis.iu.edu/items/63734e75-1604-45b6-aed8-40dddd7036ee): A widely used metric for measuring internal consistency and scale reliability.

[**Intercorrelation Agreement (ICC)**](https://en.wikipedia.org/wiki/Interclass_correlation): In statistics, the interclass correlation (or interclass correlation coefficient) quantifies the relationship between two variables belonging to different classes or types. It is determined by calculating the deviations of each variable from the mean of its respective class.
