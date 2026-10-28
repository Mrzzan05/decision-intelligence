# Decision Intelligence Platform

![CI](https://github.com/Mrzzan05/decision-intelligence/actions/workflows/ci.yml/badge.svg)

A Multi-Criteria Decision Analysis (MCDA) web application built with **Django 6.1** and **PostgreSQL**. Users assign priority weights (`0..10`) or select persona presets to rank products, inspect RTINGS-style consensus summaries with top-rated reviewer highlights, compare models side-by-side (Apple/Baymard style) with interactive Chart.js Radar & Grouped Bar charts, and track pre-purchase expectations against post-purchase reality in a personal Decision Journal.

---

## 1. Prerequisites & PostgreSQL Database Setup

Dependencies are managed via **`pyproject.toml` and `uv.lock`** (single source of truth). Ensure **PostgreSQL 15+** and **`uv`** are installed.

Before running migrations or the test suite, create a PostgreSQL role with **`CREATEDB`** permission (required by Django's test runner to create `test_decision_intelligence`):

```sql
-- Run inside psql as superuser (postgres):
CREATE USER di_user WITH PASSWORD 'di_local_pass' CREATEDB;
CREATE DATABASE decision_intelligence OWNER di_user;
GRANT ALL PRIVILEGES ON DATABASE decision_intelligence TO di_user;
```

---

## 2. Quick Start & Installation (`uv` + PostgreSQL)

```bash
# 1. Copy environment template and set DATABASE_URL
cp .env.example .env

# 2. Install locked dependencies via uv
uv sync

# 3. Apply PostgreSQL migrations
uv run python manage.py migrate

# 4. Seed demo catalog (20 Laptops & Smartphones across 11 brands, 100 synthetic demo reviews)
# Note: seed_data only runs when DEBUG=True (or with --force) and is strictly for local demo use.
uv run python manage.py seed_data

# 5. Run the 61 automated tests (with optional coverage)
uv run python manage.py test

# 6. Launch development server
uv run python manage.py runserver
```

> **Security Warning:** `seed_data` creates a local demo account (`admin@example.com` / `admin1234`) when `DEBUG=True`. It refuses to run when `DEBUG=False` unless `--force` is explicitly supplied. Never use demo credentials in production.

---

## 3. Complete Entity-Relationship Diagram (ERD with Fields)

```mermaid
erDiagram
    User {
        bigint id PK
        varchar email UK
        varchar username UK
        varchar first_name
        varchar last_name
        boolean is_staff
        timestamptz created_at
        timestamptz updated_at
    }
    UserPreference {
        bigint id PK
        bigint user_id FK,UK
        bigint preferred_category_id FK
        numeric default_budget
        varchar theme_mode
        boolean dark_mode
        timestamptz created_at
        timestamptz updated_at
    }
    Category {
        bigint id PK
        varchar name UK
        varchar slug UK
        jsonb spec_schema
        jsonb presets
        timestamptz created_at
        timestamptz updated_at
    }
    Criteria {
        bigint id PK
        bigint category_id FK
        bigint parent_id FK
        varchar name
        timestamptz created_at
        timestamptz updated_at
    }
    Product {
        bigint id PK
        bigint category_id FK
        varchar brand
        varchar name
        varchar slug UK
        numeric price
        text description
        varchar image_url
        jsonb specs
        timestamptz created_at
        timestamptz updated_at
    }
    SavedProduct {
        bigint id PK
        bigint user_id FK
        bigint product_id FK
        timestamptz created_at
        timestamptz updated_at
    }
    Review {
        bigint id PK
        bigint user_id FK
        bigint product_id FK
        smallint overall_rating
        text pros
        text cons
        text comment
        timestamptz created_at
        timestamptz updated_at
    }
    ReviewScore {
        bigint id PK
        bigint review_id FK
        bigint criteria_id FK
        smallint score
        timestamptz created_at
        timestamptz updated_at
    }
    DecisionEntry {
        bigint id PK
        bigint user_id FK
        bigint category_id FK
        bigint chosen_product_id FK
        jsonb weights_snapshot
        text rationale
        text expected_outcome
        smallint expected_rating
        text actual_experience
        smallint satisfaction_rating
        timestamptz created_at
        timestamptz updated_at
    }

    User ||--o| UserPreference : "has"
    User ||--o{ Review : "writes"
    User ||--o{ DecisionEntry : "logs"
    User ||--o{ SavedProduct : "bookmarks"
    Category ||--o{ Criteria : "defines"
    Category ||--o{ Product : "contains"
    Criteria ||--o{ Criteria : "parent/subcriteria"
    Product ||--o{ Review : "receives"
    Product ||--o{ SavedProduct : "shortlisted_in"
    Product ||--o{ DecisionEntry : "chosen_in"
    Review ||--o{ ReviewScore : "aggregates"
    Criteria ||--o{ ReviewScore : "scored_by"
```

---

## 4. URL Routing & JSON API Table

| URL Pattern | View / Handler | Name | HTTP Verbs | Auth | Description |
|---|---|---|---|---|---|
| `/` | `core.views.home_view` | `home` | `GET` | No | Landing page with category overview |
| `/accounts/login/` | `UserLoginView` | `accounts:login` | `GET, POST` | No | Email authentication |
| `/accounts/logout/` | `UserLogoutView` | `accounts:logout` | `POST` | Yes | Session termination (GET returns 405) |
| `/accounts/signup/` | `signup_view` | `accounts:signup` | `GET, POST` | No | Registration & `UserPreference` init |
| `/accounts/profile/` | `profile_view` | `accounts:profile` | `GET, POST` | Yes | Profile, preferred category, budget & theme |
| `/accounts/theme/` | `update_theme_preference_view` | `accounts:update_theme` | `POST` | No | Persists `system`/`light`/`dark` theme mode |
| `/catalog/` | `product_search_view` | `catalog:product_search` | `GET` | No | Search, category/price/score filters, sorting & pagination |
| `/catalog/compare/` | `product_compare_view` | `catalog:product_compare` | `GET` | No | 4-slot comparison matrix + Radar/Bar charts |
| `/catalog/product/<slug>/` | `product_detail_view` | `catalog:product_detail` | `GET` | No | Product profile, criteria bars & reviews |
| `/catalog/product/<slug>/save/` | `toggle_saved_product_view` | `catalog:toggle_saved_product` | `POST` | Yes | Bookmark toggle (`url_has_allowed_host_and_scheme` guarded) |
| `/reviews/<slug>/write/` | `create_or_update_review_view` | `reviews:write_review` | `GET, POST` | Yes | Structured per-criteria review + pros/cons |
| `/reviews/<slug>/delete/` | `delete_review_view` | `reviews:delete_review` | `POST` | Yes | Owner-only review deletion |
| `/recommendations/<slug>/` | `category_recommendations_view` | `recommendations:category_recommendations` | `GET` | No | Live MCDA ranking matrix with persona presets |
| `/recommendations/api/<slug>/` | `category_recommendations_api_view` | `recommendations:category_recommendations_api` | `GET` | No | RESTful JSON API for weighted rankings |
| `/dashboard/` | `dashboard_view` | `dashboard` | `GET` | Yes | Personal KPI cards, shortlist, history & analytics |
| `/journal/` | `journal_list_view` | `journal_list` | `GET` | Yes | Personal Decision Journal (Expectation vs Reality) |
| `/journal/record/<slug>/` | `record_decision_view` | `record_decision` | `GET, POST` | Yes | Record decision with `weights_snapshot` |
| `/journal/update/<id>/` | `update_decision_experience_view` | `update_decision` | `GET, POST` | Yes | Log post-purchase satisfaction & experience |

---

## 5. Requirements Traceability Matrix

| Requirement | Implemented Feature | Key Files | Automated Tests |
|---|---|---|---|
| Authentication & Preferences | Email login, signup, POST logout, profile, preferred category, budget, 3-state dark mode | `accounts/models.py`, `accounts/views.py` | `accounts/tests.py`, `core/tests.py` |
| Product & Schema Management | Relational `Product` + JSONB `specs` validated against `Category.spec_schema` | `catalog/models.py`, `catalog/admin.py` | `catalog/tests.py`, `core/tests.py` |
| Structured Reviews (CRUD) | 1..10 per-criteria sliders, written `pros`/`cons`, owner edit/delete | `reviews/models.py`, `reviews/views.py` | `reviews/tests.py`, `reviews/test_ui.py` |
| Search, Filter, Sort & Pagination | Keyword, category, finite price range, min score, 4 sort modes, paginator | `catalog/managers.py`, `catalog/views.py` | `catalog/tests.py`, `core/tests.py` |
| Side-by-Side Comparison | Dynamic category tabs, 4-slot brand/model modal, identical-row hiding, Radar/Bar charts | `recommendations/services.py`, `templates/catalog/product_compare.html` | `catalog/tests.py`, `catalog/test_ui.py` |
| Personalized Match Score | Weighted MCDA in constant 3 SQL queries, dealbreaker penalty, insufficient-data handling | `recommendations/services.py` | `recommendations/tests.py`, `recommendations/test_ui.py` |
| Smart Summary (Consensus + Quote) | Relative mean + `StdDev` mixed opinions + top-rated reviewer `pros`/`cons` quote via Subquery | `recommendations/services.py`, `templates/partials/smart_summary.html` | `recommendations/tests.py`, `core/tests.py` |
| Decision Journal | Captures `weights_snapshot`, `expected_rating`, `satisfaction_rating` & delta | `journal/models.py`, `journal/views.py` | `journal/tests.py` |
| Personal & Analytical Dashboard | KPI cards, favorite category, saved shortlist, decision history & platform analytics | `journal/views.py`, `templates/journal/dashboard.html` | `journal/tests.py`, `core/tests.py` |
| JSON API Structure | `GET /recommendations/api/<category_slug>/` accepting `?weight_<id>=...` | `recommendations/views.py`, `recommendations/urls.py` | `core/tests.py` |

---

## 6. Known Limitations & Architectural Trade-offs

1. **Live Matrix Recalculation via HTML Fetch & DOM Swap:** Adjusting priority sliders in `/recommendations/<slug>/` fetches the updated server-rendered HTML (~110 KB for 10 products) and swaps `#ranked_results_container` via `DOMParser` rather than duplicating template rendering logic in client-side JavaScript. For large catalogs (100+ items per category), client-side rendering backed by `/recommendations/api/<slug>/` should be used.
2. **Rule-Based Consensus & Top-Rated Reviewer Quote:** `generate_smart_summary` is deterministic and executes within the 3-query budget (`assertNumQueries(3)`). Written `pros`/`cons` highlights are selected from the highest-rated most recent review via a correlated SQL `Subquery` rather than LLM/NLP summarization.

---

## 7. Automated Test Suite & Coverage Report (61 Tests, 94% Coverage)

Run via `uv run coverage run manage.py test && uv run coverage report`:

```text
Name                                    Stmts   Miss  Cover
-----------------------------------------------------------
accounts/admin.py                          14      0   100%
accounts/forms.py                          20      0   100%
accounts/models.py                         31      2    94%
accounts/views.py                          56     13    77%
catalog/admin.py                           24      0   100%
catalog/managers.py                        34      2    94%
catalog/models.py                          92     11    88%
catalog/views.py                           81      3    96%
core/management/commands/seed_data.py      70      3    96%
core/models.py                              6      0   100%
core/views.py                              10      0   100%
journal/forms.py                           12      1    92%
journal/models.py                          34      1    97%
journal/views.py                           50      4    92%
recommendations/services.py               254      8    97%
recommendations/views.py                   33      5    85%
reviews/forms.py                           12      0   100%
reviews/models.py                          37      2    95%
reviews/views.py                           48      1    98%
-----------------------------------------------------------
TOTAL                                     986     56    94%
```

---

## 8. Docker

```bash
docker build -t decision-intelligence .
docker run --rm -p 8000:8000 \
  -e SECRET_KEY="change-me" \
  -e DATABASE_URL="postgres://USER:PASSWORD@HOST:5432/decision_intelligence" \
  -e ALLOWED_HOSTS="localhost,127.0.0.1" \
  -e CSRF_TRUSTED_ORIGINS="http://localhost:8000" \
  -e SECURE_SSL_REDIRECT="False" \
  decision-intelligence
```

The image runs as a non-root user and serves static files through WhiteNoise. Run
`python manage.py migrate` against the database once before first use
(`docker run ... decision-intelligence python manage.py migrate`).
