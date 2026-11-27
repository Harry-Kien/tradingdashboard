# Selected MIT indicators for Harry Gold Research

Pinned upstream sources, licenses and SHA-256 hashes are in `PROVENANCE.json`.
All files under `source/` are unmodified upstream files. `build-entry.js` selects
18 numerical indicators and 27 candlestick detectors. There are no runtime
network calls or production npm dependencies.

To rebuild, from this directory run:

```
npx --yes --package=esbuild@0.28.1 esbuild build-entry.js --bundle --platform=browser --format=iife --global-name=HGR_OSS --target=es2020 --minify --legal-comments=linked --outfile=indicators.js
python finalize.py
```

The Python module `so_cong_khai/chi_bao_nguon_mo.py` loads the artifact into the
chart and indicator worker. Its adapters mask warm-up periods, sanitize undefined
values and reset volume indicators across missing-volume gaps. EMA initialization
can differ across platforms; upstream EMA uses the first input value unless the
indicator explicitly requests an SMA seed. T3 uses six SMA-seeded EMA passes.

The application uses the trailing-window MCFO implementation, not the upstream
full-series CFO regression. Slope is a period price difference divided by the
period, not a regression slope. Bollinger %B and IBS are displayed on a 0–100
scale. Special K requires 725 bars. Volume means MT5 tick volume where supplied.

Candlestick detections are marked at the final bar of their pattern. By default
the last bar is excluded until a following bar exists; disabling confirmation
allows provisional patterns to change with live prices. Only the latest 500
bars are scanned by default (configurable). These are pattern classifications,
not tested profitability claims or automatic order instructions.

Both MIT notices are included in the embedded JavaScript as well as separate
license files. Keep these notices when distributing this bundle.
