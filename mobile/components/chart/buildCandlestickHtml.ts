export interface CandlePoint {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
}

/** Match desktop app — v5+ breaks addCandlestickSeries used below */
export const LIGHTWEIGHT_CHARTS_VERSION = '4.2.3';
const CDN_SRC = `https://cdn.jsdelivr.net/npm/lightweight-charts@${LIGHTWEIGHT_CHARTS_VERSION}/dist/lightweight-charts.standalone.production.js`;

export function normalizeCandles(rows: Record<string, unknown>[]): CandlePoint[] {
  return rows
    .map((d) => {
      const raw = d.date ?? d.datetime;
      const time = String(raw ?? '').slice(0, 10);
      const open = Number(d.open);
      const high = Number(d.high);
      const low = Number(d.low);
      const close = Number(d.close);
      if (!time || Number.isNaN(open)) return null;
      return { time, open, high, low, close };
    })
    .filter((c): c is CandlePoint => c !== null);
}

export type ChartHtmlOptions = {
  /** Full JS bundle — only reliable option inside React Native WebView */
  inlineScript?: string;
  /** CDN or file URL fallback (web / last resort) */
  scriptSrc?: string;
};

function escapeInlineScript(js: string): string {
  return js.replace(/<\/script/gi, '<\\/script');
}

function chartScriptTag(options?: ChartHtmlOptions): string {
  if (options?.inlineScript) {
    return `<script>${escapeInlineScript(options.inlineScript)}</script>`;
  }
  const src = options?.scriptSrc ?? CDN_SRC;
  return `<script src="${src}"></script>`;
}

export function buildCandlestickHtml(
  candles: CandlePoint[],
  height = 220,
  options?: ChartHtmlOptions,
): string {
  const candleData = JSON.stringify(candles);
  const libTag = chartScriptTag(options);
  const deferredBoot = !options?.inlineScript;

  return `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
${libTag}
<style>
  html, body { margin:0; padding:0; background:#0f172a; overflow:hidden; }
  #chart { width:100%; height:${height}px; }
  #err { color:#94a3b8; font:13px -apple-system,sans-serif; padding:12px; display:none; }
</style>
</head>
<body>
<div id="err"></div>
<div id="chart"></div>
<script>
(function () {
  function showErr(msg) {
    var el = document.getElementById('err');
    el.style.display = 'block';
    el.textContent = msg;
    if (window.ReactNativeWebView) {
      window.ReactNativeWebView.postMessage(JSON.stringify({ type: 'chart_error', message: msg }));
    }
  }
  function boot() {
  try {
    if (typeof LightweightCharts === 'undefined') {
      showErr('Chart library failed to load');
      return;
    }
    var chart = LightweightCharts.createChart(document.getElementById('chart'), {
      width: window.innerWidth,
      height: ${height},
      layout: {
        background: { color: '#0f172a' },
        textColor: '#94a3b8',
        padding: { top: 8, bottom: 20, left: 4, right: 8 },
      },
      grid: { vertLines: { color: '#1e293b' }, horzLines: { color: '#1e293b' } },
      rightPriceScale: { borderColor: '#1e293b' },
      timeScale: {
        borderColor: '#1e293b',
        visible: true,
        timeVisible: true,
        secondsVisible: false,
      },
    });
    var series = chart.addCandlestickSeries({
      upColor: '#22c55e', downColor: '#ef4444',
      borderUpColor: '#22c55e', borderDownColor: '#ef4444',
      wickUpColor: '#22c55e', wickDownColor: '#ef4444',
    });
    var data = ${candleData};
    if (data && data.length) {
      series.setData(data);
      chart.timeScale().fitContent();
    } else {
      showErr('No price data');
    }
    window.addEventListener('resize', function () {
      chart.applyOptions({ width: window.innerWidth });
    });
    if (window.ReactNativeWebView) {
      window.ReactNativeWebView.postMessage(JSON.stringify({ type: 'chart_ready' }));
    }
  } catch (e) {
    showErr(e && e.message ? e.message : 'Chart failed');
  }
  }
  ${deferredBoot ? `if (typeof LightweightCharts !== 'undefined') { boot(); } else { window.addEventListener('load', boot); }` : 'boot();'}
})();
</script>
</body>
</html>`;
}
