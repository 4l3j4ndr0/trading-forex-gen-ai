# Tools — Analysis (TradingView TA)

## Fuente de Datos

TradingView Technical Analysis via librería `tradingview-ta`. Screener: `forex`. Exchange: `FX_IDC`.

No requiere API key. Gratis e ilimitado.

---

## Tool 1: `forex_analysis`

**Propósito:** Análisis técnico completo de un par en un timeframe específico.

**Inputs:**
| Param | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `symbol` | str | required | Par forex: "EURUSD", "GBPUSD", etc |
| `timeframe` | str | "1h" | "5m", "15m", "1h", "4h", "1d", "1w" |

**Output:**
```json
{
  "symbol": "EURUSD",
  "timeframe": "1h",
  "timestamp": "2026-07-13T20:00:00Z",
  "price": {
    "open": 1.0892,
    "high": 1.0905,
    "low": 1.0880,
    "close": 1.0898
  },
  "indicators": {
    "rsi_14": 58.3,
    "macd_histogram": 0.00012,
    "macd_signal": 0.00045,
    "adx_14": 28.5,
    "atr_14": 0.00085,
    "ema_8": 1.0895,
    "ema_21": 1.0888,
    "ema_50": 1.0870,
    "ema_200": 1.0820,
    "bb_upper": 1.0920,
    "bb_lower": 1.0860,
    "stoch_k": 65.2,
    "stoch_d": 60.8,
    "cci_20": 45.3,
    "volume": 12500
  },
  "moving_averages": {
    "recommendation": "BUY",
    "buy_count": 8,
    "sell_count": 3,
    "neutral_count": 1
  },
  "oscillators": {
    "recommendation": "NEUTRAL",
    "buy_count": 3,
    "sell_count": 2,
    "neutral_count": 6
  },
  "recommendation": "BUY",
  "strength": "MEDIUM"
}
```

**Lógica interna:**
1. Consulta TradingView TA con screener="forex", exchange="FX_IDC"
2. Extrae indicadores específicos del response
3. Calcula `strength` basado en conteo buy/sell (>8 = STRONG, >5 = MEDIUM, else WEAK)

---

## Tool 2: `forex_multi_timeframe`

**Propósito:** Análisis top-down D1 → H4 → H1 para determinar alineación de tendencia.

**Inputs:**
| Param | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `symbol` | str | required | Par forex |

**Output:**
```json
{
  "symbol": "EURUSD",
  "timestamp": "2026-07-13T20:00:00Z",
  "timeframes": {
    "D1": {
      "recommendation": "BUY",
      "strength": "STRONG",
      "ema_trend": "BULLISH",
      "adx": 32.5,
      "rsi": 62.1
    },
    "H4": {
      "recommendation": "BUY",
      "strength": "MEDIUM",
      "ema_trend": "BULLISH",
      "adx": 27.8,
      "rsi": 55.3
    },
    "H1": {
      "recommendation": "NEUTRAL",
      "strength": "WEAK",
      "ema_trend": "FLAT",
      "adx": 18.2,
      "rsi": 48.7
    }
  },
  "alignment": {
    "direction": "BULLISH",
    "score": 2,
    "max_score": 3,
    "aligned": true,
    "note": "D1+H4 bullish, H1 consolidating — wait for H1 confirmation"
  }
}
```

**Lógica interna:**
1. Ejecuta `forex_analysis` para D1, H4, H1
2. Determina `ema_trend`: EMA8 > EMA21 > EMA50 = BULLISH, inverso = BEARISH, else FLAT
3. Scoring: +1 por cada TF bullish, -1 bearish, 0 neutral
4. `aligned` = true si |score| >= 2

---

## Tool 3: `forex_market_scan`

**Propósito:** Escanea todos los pares configurados y retorna las mejores oportunidades rankeadas.

**Inputs:**
| Param | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `pairs` | list[str] | null | Override de pares. Si null, usa ALLOWED_PAIRS del config |
| `min_adx` | float | 25.0 | Filtro mínimo de ADX (fuerza de tendencia) |

**Output:**
```json
{
  "timestamp": "2026-07-13T20:00:00Z",
  "scanned": 6,
  "opportunities": [
    {
      "symbol": "GBPUSD",
      "recommendation": "SELL",
      "strength": "STRONG",
      "adx": 35.2,
      "rsi": 28.5,
      "alignment_score": -3,
      "rank": 1
    },
    {
      "symbol": "EURUSD",
      "recommendation": "BUY",
      "strength": "MEDIUM",
      "adx": 27.8,
      "rsi": 62.1,
      "alignment_score": 2,
      "rank": 2
    }
  ],
  "no_trade": ["USDJPY", "AUDUSD", "USDCAD", "EURGBP"],
  "reason_no_trade": "ADX < 25 or no alignment"
}
```

**Lógica interna:**
1. Para cada par: ejecuta `forex_multi_timeframe`
2. Filtra: ADX H1 >= min_adx AND |alignment_score| >= 2
3. Rankea por: |alignment_score| * ADX (mayor = mejor)

---

## Tool 4: `get_session_info`

**Propósito:** Información de la sesión de trading activa, volatilidad esperada y pares óptimos.

**Inputs:** Ninguno

**Output:**
```json
{
  "timestamp": "2026-07-13T20:00:00Z",
  "utc_hour": 20,
  "active_sessions": ["new_york"],
  "overlap": false,
  "volatility_level": "MEDIUM",
  "optimal_pairs": ["EURUSD", "GBPUSD", "USDCAD"],
  "avoid_pairs": ["AUDUSD", "USDJPY"],
  "session_ends_in_hours": 1.0,
  "notes": "NY session winding down. Avoid new positions after 20:30 UTC."
}
```

**Lógica interna:**
1. Hora UTC actual → determina sesiones activas
2. Mapeo de pares óptimos por sesión
3. Si falta < 1h para cierre de sesión → nota de precaución
4. Overlap London+NY (12-16 UTC) = volatilidad HIGH
