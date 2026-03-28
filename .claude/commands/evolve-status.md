# /evolve-status — EvolveSys Status Dashboard

Show the current EvolveSys evolution status: regime, Lyapunov exponent, quality deltas, and bifurcation history.

## Instructions

1. Call AttractorFlow MCP tools to get current trajectory state:
   - `attractorflow_get_regime()`
   - `attractorflow_get_lyapunov()`
   - `attractorflow_get_basin_depth()`

2. Run quality metrics measurement:
   ```bash
   python -m evolve_sys.quality_metrics --json
   ```

3. Read current run log:
   ```bash
   python -m evolve_sys.report
   ```

4. Format and display the combined status using this template:

---

## 🔄 EvolveSys Status

**Regime:** {regime} ({confidence}%)  **λ:** {ftle:+.3f} ({stability_label})
**Basin depth:** {stability}  |  **Steps tracked:** {n_steps}

**Diagnosis:** {rationale}
**Recommended action:** {action}

---

### Quality Progress

| Axis | Baseline | Current | Delta |
|------|----------|---------|-------|
| Test Coverage | {cov_baseline}% | {cov_current}% | {cov_delta:+.1f}% |
| Mypy Errors | {mypy_baseline} | {mypy_current} | {mypy_delta:+d} |
| Benchmark | {bench_baseline}ms | {bench_current}ms | {bench_delta:+.0f}ms |
| Avg Complexity | {cc_baseline} | {cc_current} | {cc_delta:+.2f} |

---

### Bifurcation History

{bifurcation_table or "No bifurcations detected yet."}

---

### Attractor-Flow Regime Distribution (this run)

{regime_bar_chart}

---

*Use `/evolve-cycle` to trigger one improvement cycle.*
*Use `/attractor-status` for raw AttractorFlow diagnostics.*
*Use `/phase-portrait` for trajectory visualization.*
