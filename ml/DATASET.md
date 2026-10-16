# SCANIA Component X — Dataset Documentation

## 1. Dataset Name

SCANIA Component X

## 2. Purpose

The dataset is used to develop and evaluate a baseline predictive-maintenance model for the Analytics Agent of the Vehicle Management System.

The model attempts to identify vehicles associated with a repair event for the monitored component.

## 3. Data Source

The dataset is the SCANIA Component X predictive-maintenance dataset.

Official dataset:

https://researchdata.se/en/catalogue/dataset/2024-34/3

The dataset is based on operational data from SCANIA heavy-duty vehicles.

## 4. Files Used

The current ML implementation uses:

- `train_operational_readouts.csv`
- `train_tte.csv`

### Operational data

The operational dataset contains:

- `vehicle_id`
- `time_step`
- 105 anonymized operational measurements

The loaded training file contains:

- 1,122,452 operational observations
- 107 columns

### Target data

The target dataset contains:

- `vehicle_id`
- `length_of_study_time_step`
- `in_study_repair`

The loaded target file contains:

- 23,550 vehicles
- 3 columns

## 5. Target Variable

The target used by the baseline model is:

`in_study_repair`

Interpretation:

- `0` → no repair recorded during the study period
- `1` → repair recorded during the study period

This is treated as a binary classification problem.

## 6. Feature Preparation

The operational dataset contains multiple observations for each vehicle over time.

For the initial baseline:

1. Operational records are sorted by `vehicle_id` and `time_step`.
2. The latest available observation for each vehicle is selected.
3. The latest operational observation is joined with the repair target using `vehicle_id`.
4. Identifier and target columns are removed from the model features.
5. Numeric features are retained for the initial model.
6. Infinite values are converted to missing values.
7. Missing values are handled using median imputation.
8. Features are standardized before logistic regression.

This produces one training example per vehicle.

## 7. Class Distribution

The training data contains:

| Class | Count |
|---|---:|
| No repair (`0`) | 21,278 |
| Repair (`1`) | 2,272 |

The dataset is therefore imbalanced toward the no-repair class.

The baseline uses class-balanced logistic regression to reduce the effect of this imbalance.

## 8. Baseline Model

The initial model is:

`LogisticRegression`

The preprocessing and model are stored together in a scikit-learn Pipeline.

This ensures that the same preprocessing steps are applied during training and prediction.

## 9. Initial Evaluation

The baseline produced:

- Accuracy: approximately 0.68
- Repair precision: 0.19
- Repair recall: 0.71
- Repair F1-score: 0.30
- ROC-AUC: 0.7624

Confusion matrix:

```text
[[2901, 1355],
 [ 131,  323]]
```

## 10. Interpretation

The baseline is able to identify a substantial portion of the repair cases, with approximately 71% recall for the positive class.

However, precision for the repair class is only approximately 19%. This means the model generates many false-positive maintenance-risk predictions.

Therefore, this model should currently be considered a baseline for experimentation and system integration rather than a production-ready maintenance decision system.

## 11. Limitations

The operational feature names are anonymized.

The dataset represents a specific SCANIA predictive-maintenance research setting and should not be assumed to represent every vehicle fleet.

The model has been trained on the SCANIA dataset and has not yet been trained on the team's actual vehicle-management database.

The model's predictions should therefore be treated as decision-support information rather than definitive statements that a vehicle will fail.

The current baseline uses the latest available operational observation rather than a more advanced temporal representation of the vehicle's complete history.

Real-world model performance for the team's fleet can only be established after appropriate historical vehicle data and maintenance outcomes become available.

## 12. License

The SCANIA Component X dataset is distributed with its associated research publication and dataset terms. The dataset's current access and licensing conditions should be checked at the official repository before redistribution.

The research publication is available under Creative Commons Attribution 4.0.

## 13. Future Improvements

Potential improvements include:

- temporal feature engineering
- better handling of the class imbalance
- model comparison
- hyperparameter tuning
- probability calibration
- feature importance/explainability
- validation on the team's actual fleet data
- monitoring for input drift
- retraining using real maintenance outcomes