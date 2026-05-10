"""
options_engine.py
=================
Options chain ka full analysis karta hai:
  - PCR (OI & Volume)
  - Buyer vs Seller dominance per strike
  - Strong CE / PE strike identify karna
  - Max Pain calculate karna
  - High activity strikes highlight karna
  - Alerts generate karna

Usage:
    from options_engine import OptionsEngine
    result = OptionsEngine.analyze(chain_data, expiry="05-Jun-2025")
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class OptionsEngine:

    # ── Main entry point ──────────────────────────────────────

    @staticmethod
    def analyze(chain_data: dict, expiry: Optional[str] = None) -> dict:
        """
        Full options chain analysis karo.

        Args:
            chain_data: OptionsFetcher.get_chain() ka output
            expiry:     Specific expiry date (None = pehli/nearest expiry)

        Returns:
            Complete analysis dict dashboard ke liye ready
        """
        spot     = chain_data.get("spot", 0)
        expiries = chain_data.get("expiries", [])
        all_data = chain_data.get("data", {})

        # Expiry select karo
        if not expiry or expiry not in all_data:
            expiry = expiries[0] if expiries else (
                list(all_data.keys())[0] if all_data else None
            )

        if not expiry:
            return {"error": "No expiry data available"}

        strike_map = all_data.get(expiry, {})
        if not strike_map:
            return {"error": f"No data for expiry {expiry}"}

        # ATM strike dhundo
        atm_strike = OptionsEngine._find_atm(strike_map, spot)

        # Har strike ka enriched row banao
        rows = OptionsEngine._build_rows(strike_map, spot, atm_strike)

        # Summary metrics
        metrics = OptionsEngine._compute_metrics(rows, spot)

        # Max Pain
        max_pain = OptionsEngine._compute_max_pain(strike_map)

        # Alerts
        alerts = OptionsEngine._generate_alerts(
            rows, metrics, spot, max_pain
        )

        return {
            "spot":       spot,
            "expiry":     expiry,
            "expiries":   expiries,
            "atm_strike": atm_strike,
            "max_pain":   max_pain,
            "metrics":    metrics,
            "rows":       rows,
            "alerts":     alerts,
            "source":     chain_data.get("source", "unknown"),
            "timestamp":  chain_data.get("timestamp", ""),
        }

    # ── ATM finder ────────────────────────────────────────────

    @staticmethod
    def _find_atm(strike_map: dict, spot: float) -> int:
        """Spot ke sabse paas wala strike = ATM."""
        strikes = [int(k) for k in strike_map.keys()]
        if not strikes:
            return 0
        return min(strikes, key=lambda s: abs(s - spot))

    # ── Per-strike row builder ────────────────────────────────

    @staticmethod
    def _build_rows(
        strike_map: dict,
        spot: float,
        atm_strike: int,
    ) -> list:
        """Har strike ke liye enriched dict banao."""
        rows = []
        all_combined_oi = [
            (v.get("ce", {}).get("oi", 0) or 0) +
            (v.get("pe", {}).get("oi", 0) or 0)
            for v in strike_map.values()
        ]
        max_combined = max(all_combined_oi) if all_combined_oi else 1
        hot_threshold = max_combined * 0.35  # Top 35% activity = hot

        max_ce_oi = max(
            (v.get("ce", {}).get("oi", 0) or 0)
            for v in strike_map.values()
        ) or 1
        max_pe_oi = max(
            (v.get("pe", {}).get("oi", 0) or 0)
            for v in strike_map.values()
        ) or 1

        for strike_key, vals in sorted(strike_map.items(), key=lambda x: int(x[0])):
            s   = int(strike_key)
            ce  = vals.get("ce", {})
            pe  = vals.get("pe", {})

            ce_oi    = int(ce.get("oi",    0) or 0)
            ce_chg   = int(ce.get("chgOI", 0) or 0)
            ce_vol   = int(ce.get("vol",   0) or 0)
            ce_ltp   = float(ce.get("ltp", 0) or 0)
            ce_iv    = float(ce.get("iv",  0) or 0)

            pe_oi    = int(pe.get("oi",    0) or 0)
            pe_chg   = int(pe.get("chgOI", 0) or 0)
            pe_vol   = int(pe.get("vol",   0) or 0)
            pe_ltp   = float(pe.get("ltp", 0) or 0)
            pe_iv    = float(pe.get("iv",  0) or 0)

            combined_oi = ce_oi + pe_oi

            # ── Dominance score (0–100) ──────────────────────
            # >55 = sellers dominant, <45 = buyers dominant
            ce_dom = OptionsEngine._dominance_score(
                ce_oi, ce_chg, ce_vol
            )
            pe_dom = OptionsEngine._dominance_score(
                pe_oi, pe_chg, pe_vol
            )

            # ── OI strength as % of max ──────────────────────
            ce_strength = round(ce_oi / max_ce_oi * 100, 1) if max_ce_oi else 0
            pe_strength = round(pe_oi / max_pe_oi * 100, 1) if max_pe_oi else 0

            rows.append({
                "strike":        s,
                "moneyness":     OptionsEngine._moneyness(s, spot),
                "is_atm":        s == atm_strike,
                "is_hot":        combined_oi >= hot_threshold,
                "is_strong_ce":  ce_oi == max_ce_oi,
                "is_strong_pe":  pe_oi == max_pe_oi,

                "ce": {
                    "oi":       ce_oi,
                    "chgOI":    ce_chg,
                    "vol":      ce_vol,
                    "ltp":      ce_ltp,
                    "iv":       ce_iv,
                    "dom":      ce_dom,
                    "dom_label": OptionsEngine._dom_label(ce_dom),
                    "strength": ce_strength,
                },
                "pe": {
                    "oi":       pe_oi,
                    "chgOI":    pe_chg,
                    "vol":      pe_vol,
                    "ltp":      pe_ltp,
                    "iv":       pe_iv,
                    "dom":      pe_dom,
                    "dom_label": OptionsEngine._dom_label(pe_dom),
                    "strength": pe_strength,
                },
            })

        return rows

    # ── Dominance calculation ─────────────────────────────────

    @staticmethod
    def _dominance_score(oi: int, chg_oi: int, vol: int) -> float:
        """
        0–100 score:
          > 55 → Sellers dominant (OI add ho raha, writers active)
          < 45 → Buyers dominant (OI ghat raha, long covering)
          45–55 → Neutral
        """
        if oi <= 0:
            return 50.0

        # OI change component: positive chg = sellers writing = seller dominant
        chg_ratio = chg_oi / oi  # -1 to +1 range
        oi_score  = 50 + min(30, max(-30, chg_ratio * 150))

        # Volume component: high vol relative to OI = active buyers
        vol_ratio  = vol / oi if oi > 0 else 0
        vol_signal = 50 - min(20, vol_ratio * 40)  # high vol = buyers

        # Weighted mix
        score = oi_score * 0.65 + vol_signal * 0.35
        return round(max(0, min(100, score)), 1)

    @staticmethod
    def _dom_label(score: float) -> str:
        if score >= 65:
            return "Strong Sellers"
        elif score >= 55:
            return "Sellers"
        elif score <= 35:
            return "Strong Buyers"
        elif score <= 45:
            return "Buyers"
        else:
            return "Neutral"

    @staticmethod
    def _moneyness(strike: int, spot: float) -> str:
        diff_pct = (strike - spot) / spot * 100
        if abs(diff_pct) <= 0.3:
            return "ATM"
        elif diff_pct > 3:
            return "Deep OTM CE"
        elif diff_pct > 0:
            return "OTM CE"
        elif diff_pct < -3:
            return "Deep OTM PE"
        else:
            return "OTM PE"

    # ── Summary metrics ───────────────────────────────────────

    @staticmethod
    def _compute_metrics(rows: list, spot: float) -> dict:
        """PCR, totals, strong strikes, bias."""
        total_ce_oi  = sum(r["ce"]["oi"]  for r in rows)
        total_pe_oi  = sum(r["pe"]["oi"]  for r in rows)
        total_ce_vol = sum(r["ce"]["vol"] for r in rows)
        total_pe_vol = sum(r["pe"]["vol"] for r in rows)

        pcr_oi  = round(total_pe_oi  / total_ce_oi,  3) if total_ce_oi  else 0
        pcr_vol = round(total_pe_vol / total_ce_vol, 3) if total_ce_vol else 0

        # Strong strikes (max OI)
        strong_ce_row = max(rows, key=lambda r: r["ce"]["oi"], default=None)
        strong_pe_row = max(rows, key=lambda r: r["pe"]["oi"], default=None)

        strong_ce = strong_ce_row["strike"] if strong_ce_row else 0
        strong_pe = strong_pe_row["strike"] if strong_pe_row else 0

        # Hot strikes (top activity)
        hot_strikes = sorted(
            [r["strike"] for r in rows if r["is_hot"]]
        )

        # Market bias from PCR
        bias, bias_desc = OptionsEngine._pcr_bias(pcr_oi)

        # Net OI change (bullish/bearish pressure)
        net_ce_chg = sum(r["ce"]["chgOI"] for r in rows)
        net_pe_chg = sum(r["pe"]["chgOI"] for r in rows)

        return {
            "total_ce_oi":  total_ce_oi,
            "total_pe_oi":  total_pe_oi,
            "total_ce_vol": total_ce_vol,
            "total_pe_vol": total_pe_vol,
            "pcr_oi":       pcr_oi,
            "pcr_vol":      pcr_vol,
            "strong_ce":    strong_ce,
            "strong_pe":    strong_pe,
            "hot_strikes":  hot_strikes,
            "bias":         bias,
            "bias_desc":    bias_desc,
            "net_ce_chg":   net_ce_chg,
            "net_pe_chg":   net_pe_chg,
        }

    @staticmethod
    def _pcr_bias(pcr: float):
        """PCR value se market bias determine karo."""
        if pcr < 0.5:
            return "Very Bearish", "Extreme call writing — heavy resistance"
        elif pcr < 0.7:
            return "Bearish", "Call writers dominant — bearish pressure"
        elif pcr < 0.9:
            return "Mildly Bearish", "Slight call dominance — cautious"
        elif pcr < 1.1:
            return "Neutral", "Balanced OI — range-bound likely"
        elif pcr < 1.3:
            return "Mildly Bullish", "Slight put writing — mild support"
        elif pcr < 1.5:
            return "Bullish", "Put writers dominant — bullish bias"
        else:
            return "Very Bullish", "Extreme put writing — strong support"

    # ── Max Pain ──────────────────────────────────────────────

    @staticmethod
    def _compute_max_pain(strike_map: dict) -> int:
        """
        Max Pain = wo strike jahan option buyers ka total loss maximum ho.
        Market is strike ke aas paas expire karta hai typically.
        """
        strikes = sorted([int(k) for k in strike_map.keys()])
        if not strikes:
            return 0

        min_loss    = float("inf")
        max_pain_st = strikes[0]

        for target in strikes:
            total_loss = 0
            for s in strikes:
                vals = strike_map.get(s, strike_map.get(str(s), {}))
                ce_oi = int(vals.get("ce", {}).get("oi", 0) or 0)
                pe_oi = int(vals.get("pe", {}).get("oi", 0) or 0)
                # CE buyers lose if target < strike
                total_loss += ce_oi * max(0, s - target)
                # PE buyers lose if target > strike
                total_loss += pe_oi * max(0, target - s)

            if total_loss < min_loss:
                min_loss    = total_loss
                max_pain_st = target

        return max_pain_st

    # ── Alert generation ──────────────────────────────────────

    @staticmethod
    def _generate_alerts(
        rows: list,
        metrics: dict,
        spot: float,
        max_pain: int,
    ) -> list:
        """
        Strong activity detect karke actionable alerts banao.
        Each alert: {type, severity, strike, message}
        """
        alerts = []
        pcr    = metrics["pcr_oi"]
        strong_ce = metrics["strong_ce"]
        strong_pe = metrics["strong_pe"]

        # ── 1. Strong CE wall (resistance) ───────────────────
        if strong_ce and abs(spot - strong_ce) <= 500:
            alerts.append({
                "type":     "RESISTANCE",
                "severity": "HIGH",
                "strike":   strong_ce,
                "message":  (
                    f"Strong Call Wall at {strong_ce} — "
                    f"Heavy CE OI, resistance zone. "
                    f"Sellers defending strongly."
                ),
                "icon": "ti-arrow-bar-up",
                "color": "danger",
            })

        # ── 2. Strong PE support ──────────────────────────────
        if strong_pe and abs(spot - strong_pe) <= 500:
            alerts.append({
                "type":     "SUPPORT",
                "severity": "HIGH",
                "strike":   strong_pe,
                "message":  (
                    f"Strong Put Support at {strong_pe} — "
                    f"Heavy PE OI, support zone. "
                    f"Put writers defending."
                ),
                "icon": "ti-shield-check",
                "color": "success",
            })

        # ── 3. PCR extremes ───────────────────────────────────
        if pcr < 0.6:
            alerts.append({
                "type":     "PCR_EXTREME",
                "severity": "HIGH",
                "strike":   None,
                "message":  (
                    f"PCR {pcr:.2f} — Very low! Call writers dominant. "
                    f"Strong bearish pressure. Caution on longs."
                ),
                "icon": "ti-trending-down",
                "color": "danger",
            })
        elif pcr > 1.6:
            alerts.append({
                "type":     "PCR_EXTREME",
                "severity": "HIGH",
                "strike":   None,
                "message":  (
                    f"PCR {pcr:.2f} — Very high! Put writers dominant. "
                    f"Strong bullish support. Favorable for longs."
                ),
                "icon": "ti-trending-up",
                "color": "success",
            })
        elif pcr < 0.8:
            alerts.append({
                "type":     "PCR_WARN",
                "severity": "MEDIUM",
                "strike":   None,
                "message":  f"PCR {pcr:.2f} — Bearish tilt. More calls being written.",
                "icon": "ti-alert-triangle",
                "color": "warning",
            })
        elif pcr > 1.3:
            alerts.append({
                "type":     "PCR_WARN",
                "severity": "MEDIUM",
                "strike":   None,
                "message":  f"PCR {pcr:.2f} — Bullish tilt. Put writers active.",
                "icon": "ti-info-circle",
                "color": "info",
            })

        # ── 4. Heavy OI buildup near spot ────────────────────
        for row in rows:
            if abs(row["strike"] - spot) > 1000:
                continue
            s      = row["strike"]
            ce     = row["ce"]
            pe     = row["pe"]
            ce_oi  = ce["oi"]
            pe_oi  = pe["oi"]
            ce_chg = ce["chgOI"]
            pe_chg = pe["chgOI"]

            # CE buildup (resistance building)
            if ce_oi > 0 and ce_chg / ce_oi > 0.25:
                alerts.append({
                    "type":     "CE_BUILDUP",
                    "severity": "MEDIUM",
                    "strike":   s,
                    "message":  (
                        f"CE OI buildup at {s} "
                        f"(+{ce_chg:,} contracts). "
                        f"Resistance strengthening."
                    ),
                    "icon": "ti-arrow-bar-up",
                    "color": "danger",
                })

            # PE buildup (support building)
            if pe_oi > 0 and pe_chg / pe_oi > 0.25:
                alerts.append({
                    "type":     "PE_BUILDUP",
                    "severity": "MEDIUM",
                    "strike":   s,
                    "message":  (
                        f"PE OI buildup at {s} "
                        f"(+{pe_chg:,} contracts). "
                        f"Support strengthening."
                    ),
                    "icon": "ti-arrow-bar-down",
                    "color": "success",
                })

            # CE unwinding (resistance weakening — bullish)
            if ce_oi > 0 and ce_chg / ce_oi < -0.25:
                alerts.append({
                    "type":     "CE_UNWIND",
                    "severity": "MEDIUM",
                    "strike":   s,
                    "message":  (
                        f"CE OI unwinding at {s} "
                        f"({ce_chg:,} contracts). "
                        f"Resistance weakening — possible breakout."
                    ),
                    "icon": "ti-bolt",
                    "color": "warning",
                })

            # PE unwinding (support weakening — bearish)
            if pe_oi > 0 and pe_chg / pe_oi < -0.25:
                alerts.append({
                    "type":     "PE_UNWIND",
                    "severity": "MEDIUM",
                    "strike":   s,
                    "message":  (
                        f"PE OI unwinding at {s} "
                        f"({pe_chg:,} contracts). "
                        f"Support weakening — possible breakdown."
                    ),
                    "icon": "ti-bolt",
                    "color": "warning",
                })

        # ── 5. Strong buyer activity (both sides) ─────────────
        strong_buyer_rows = [
            r for r in rows
            if (r["ce"]["dom_label"] in ("Strong Buyers", "Buyers")
                or r["pe"]["dom_label"] in ("Strong Buyers", "Buyers"))
            and abs(r["strike"] - spot) <= 500
        ]
        if len(strong_buyer_rows) >= 3:
            buyer_strikes = [r["strike"] for r in strong_buyer_rows[:3]]
            alerts.append({
                "type":     "BUYER_ACTIVITY",
                "severity": "MEDIUM",
                "strike":   None,
                "message":  (
                    f"Strong buyer activity detected near spot: "
                    f"strikes {', '.join(str(s) for s in buyer_strikes)}. "
                    f"Short covering or fresh longs possible."
                ),
                "icon": "ti-users",
                "color": "info",
            })

        # ── 6. Max Pain vs Spot ────────────────────────────────
        if max_pain and spot:
            pain_diff = max_pain - spot
            if abs(pain_diff) > 300:
                direction = "above" if pain_diff > 0 else "below"
                alerts.append({
                    "type":     "MAX_PAIN",
                    "severity": "LOW",
                    "strike":   max_pain,
                    "message":  (
                        f"Max Pain ({max_pain}) is {abs(int(pain_diff))} pts "
                        f"{direction} spot. "
                        f"Expiry pullback/push towards {max_pain} possible."
                    ),
                    "icon": "ti-target",
                    "color": "warning",
                })

        # Severity order mein sort karo
        order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        alerts.sort(key=lambda a: order.get(a["severity"], 3))

        return alerts[:8]  # Max 8 alerts show karo