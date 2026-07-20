# EduTech Impact on AI — Student Performance Analytics Dashboard

A full-stack data analytics and AI web application that analyzes whether AI tool usage correlates with improved student performance across education levels (Class 6 through PG Year 2).

**Stack:** Flask · SQLite · Pandas · scikit-learn · Chart.js

---

## Project Summary

| Item | Detail |
|---|---|
| **Type** | Full-Stack Data Analytics + AI Web App |
| **Backend** | Python, Flask, SQLAlchemy, SQLite |
| **Data Layer** | Pandas, NumPy |
| **ML Model** | scikit-learn (Linear Regression) |
| **Frontend** | HTML, CSS, JavaScript, Chart.js |
| **Dataset** | 1000 synthetic student records (Class 6 → PG Year 2) |
| **Core Finding** | AI tool users score **+8–9 points higher** on average |

---

## Setup & Run

```bash
git clone https://github.com/Karunakarreddy-Pamireddy/edutech-ai-dashboard.git
cd edutech-ai-dashboard

python -m venv .venv
source .venv/Scripts/activate      # Windows Git Bash
# source .venv/bin/activate        # Mac/Linux

pip install -r requirements.txt
python run.py
```

Visit `http://localhost:5000`

---

## Dataset Format

Upload CSV or Excel files with these required columns:

| Column | Type | Example |
|---|---|---|
| student_id | string | S0001 |
| class_name | string | UG Year 2 |
| subject | string | Machine Learning |
| score | float (0–100) | 84.5 |
| ai_tool_used | bool | True / False |
| study_hours | float | 6.5 |
| record_date | date | 2025-03-15 |

Sample dataset included at `data/sample_student_data_1000.csv` (1000 rows, Class 6 → PG Year 2).

---

## Education Levels Covered

| Level | Classes | Key Subjects |
|---|---|---|
| Middle School | Class 6A, 6B | Math, Science, English, History, Geography |
| High School | Class 9A, 9B | Math, Physics, Chemistry, Biology |
| Senior Secondary | Class 11A, 11B | Math, Physics, Chemistry, Computer Science |
| Undergraduate | UG Year 1–4 | Statistics, Data Analysis, Machine Learning, AI Ethics |
| Post-Graduate | PG Year 1–2 | Deep Learning, Data Science, Thesis, Advanced Statistics |

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | Health check |
| POST | `/api/upload` | Upload CSV/Excel file |
| GET | `/api/batches` | List all upload batches |
| DELETE | `/api/batches/<id>` | Delete a batch and its records |
| GET | `/api/records` | View records with filters |
| GET | `/api/filter-options` | Available subjects, classes, counts |
| GET | `/api/kpis` | All KPIs and chart data (filterable) |
| GET | `/api/pipeline/summary` | Pipeline health and data stats |
| GET | `/api/pipeline/preview` | Preview cleaned/enriched DataFrame |
| GET | `/api/export/csv` | Download filtered records as CSV |
| GET | `/api/stats/summary` | Quick record/batch count for auto-refresh |
| POST | `/api/model/train` | Train the predictive ML model |
| GET | `/api/model/status` | Model metrics and status |
| POST | `/api/predict` | Predict a student's score |

---

## DB Schema

### `StudentRecord`
| Field | Type | Notes |
|---|---|---|
| id | int | Primary key |
| batch_id | int | FK to UploadBatch |
| student_id | string | e.g. S0001 |
| class_name | string | e.g. UG Year 2 |
| subject | string | e.g. Machine Learning |
| score | float | 0-100 |
| ai_tool_used | bool | Did student use an AI study tool |
| study_hours | float | Hours studied for this assessment |
| record_date | date | Date of assessment |

### `UploadBatch`
| Field | Type | Notes |
|---|---|---|
| id | int | Primary key |
| filename | string | Original uploaded filename |
| uploaded_at | datetime | Auto-set on upload |
| row_count | int | Valid rows stored |
| status | string | success / partial / failed |

---

## Data Pipeline

Managed by `app/pipeline.py`. Three stages run on every request:

1. **Cleaning** — drop bad rows, clip scores 0-100, normalize text, parse dates, fill missing study_hours with median
2. **Feature Engineering** — adds `pass_fail`, `score_band`, `ai_group`, `year_month`, `study_hours_band`
3. **Outlier Flagging** — IQR method per subject, flags but does not remove

---

## KPIs and Charts

| KPI / Chart | Description |
|---|---|
| AI vs Non-AI Score by Subject | Core insight — grouped bar comparing AI and non-AI users |
| Score Trend Over Time | Monthly line chart (overall, AI, non-AI) |
| Avg Score by Subject | Bar chart |
| Avg Score by Class | Bar chart |
| Score Distribution | Below Average / Average / Good / Excellent |
| Pass / Fail | Doughnut chart |
| AI Adoption by Class | Bar chart showing adoption % per class |
| Top 5 / Bottom 5 Leaderboard | Student leaderboard with AI badge |
| Pipeline Health Panel | Date range, mean, outliers, adoption rate |

All charts update live when filters are applied (subject, class, AI tool, date range).

---

## AI Predictive Model

- **Algorithm:** Linear Regression (scikit-learn)
- **Features:** study_hours, ai_tool_used, subject (one-hot encoded)
- **Target:** score (0-100)
- **Split:** 80% train / 20% test
- **Results on 1000-row dataset:**
  - R2 = 0.643 (explains 64% of score variance)
  - MAE = 4.3 points average error
  - AI tool usage coefficient: +9.2 (strongest single predictor)
- **Saved as:** `data/model.pkl` (joblib)
- **Disclaimer:** Trained on synthetic data. For demonstration only.

### Predict endpoint example

```bash
POST /api/predict
Content-Type: application/json

{
  "study_hours": 8,
  "ai_tool_used": true,
  "subject": "Machine Learning"
}
```

Response:
```json
{
  "predicted_score": 86.4,
  "confidence_band": { "low": 82.1, "high": 90.7 },
  "inputs": { "study_hours": 8, "ai_tool_used": true, "subject": "Machine Learning" }
}
```

---

## Dashboard Features

- **Interactive Dashboard & Multi-Tab Layout**: Dashboard, Upload, Records, Compare, Student Search, Alerts, AI Predictor, Status & User Management.
- **PDF Report Generation**:
  - **Structured PDF Report (`Report PDF`)**: Backend ReportLab generation with styled tables, KPIs, and executive insights.
  - **Visual PDF Snapshot (`Visual PDF`)**: Client-side canvas capture using `html2canvas` and `jsPDF` for instant PDF export of live charts and dashboard state.
- **Live Filtering**: Filter all charts & KPIs simultaneously by Subject, Class, AI tool usage, and Date range.
- **Export CSV**: Download filtered and pipeline-enriched data as CSV.
- **Predictive AI Model**: Linear Regression model predicting student scores based on study hours, subject, and AI tool usage.
- **Auto-Refresh Toggle**: Silently updates metrics when new upload batches arrive.
- **Responsive & Dark Mode UI**: Full dark mode support with tailored color schemes and mobile responsiveness.

---

## Build Log — 10-Day Sprint

| Day | What Was Built |
|---|---|
| **Day 1** | Flask app factory, SQLAlchemy models (StudentRecord, UploadBatch), SQLite setup, 300-row sample dataset, `/api/health` route |
| **Day 2** | `POST /api/upload` — CSV/Excel parsing with Pandas, row-level validation (score range, date format, boolean parsing, missing fields), batch tracking, upload form UI |
| **Day 3** | `app/data_access.py` data layer, `/api/records` with filters, `/api/filter-options`, batch management UI with delete, records preview table with filter dropdowns |
| **Day 4** | `app/pipeline.py` — Pandas cleaning (clip scores, normalize text, parse dates, fill nulls), feature engineering (pass_fail, score_band, ai_group, year_month, study_hours_band), IQR outlier flagging |
| **Day 5** | `app/kpis.py` — 10 KPI functions: overview cards, AI vs non-AI comparison, subject/class averages, trend over time, pass/fail, score distribution, study hours scatter, AI adoption by class, leaderboard. `GET /api/kpis` with filters |
| **Day 6** | Full Chart.js dashboard — 7 live charts wired to `/api/kpis`, KPI cards, filter bar, leaderboard, 3-tab layout |
| **Day 7** | UI polish — animated KPI counters, skeleton loaders, dynamic insight engine, pipeline health panel, drag-and-drop upload, section dividers, hover effects, responsive layout |
| **Day 8** | `GET /api/export/csv`, `GET /api/stats/summary`, auto-refresh toggle, Export CSV button, Day 9 Checkpoint tab with 8 readiness checks, full project status table |
| **Day 9** | `app/ml_model.py` — Linear Regression with sklearn Pipeline and OneHotEncoder, train/test split, R2/MAE/RMSE evaluation, joblib save. `POST /api/model/train`, `GET /api/model/status`, `POST /api/predict`. AI Predictor tab with train button, metrics panel, Predict My Score widget. Expanded dataset to 1000 rows (Class 6 to PG Year 2) |
| **Day 10** | Deployment, final testing, demo recording *(in progress)* |

---

## Key Finding

Students who use AI study tools score an average of **+8-9 points higher** than those who do not, across all subjects and education levels. AI tool usage is the **single strongest predictor** of student score in the linear regression model (coefficient +9.2), outweighing study hours (+2.3 per hour).

---

## Project Structure

```
edutech-ai-dashboard/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── models.py            # SQLAlchemy models
│   ├── routes.py            # All API endpoints
│   ├── data_processing.py   # Upload parsing and validation
│   ├── data_access.py       # DB to DataFrame layer
│   ├── pipeline.py          # Pandas cleaning and feature engineering
│   ├── kpis.py              # KPI calculation functions
│   ├── ml_model.py          # scikit-learn predictive model
│   └── templates/
│       └── index.html       # Full dashboard frontend
├── data/
│   ├── sample_student_data_1000.csv   # 1000-row sample dataset
│   ├── edutech.db                     # SQLite database (git-ignored)
│   └── model.pkl                      # Trained model (git-ignored)
├── requirements.txt
├── run.py
└── README.md
```

---

## Author

**Karunakar Reddy Pamireddy**
GitHub: [Karunakarreddy-Pamireddy](https://github.com/Karunakarreddy-Pamireddy)
