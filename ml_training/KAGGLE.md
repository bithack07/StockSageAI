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
- Default symbol list: **Nifty 50** in `train_all.py`

## Kaggle notebook steps

1. **Create notebook** → Add-ons → Internet **On** → Accelerator **GPU** (optional, speeds LSTM only).

2. **Clone or upload** this repo:
   ```python
   !git clone https://github.com/YOUR_ORG/StockSageAI.git
   %cd StockSageAI/StockSageAI/backend
   ```

3. **Install deps:**
   ```python
   !pip install -q xgboost prophet ta yfinance scikit-learn joblib torch pandas numpy
   ```

4. **Train:**
   ```python
   !python ../ml_training/kaggle_train.py --output /kaggle/working/models --lstm-epochs 25
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
python ../ml_training/train_all.py
```

## Feature list (XGBoost)

Base: RSI, MACD, Bollinger, ATR, EMA 20/50/200, sentiment, P/E, ROCE, D/E.

Graham: `graham_score_norm`, `graham_mos_norm`, `graham_pe_pb_norm`, `graham_price_ratio`.

Playbook technical: Weinstein stage, ADX proxy, Murphy alignment, Wyckoff, golden/death cross, EMA stack, price vs 200 EMA, RSI action, checklist pass.

Playbook fundamental: Lynch PEG, Greenblatt combined, FA score, moat score, fundamental bias.

## Inference without retrain

Old `xgb_model.joblib` (12–16 features) still runs; playbook is blended via **`playbook_direction_prior`** (~35–45% weight). For playbook inside **learned** weights, you must deploy a newly trained model.

## Tips

- First run: `--skip-lstm` to validate XGBoost in ~10–15 min on CPU.
- LSTM on GPU: 25 epochs × 50 symbols ≈ 20–40 min.
- Save notebook output as **Kaggle Dataset** for versioned model artifacts.
- Do not commit large `.joblib` / `.pt` files to git; use releases or object storage.
