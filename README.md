# EduTech Impact on AI — Day 1 Scaffold

Full-stack data analytics + AI dashboard. Tracks student performance and whether AI tool usage correlates with score improvement.

## What's in this scaffold
**Day 1:**
- Flask app factory + blueprint structure (`app/`)
- SQLite DB wired up via Flask-SQLAlchemy, auto-creates tables on startup
- Data schema (`StudentRecord`, `UploadBatch`)
- Sample dataset (`data/sample_student_data.csv`, 300 rows) with a real AI-usage-vs-score signal baked in

**Day 2 (new):**
- `POST /api/upload` — accepts CSV/Excel, validates row-by-row, stores good rows, skips and reports bad ones (never crashes on bad data)
- `GET /api/batches` — lists upload history
- `DELETE /api/batches/<id>` — deletes a batch and its records (cleanup for bad uploads)
- `app/data_processing.py` — parsing/validation logic, separated from routes so it's reusable by the Day 4-5 pipeline
- Simple upload form added to the homepage for manual testing

### Upload validation rules
- Required columns: `student_id, class_name, subject, score, ai_tool_used, study_hours, record_date`
- `score` must be numeric, 0-100
- `ai_tool_used` accepts true/false, 1/0, yes/no (case-insensitive)
- `study_hours` is optional but must be numeric and non-negative if present
- `record_date` must be a parseable date
- Bad rows are skipped individually with a reason — they don't block the rest of the file
- A file with missing required columns is rejected outright (400 error) before any rows are processed

Tested with: a clean 300-row file (100% stored), a file missing required columns (rejected with clear error), and a mixed file with 5 different error types in 6 rows (1 valid row stored, 5 skipped with specific reasons each).

## Setup
```bash
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py
```
Visit `http://localhost:5000` and `http://localhost:5000/api/health`.

## Data Schema

### `StudentRecord`
| Field | Type | Notes |
|---|---|---|
| id | int | primary key |
| batch_id | int | FK to UploadBatch |
| student_id | string | e.g. "S0001" |
| class_name | string | e.g. "Class 5A" |
| subject | string | Math / Science / English / History |
| score | float | 0-100 |
| ai_tool_used | bool | did the student use an AI study tool |
| study_hours | float | hours studied for this assessment |
| record_date | date | date of the assessment |

### `UploadBatch`
| Field | Type | Notes |
|---|---|---|
| id | int | primary key |
| filename | string | original uploaded filename |
| uploaded_at | datetime | auto-set |
| row_count | int | rows successfully parsed |
| status | string | success / partial / failed |

This lets you trace every record back to the file it came from, and delete/re-upload a whole batch cleanly.

## Core KPIs this schema supports
- Average score by subject/class
- Score improvement % — AI users vs non-users
- Score trend over time
- AI tool adoption rate
- Pass/fail distribution

## Sample dataset
`data/sample_student_data.csv` — 300 synthetic rows across 4 classes and 4 subjects, Jan-Apr 2025. AI tool usage is correlated with a real (but noisy) score boost, so your KPI charts and the Day 9 model will have an actual signal to find — not flat random data.

## Next steps (Day 3)
- Add basic CRUD views for batches in the UI (already have the API: `/api/batches`, `DELETE /api/batches/<id>`)
- Confirm DB persistence is solid, then move into Day 4-5: Pandas cleaning/aggregation pipeline and KPI calculations.
