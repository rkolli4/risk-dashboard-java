# PRISM Prototype

A Windows-friendly market risk pipeline: Python fetches a Nifty snapshot, SQLite stores it, C evaluates exposure controls, and Java serves a browser UI plus JSON API.

## Run

From PowerShell:

<img width="1328" height="943" alt="image" src="https://github.com/user-attachments/assets/9ce2a438-c458-4db1-bece-a4474b1c265c" />



```powershell
./run_pipeline.ps1
```

The UI is available at `http://localhost:8080`. Set `PORT` to choose another port. The runner uses `gcc` and `javac` from `PATH`; Python uses only its standard library. Yahoo Finance is queried directly, with a labeled demo fallback when the network is unavailable.

Supported overrides: `TOTAL_DEPOSIT`, `MIN_LIQUID_NETWORTH`, `INITIAL_MARGIN`, `EXTREME_LOSS_MARGIN`, `TM_LIMIT`, `POSITION_QTY`, `POSITION_LIMIT`, `ORACLE_DSN`, `ORACLE_USER`, `ORACLE_PASSWORD`.
