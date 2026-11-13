# Dynamic Systems and Control (DSC) at NeurIPS 2026 — classification rubric

Each main-track paper gets a **tier** (core / adjacent / out), a **subcategory** code, and a one-line reason.
Judge from the title and abstract only. The question is *what the paper contributes*, not what words it uses.

## Tier: core
The paper's main contribution is a method, theory or analysis for **controlling, identifying, estimating or
certifying a dynamical system** (a physical, engineered, biological or abstract system whose state evolves in
time under inputs). A control engineer would recognise the problem as theirs.

| code | subcategory | includes |
|---|---|---|
| `OC` | Optimal control & MPC | optimal control, model predictive control, LQR/LQG, HJB/Pontryagin methods, trajectory optimization with dynamics constraints, differentiable MPC, stochastic/robust optimal control, learning-based MPC |
| `ID` | System identification & learned dynamics for control | identifying dynamical models from data (linear, nonlinear, hybrid, switching), Koopman / operator-theoretic methods (EDMD, Koopman autoencoders, dictionary discovery), equation discovery of dynamical systems (SINDy-style), dynamic mode decomposition, learned dynamics or world models **whose purpose is control, planning or stability analysis**, physics-constrained dynamics models for control, data-driven (Willems-type) control, behavioural systems. Identification of an explicit dynamical model from data is core even when the stated downstream use is prediction |
| `SF` | Stability, safety & certificates | Lyapunov / barrier / contraction certificates, control barrier functions, reachability analysis, safety filters, formal verification of controllers or closed loops, robust stability, dissipativity, input-to-state stability, neural certificate synthesis |
| `ES` | Estimation & filtering | state estimation, Kalman and nonlinear filters, observers, smoothing, data assimilation for dynamical systems, sensor fusion for state, learned filters |
| `LC` | Learning-based & adaptive control theory | adaptive control, online control with regret bounds, non-stochastic control, control of unknown linear/nonlinear systems, sample complexity of controlling systems, control-theoretic analysis of RL (LQR as RL testbed, policy gradient for control), robustness margins, system-level synthesis, networked / distributed / multi-agent control, control of PDEs, delay systems, control with LLMs or foundation models *as controllers* |
| `RC` | Robotics & embodied control | locomotion / manipulation / flight where the contribution is a controller, dynamics-aware planner, whole-body control, contact dynamics for control, learned dynamics for robot control, sim-to-real for controllers. RL for robots is core only if dynamics or control structure is central (e.g. model-based, MPC+RL, stability-constrained); pure end-to-end policy learning on robot benchmarks is adjacent |

## Tier: adjacent
The paper is about dynamical systems or sequential decision making in a way a control researcher would read,
but control / identification / estimation of a system is **not** the contribution.

| code | subcategory | includes |
|---|---|---|
| `MB` | Model-based RL & world models | learned world models / dynamics for RL or planning in general (games, Atari, MuJoCo) without control-theoretic framing; Dyna-style; planning with learned models; model-based offline RL |
| `NO` | Neural ODE/SDE, PDE surrogates & physics-informed dynamics | neural ODEs/SDEs/CDEs, PDE solvers and operator learning (FNO, DeepONet), physics-informed networks, simulation surrogates, Hamiltonian/Lagrangian networks, when the goal is modelling or forecasting rather than control |
| `TD` | Dynamical-systems view of learning | gradient-flow / ODE analyses of training, stability or oscillation of optimizers, feedback or control-theoretic analysis of learning algorithms, implicit bias through dynamics, mean-field / dynamical-systems theory of networks |
| `TS` | Time series & dynamical-system reconstruction | forecasting of physical or dynamical systems with black-box models, chaotic attractor reconstruction with generic sequence models, causal discovery in dynamical systems, dynamical-systems analysis tools (comparing or embedding dynamics) that neither identify an explicit model nor control. Generic time-series forecasting benchmarks (retail, traffic, finance) are **out** unless framed as dynamical systems |
| `SD` | Sequential decision making close to control | safe / constrained / robust RL, risk-sensitive RL, LQ games, stochastic games with continuous state, online learning for dynamic environments, bandits with dynamics, planning under uncertainty (POMDPs) in physical domains, multi-agent coordination of physical agents, inverse optimal control / IRL framed as dynamics. Generic deep RL algorithm papers on standard benchmarks are **out** |

## Tier: out
Everything else. In particular these **false friends** are *out* unless the abstract makes a genuine control
or dynamical-systems contribution:
- "state space model" meaning Mamba/S4-style sequence models for language, vision or audio
- "controllable generation", "controllable diffusion", "control tokens", "ControlNet", "steering" of LLMs
- "training dynamics", "training stability", "learning dynamics" as empirical descriptions (not an ODE/control analysis → `TD` only if the analysis is dynamical-systems-theoretic)
- "human feedback", "control group", "access control", "congestion control", "version control", "quality control"
- "Kalman" or "filter" used for signal denoising in vision/audio, "observer" meaning a human viewer
- "optimal transport", "optimal stopping" in finance unless framed as control
- "robust" meaning adversarial robustness of classifiers
- "stability" of training, numerical stability, stable diffusion
- "trajectory" meaning LLM agent traces or diffusion sampling paths
- "world model" for video generation or language agents with no planning/control use → out; with planning → `MB`
- Reinforcement learning for LLMs (RLHF, GRPO, reasoning) → out
- Robotics papers on perception, VLA models, datasets or language grounding with no controller contribution → out

## Borderline guidance
- Decision between core `ID` and adjacent `NO`/`TS`: Koopman/operator methods, system identification and equation discovery are core `ID` by definition. For other learned dynamics (neural ODEs, neural operators, generic world models) ask whether the model is **used or analysed for control, planning or stability** (core) or only for prediction/simulation (adjacent).
- Decision between core `RC` and adjacent `SD`/`MB`: core if the paper reasons about dynamics, constraints, stability or MPC-like structure; adjacent if it is policy learning with a generic RL algorithm on robot tasks.
- Decision between core `LC` and adjacent `TD`: core if a *system* is controlled; adjacent if the "system" is the learning algorithm itself.
- Diffusion / flow-matching papers that cast sampling as stochastic optimal control (Schrödinger bridges, control of SDEs for sampling) → adjacent `SD`, unless they control a physical system → core `OC`.
- Theory papers on LQR, linear systems, Markov decision processes with continuous dynamics, or online control → core `LC`/`OC`.
- Papers on PDE control, fluid control, plasma control, power grids, traffic, HVAC, chemical processes → core (`OC`/`LC`) when they control, adjacent `NO` when they only simulate.
- Mean-field games with dynamics → adjacent `SD`; mean-field control → core `OC`.

## Output format (per paper)
```json
{"id": "<neurips id>", "tier": "core|adjacent|out", "sub": "<code or null for out>", "reason": "<= 20 words"}
```
