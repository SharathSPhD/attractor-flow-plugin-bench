# /evolve-cycle — Run One EvolveSys Improvement Cycle

Trigger a single EvolveSys improvement cycle on `target_pipeline/`.

One cycle = explore → bifurcation check → converge → commit.

## Instructions

1. Read the current quality baseline:
   ```bash
   python -m evolve_sys.quality_metrics --json
   ```

2. Record the cycle start state with AttractorFlow:
   ```
   attractorflow_record_state(
     state_text="EvolveSys single cycle starting. [paste quality snapshot]",
     goal_text="Improve target_pipeline/ quality across 4 axes: test coverage, type safety, performance, code complexity"
   )
   ```

3. Get the explorer-agent prompt for this cycle:
   ```bash
   python -c "
   from evolve_sys.quality_metrics import measure_all
   from evolve_sys.improvement_cycle import build_explorer_prompt
   import json
   snap = measure_all(cycle=1)
   print(build_explorer_prompt(snap, cycle=1))
   "
   ```

4. Invoke the **explorer-agent** subagent (via Task tool) with that prompt.
   Wait for it to return a JSON array of improvement proposals.

5. Record each returned proposal:
   ```
   attractorflow_record_state(state_text="Proposal: [title] for [axis] in [file]")
   ```

6. Check for bifurcation:
   ```
   attractorflow_detect_bifurcation()
   ```

   - **If PITCHFORK:** split proposals by cluster, spawn 2 convergence-agents in parallel
   - **If HOPF:** add exit criterion to convergence prompt
   - **If SADDLE_NODE:** checkpoint, inject perturbation, re-explore
   - **If none:** select best proposal, spawn 1 convergence-agent

7. Get the convergence-agent prompt:
   ```bash
   python -c "
   from evolve_sys.quality_metrics import measure_all
   from evolve_sys.improvement_cycle import build_convergence_prompt, ImprovementProposal
   snap = measure_all(cycle=1)
   # Replace with actual proposals from explorer output
   proposals = [ImprovementProposal(axis='test_coverage', title='[from explorer]', description='[from explorer]', target_file='[from explorer]', estimated_impact='[from explorer]')]
   print(build_convergence_prompt(proposals, 'main', snap, cycle=1))
   "
   ```

8. Invoke the **convergence-agent** subagent with that prompt.
   Wait for it to complete and checkpoint.

9. Measure quality after improvement:
   ```bash
   python -m evolve_sys.quality_metrics --json
   ```

10. Record cycle completion:
    ```
    attractorflow_checkpoint()
    attractorflow_record_state(state_text="Cycle complete. delta: coverage=[X]%, mypy=[Y], bench=[Z]ms")
    ```

11. Display cycle summary using the quality delta (before vs. after).

## Notes
- This command drives one cycle manually, ideal for observing attractor-flow dynamics step by step.
- For automated multi-cycle runs, use the attractor-orchestrator agent with the full prompt from:
  `python -m evolve_sys.orchestrator --prompt --cycles 5`
- Check regime between steps with `/attractor-status`
- Visualize trajectory with `/phase-portrait`
