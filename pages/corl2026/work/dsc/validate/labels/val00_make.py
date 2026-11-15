import json,sys
L="""IY6ti85pg0|core|RC|CLF-guided RL around model-based safe reference for humanoid foothold locomotion
QBAA8svAIK|out||Generic federated RL algorithm with diffusion priors; no control contribution
R1fgJZLFnx|adjacent|SD|End-to-end RL loco-manipulation policy with tactile latent and reward design
WxBKiMUZtI|adjacent|SD|RL motion tracking with contact rewards; generic policy learning
58liP3p4hu|core|ID|Learns actuator dynamics model from joint trajectories for sim-to-real control
m94Acp7Al5|core|RC|Receding-horizon safe UAV following planner with risk-scored trajectory repair
C08KksTfEx|adjacent|SD|Learned whole-arm contact trajectories from demos fed to kinematic optimizer
0mUj0bXuJh|adjacent|SD|Automatic curriculum for RL locomotion training
fGWkovHMQE|out||VLA reasoning architecture; no controller contribution
Sh0dG0HwVK|adjacent|SD|Diffusion-policy imitation learning from suboptimal data; generic IL
7KV78k8rcv|out||VLA cross-embodiment training recipe via visual masking
79jC3quhGp|out||VLA models for human-robot collaboration; empirical study
lY47GBfn32|out||Humanoid motion dataset
C96z0RnFh8|out||Agentic coding harness for robot programming
FuxTpvfYnh|adjacent|MB|Learned navigation world model used for planning
iIanOcE27q|core|RC|Online material property estimation to set minimal grasp force control
rJe0dLlPev|adjacent|SD|Fine-tuning RL locomotion policies for footwear morphology changes
DMljKr2f4O|core|SF|Learning neural control barrier functions via HJ value approximation
tegLlXBRCU|out||VLA action-token planning; no controller contribution
8klpl3FXjN|core|ID|Residual actuator dynamics model with state estimator for humanoid sim-to-real
334wtBsPIG|out||Multimodal representation bottleneck for visuo-tactile policy encoding
Qa1Uu7lc8n|adjacent|SD|Sim-trained point-track conditioned dexterous policy; generic policy learning
mjvsJNQuFV|core|RC|Fault-tolerant whole-body control with fault estimation and stability-preserving posture adaptation
3Ex2nEGqHP|adjacent|SD|Training strategies for shared learned WBC under skill composition
994ptkAdnU|core|ID|Dynamics estimation world model for fault detection and parameter identification
JQvRoFU5aS|out||VLA failure recovery via imagined milestones
bsjuF5klA3|out||VLA post-training data reweighting
Gkka9VEhWb|core|RC|Force-supervised planner providing contact-force references to tactile admittance controller
iy5oCeLdEF|adjacent|SD|Latent action imitation learning from videos
l8hOz8loVg|adjacent|SD|Hierarchical RL with motion-imitation priors for loco-manipulation
gvM7KWEhVI|core|SF|Flow planner certified via high-order control barrier functions
Ti3oK55n1H|core|RC|Learned residual torque adaptation compensating dynamics mismatch
U3Nmrhun8B|adjacent|SD|RL fine-tuning algorithm for VLA policies
84ea2xeP60|adjacent|SD|Sim-to-real distillation of WBC and RL experts into vision policy
O7LrmASsJS|adjacent|SD|End-to-end perceptive RL parkour policy for humanoid
DwRC6la1Kr|out||Demo-conditioned VLA latent planning; perception-centric
xOhVCWilYJ|out||VLM grounding with affordance heatmaps
UVJPDRCmlf|core|OC|Output-feedback robust MPC with differentiable simulator for deformables
uoFfrJHHq8|core|RC|RL modulating reference trajectories for constrained quadrotor inversion control
vVIVf2E7KG|core|ID|Perception-conditioned learned vehicle dynamics for off-road control
y1uP4arjzC|core|SF|Predictive control barrier enforcement for safe robot control
XnyoJXimAK|adjacent|SD|Hierarchical RL with latent motion priors for humanoid soccer
kBoTnjRw4s|adjacent|SD|Cross-embodiment learned WBC foundation policy
v24DO7JOuN|core|ID|Learned multi-physics dynamics model integrated with MPC for manipulation
dngZLI0SlV|adjacent|MB|Model-based RL with chunk world model
loMfT7cfYl|core|RC|Predicts task frame and gains for admittance compliance control
Alu9eLT93i|core|OC|Distills long-horizon MPC into vision-parameterized short-horizon MPC
8MNr0evyJT|adjacent|SD|Retargeting-guided residual RL for dexterous manipulation
qEOv7MuWIx|core|ID|Adapting learned vehicle dynamics models for high-speed MPC
L8ATlveWKT|core|ES|Differentiable particle filter for SE(3) LiDAR localization
SN5sVBOZ8D|adjacent|SD|VLA transfer to aerial manipulation with payload-aware sampling guidance
QAHhXvXHtb|out||Gripper hardware for data collection
MQlY5j6pnd|adjacent|SD|Action augmentation for imitation policies on moving objects
wALhOwQWnx|core|RC|Learned task-dependent directional compliance control for whole-body manipulation
hr2FYFod4n|adjacent|SD|Survival-model wait-or-reroute navigation planning under uncertainty
RmP7m64fQ6|out||VLM steering of pretrained policies
cHCwUratwL|adjacent|SD|Unified multi-skill RL policy for humanoid soccer
MTZ4eKUP94|out||Continual learning for grasp synthesis
4pwzyVBjXY|core|LC|Dynamic regret analysis for replanning under drifting dynamics
3hsq75Gmr9|core|ID|Physics-guided residual dynamics for deformables used in MPC
Gpc0nCixhZ|adjacent|SD|Multi-robot imitation learning for coordinated pushing
hDNvcoKMXH|adjacent|SD|Hierarchical imitation learning using grasp pretraining
CSYA6oHdlE|core|OC|Learned conic solvers for covariance steering optimal control
xyFvvMLQRo|out||Memory architecture for chained-goal navigation
1zYrrwoISV|core|RC|Force-aware model with wrench prediction and online force-feedback correction
msKuD5tWYj|adjacent|SD|Multi-agent self-play residual RL for parking
NZrwlgnR4X|adjacent|SD|Energy-based selection of low-level policies and goals
sIYfeRhQrn|core|SF|Multi-step HJ reachability safety Bellman learning for humanoids
nzYChkCtvT|core|OC|Simulator-in-the-loop MPPI for cloth manipulation
aq2hmhW0kU|out||Humanoid-free data collection interface
Tk20sRMzhv|out||Transformer prediction of rehab trajectories from sEMG
51YZMUGRUA|out||Simulation-augmented policy evaluation
TH0fdttVB0|out||Language-based personalization of tactile policies
ShBMWDRPVu|out||3D trace prediction world model without planning
2tjuz95jmb|adjacent|SD|Generative motion planner with learned tracking policy for humanoids
z5Mgc1GGjP|adjacent|SD|Sim-to-real RL fine-tuning of VLAs in generated worlds
c9tCcHtVcS|adjacent|SD|Uncertainty tubes from diffusion trajectory models for risk-aware planning
uKRtsLLqs6|out||Multi-object dexterous grasp generation
oKJnHTluoA|out||VLA geometric motion conditioning
nl8iBTm3Mt|core|ES|Equivariant learned measurements for filter-based inertial odometry
X4i3kSa2kd|core|RC|Velocity feedforward low-latency whole-body teleoperation control
sIe2LX2HaF|adjacent|SD|Real2sim2real data engine for dexterous cutting policies
k6kMJCL22t|core|SF|Neural HJ reachability for safety-critical control
qx5mPYiXVi|adjacent|SD|Value reliability study in offline-to-online robot RL
GseuCgLNtO|out||Gripper hardware design
GX5xey9ade|out||Spatial annotation of robot demonstrations
f3Dic5dJnz|adjacent|SD|Tactile reflex controller used to shape demonstrations for imitation
yPkDKkOD11|adjacent|MB|Learned dynamics model guides robot design diffusion
mMRhLrwLFx|core|RC|Inverse dynamics model adaptation aligning humanoid control to target dynamics
Wv9xF5Ii7L|adjacent|SD|Policy gradient RL for flow-matching manipulation policies
qKU6lifnPU|out||VLA mixture-of-experts sensor routing
yNHgrgATuY|out||VLA fine-tuning objective for visual features
aspenN9eir|adjacent|SD|Human-in-the-loop adaptation of generative policies
MQdt80qzTP|adjacent|SD|Adaptive environment sampling for large-scale RL
sitHOFsi2x|out||Manipulation data generation from human videos
YQoaLlpDD3|adjacent|MB|Morphology-conditioned world model for policy learning in imagination
XJgz1iK29G|core|RC|LLM-guided search with kinodynamic trajectory optimization for loco-manipulation
psNqjklVOK|adjacent|MB|Differentiable world model for policy learning via imagined rollouts
HATezFmdN5|adjacent|MB|Video world models from play used for policy evaluation and RL
c7BvD59RpP|adjacent|SD|Visual RL policy gradient algorithm for robot control
AilV1LyfXF|out||Video diffusion backbone repurposed as robot policy
Am3aGfOlLh|out||VLA spatial alignment features
yzejD0WIk9|core|RC|Onboard spiking-network state estimation and control for flapping-wing flight
ALlLaCTHKQ|adjacent|SD|Tactile behavior cloning for cable tracing
uMgOYXmgn2|adjacent|SD|Mamba-based humanoid locomotion policy robust to sensor dropout
ntHuqgjrgs|out||World action model using image editing priors
cxxUgLuNa2|out||Dexterous grasp synthesis with human priors
WNZ4Dr57JS|out||Zero-shot 3D object perception
39Q3r1h0mD|core|OC|Learning-based MPC with residual dynamics and learned critic in iLQR"""
lab={}
for l in L.splitlines():
    i,t,s,r=l.split('|'); lab[i]={"id":i,"tier":t,"sub":s or None,"reason":r}
d=json.load(open(sys.argv[1]))
assert set(lab)==set(p['id'] for p in d),(set(lab)^set(p['id'] for p in d))
json.dump([lab[p['id']] for p in d],open(sys.argv[2],'w'),indent=1)
