# Training StockSage ML on Kaggle (free)

StockSage direction (XGBoost), 7-day LSTM, and Prophet models can be trained on [Kaggle](https://www.kaggle.com) at no cost. After our playbook integration, **retraining is required** so models learn Graham + Murphy + Weinstein + Lynch + Greenblatt features (31 inputs for XGBoost, 10 for LSTM).

## What to train

| Model | Role | Playbook in weights? |
|-------|------|----------------------|
| **XGBoost** (`xgb_model.joblib`) | 7-day direction (-1 / 0 / +1) | Yes — 31 features |
| **LSTM** (`lstm_weights.pt`) | 7-day up/down probability | Yes — 10 channels |
| **Prophet** (`prophet_models/*.pkl`) | 30-day price band | No (price only) |

## Datasets on Kaggle

You do **not** need a dataset if **Internet is ON** — `train_all.py` / `kaggle_train.py` pull OHLCV via **yfinance** (same as production).

Optional CSV datasets (search on Kaggle → Datasets):

1. **NSE / Nifty OHLCV** — e.g. datasets tagged `NSE`, `Nifty 50`, `Indian stock market`
2. **Columns required:** `symbol`, `date`, `open`, `high`, `low`, `close`, `volume`
3. **Symbols:** use `.NS` suffix (`RELIANCE.NS`, `TCS.NS`, …) to match StockSage

Fundamental playbook features (Lynch PEG, Greenblatt, FA score) use **latest** yfinance fundamentals per symbol during training (replicated on each row). Technical playbook features (Weinstein, Wyckoff, ADX proxy) are computed **per day** from OHLCV.

### Minimum data

- **~5 years daily** bars per symbol
- **≥ 220 trading days** after indicators (script skips thin symbols)
- Default universe: **all NSE equities** (`--universe nse_all`, ~1500–2000 symbols from NSE `EQUITY_L.csv`)

### Symbol universe (CLI)

| `--universe` | Symbols |
|--------------|---------|
| `nse_all` (default) | All NSE listed equities (EQUITY_L.csv; falls back to Nifty 500 → 50) |
| `nifty500` | Nifty 500 (Wikipedia) |
| `nifty50` | Nifty 50 only |

```python
# All NSE stocks — XGBoost + LSTM (Prophet capped at 200 names by default)
!python ../ml_training/kaggle_train.py --output /kaggle/working/models --universe nse_all

# Nifty 500 only
!python ../ml_training/kaggle_train.py --universe nifty500 --skip-lstm

# Custom list file (one symbol per line or CSV with Symbol column)
!python ../ml_training/kaggle_train.py --symbols-file /kaggle/input/my_tickers/symbols.txt

# Kaggle time limit: test on 100 names first
!python ../ml_training/kaggle_train.py --universe nse_all --max-symbols 100 --skip-lstm
```

**Prophet:** one `.pkl` per symbol — training ~2000 Prophet models on Kaggle is not practical. Default `--prophet-max 200` (Nifty 50 first, then others). Use `--prophet-max 0` to skip Prophet entirely.

**Runtime:** `nse_all` with Graham/yfinance per symbol can take **many hours** on Kaggle. Use GPU for LSTM; consider `--max-symbols` for a first run.

## Kaggle notebook steps

1. **Create notebook** → Add-ons → Internet **On** → Accelerator **GPU** (optional, speeds LSTM only).

2. **Get the code** (pick one):

   **Option A — public repo (recommended on Kaggle)**  
   GitHub → repo **Settings** → **Change visibility** → **Public**, then:
   ```python
   import os
   os.environ["GIT_TERMINAL_PROMPT"] = "0"  # no interactive username/password
   !git clone --depth 1 https://github.com/bithack07/StockSageAI.git
   %cd StockSageAI/backend
   ```

   **Option B — ZIP (no git login)**  
   Works only if the repo is **public**:
   ```python
   !wget -q https://github.com/bithack07/StockSageAI/archive/refs/heads/main.zip -O repo.zip
   !unzip -q repo.zip && mv StockSageAI-main StockSageAI
   %cd StockSageAI/backend
   ```

   **Option C — private repo**  
   Do not type your GitHub password in the notebook (GitHub rejects it). Use a [Personal Access Token](https://github.com/settings/tokens) with `repo` scope, store it in **Kaggle → Add-ons → Secrets** as `GITHUB_TOKEN`, then:
   ```python
   import os
   token = os.environ["GITHUB_TOKEN"]  # Add secret in notebook settings first
   !git clone --depth 1 https://{token}@github.com/bithack07/StockSageAI.git
   %cd StockSageAI/backend
   ```

   **Option D — no GitHub**  
   Zip `backend/` + `ml_training/` from your machine → **Upload** as a Kaggle dataset → `%cd /kaggle/input/YOUR_DATASET/backend`

   Repo root on GitHub is `backend/`, `ml_training/` (not `StockSageAI/StockSageAI/`).

3. **Install deps** (no Postgres required — training uses yfinance only):
   ```python
   !pip install -q xgboost prophet ta yfinance scikit-learn joblib torch pandas numpy requests lxml html5lib
   ```
   If you pulled an **older** repo revision that errors on `app.db` / `psycopg2`, either `git pull` the latest or add: `pydantic-settings psycopg2-binary sqlalchemy` (not needed for training after the lazy-DB fix).

4. **Train:**
   ```python
   !python ../ml_training/kaggle_train.py --output /kaggle/working/models --universe nse_all --lstm-epochs 25
   ```

5. **Download artifacts** from `/kaggle/working/models`:
   - `xgb_model.joblib`
   - `lstm_weights.pt`
   - `prophet_models/*.pkl`

6. **Copy into your app:**
   ```
   StockSageAI/backend/app/models/
   StockSageAI/backend/app/models/prophet_models/
   ```

7. **Restart** the backend so `ml_inference.py` loads the new files.

## Local training (same features)

```bash
cd StockSageAI/backend
source venv/bin/activate
pip install xgboost prophet ta yfinance scikit-learn joblib torch
python ../ml_training/train_all.py --universe nse_all
```

## Feature list (XGBoost)

Base: RSI, MACD, Bollinger, ATR, EMA 20/50/200, sentiment, P/E, ROCE, D/E.

Graham: `graham_score_norm`, `graham_mos_norm`, `graham_pe_pb_norm`, `graham_price_ratio`.

Playbook technical: Weinstein stage, ADX proxy, Murphy alignment, Wyckoff, golden/death cross, EMA stack, price vs 200 EMA, RSI action, checklist pass.

Playbook fundamental: Lynch PEG, Greenblatt combined, FA score, moat score, fundamental bias.

## Inference without retrain

Old `xgb_model.joblib` (12–16 features) still runs; playbook is blended via **`playbook_direction_prior`** (~35–45% weight). For playbook inside **learned** weights, you must deploy a newly trained model.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|--------|-----|
| `Username for 'https://github.com':` | Repo is **private** or missing; Git wants credentials | Make repo **public** (Option A/B) or use a PAT secret (Option C) |
| Hangs then you press `^C` | Waiting for password input in a non-interactive cell | Set `GIT_TERMINAL_PROMPT=0` and use Option A/B/C above |
| `cd: StockSageAI/StockSageAI/backend: No such file` | Wrong path in old docs | Use `%cd StockSageAI/backend` after clone |
| `404` on clone | Repo name/owner wrong or private without token | Confirm URL: `https://github.com/bithack07/StockSageAI` |
| Traceback in `intelligent_investor` / `value_investing` | Old code imports Postgres at startup | `git pull` latest, or lazy-DB fix; training does not need a database |
| `ModuleNotFoundError: psycopg2` | Same as above | Re-clone latest repo; no extra pip packages needed for training |

## Tips

- First run: `--skip-lstm` to validate XGBoost in ~10–15 min on CPU.
- LSTM on GPU: 25 epochs × 50 symbols ≈ 20–40 min.
- Save notebook output as **Kaggle Dataset** for versioned model artifacts.
- Do not commit large `.joblib` / `.pt` files to git; use releases or object storage.
