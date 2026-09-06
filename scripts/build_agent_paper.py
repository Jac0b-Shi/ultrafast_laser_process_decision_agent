"""Render paper figures and assemble an English manuscript from saved experiment tables."""
import json
import re
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data/processed/agent_experiment"
OUT=ROOT/"docs/research/english"
TITLE="AI-Bridged Data-Knowledge Fusion for Intelligent Laser Parameter Recommendation in Ultrafast Laser Processing"
NAMES={"4H碳化硅":"4H-SiC","微晶玻璃":"Glass ceramic","金刚石":"Diamond","高温合金":"Superalloy"}
TARGET={"depth_um":"Depth","roughness_um":"Roughness","diameter_um":"Diameter"}
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"axes.spines.top":False,"axes.spines.right":False,"savefig.dpi":220})


def save(fig,name):
    fig.savefig(OUT/"figures"/(name+".png"),bbox_inches="tight",facecolor="white")
    fig.savefig(OUT/"figures"/(name+".svg"),bbox_inches="tight",facecolor="white")
    plt.close(fig)


def table(frame):
    headers=list(frame.columns)
    rows=["| "+" | ".join(headers)+" |","|"+"|".join(["---"]*len(headers))+"|"]
    for row in frame.itertuples(index=False,name=None):
        rows.append("| "+" | ".join(f"{v:.3f}" if isinstance(v,(float,np.floating)) else str(v) for v in row)+" |")
    return "\n".join(rows)


def build():
    (OUT/"figures").mkdir(parents=True,exist_ok=True)
    m=pd.read_csv(DATA/"metrics.csv");p=pd.read_csv(DATA/"predictions.csv");f=pd.read_csv(DATA/"feedback.csv");s=pd.read_csv(DATA/"scoring.csv")
    provenance=json.loads((DATA/"provenance.json").read_text())
    wide=m.pivot(index=["material","target"],columns="variant",values="rmse")
    gain=(1-wide.fusion_simple/wide.raw_simple)*100
    primary=[("BF33","depth_um"),("AlSiC","depth_um"),("ZrO2","depth_um"),("CFRP","depth_um"),("金刚石","roughness_um")]
    # One compact method figure with explicit inputs and outputs.
    fig,ax=plt.subplots(figsize=(10,3.9));ax.set_xlim(0,10);ax.set_ylim(0,4);ax.axis("off")
    boxes=[(.1,2.6,2.0,"Literature + records\nEquations, units, scope"),(2.75,2.6,2.0,"Knowledge mapping\nReviewed relations"),(5.4,2.6,2.0,"Compute variables\nz = phi(x; K)"),(7.95,2.6,1.95,"Grouped validation\nPredict quality y")]
    for x,y,w,text in boxes:
        ax.add_patch(FancyBboxPatch((x,y),w,1,boxstyle="round,pad=.08",facecolor="#e9f1ee",edgecolor="#497565"));ax.text(x+w/2,y+.5,text,ha="center",va="center",fontsize=9)
    for x in (2.15,4.8,7.45):ax.annotate("",xy=(x+.5,3.1),xytext=(x,3.1),arrowprops={"arrowstyle":"->","color":"#497565"})
    ax.text(2,1.25,"Measured historical match?",ha="center",fontsize=11)
    ax.annotate("",xy=(2.0,1.7),xytext=(1.1,2.5),arrowprops={"arrowstyle":"->"})
    ax.text(5.7,1.25,"Yes: reuse one observed setting\nNo: rank supported new settings",ha="center",fontsize=10)
    ax.annotate("",xy=(4,1.4),xytext=(3.5,1.4),arrowprops={"arrowstyle":"->"})
    ax.annotate("",xy=(7.5,1.7),xytext=(8.9,2.5),arrowprops={"arrowstyle":"->"})
    ax.text(5,.15,"Measured feedback → append record → update data version → refit",ha="center",fontsize=10)
    save(fig,"method")
    fig,ax=plt.subplots(figsize=(8,6.2));labels=[NAMES.get(a,a)+" / "+TARGET[b] for a,b in gain.index];positions=np.arange(len(gain));ax.barh(positions,gain.to_numpy(),color=["#287b68" if v>=0 else "#b96747" for v in gain]);ax.set_yticks(positions,labels);ax.invert_yaxis();ax.axvline(0,color="#555",lw=.8);ax.set_xlabel("Test RMSE reduction from mechanism variables (%)");ax.grid(axis="x",alpha=.2);save(fig,"mechanism_gain")
    fig,axes=plt.subplots(1,3,figsize=(10,3.2))
    for ax,(material,target) in zip(axes,primary[:3]):
        q=p.loc[(p.material==material)&(p.target==target)&(p.variant=="fusion_simple")]
        lo=min(q.measured.min(),q.predicted.min());hi=max(q.measured.max(),q.predicted.max());ax.scatter(q.measured,q.predicted,color="#287b68",s=30,alpha=.85);ax.plot([lo,hi],[lo,hi],"--",color="#888",lw=1);ax.set_title(NAMES.get(material,material));ax.set_xlabel("Measured depth (μm)");ax.set_ylabel("Predicted depth (μm)");ax.set_aspect("equal",adjustable="box")
    fig.tight_layout();save(fig,"prediction_parity")
    fig,axes=plt.subplots(1,2,figsize=(9,3.3))
    rates=s.groupby("variant").satisfied.mean().reindex(["constraint_only","constraint_uncertainty","full_score"])
    axes[0].bar(["Target","+ uncertainty","+ support"],rates*100,color=["#a6bbb3","#699487","#287b68"]);axes[0].set_ylabel("Targets satisfied (%)");axes[0].set_ylim(0,max(40,rates.max()*120));axes[0].set_title("Held-out candidate ranking")
    for mode,color in (("raw","#a1694d"),("fusion","#287b68")):
        q=f.loc[f['mode']==mode].copy();den=q.groupby(["material","target"]).rmse.transform("first");q["relative"]=q.rmse/den
        avg=q.groupby("fraction").relative.median();axes[1].plot(avg.index*100,avg,marker="o",label=mode.capitalize(),color=color)
    axes[1].set_xlabel("Available feedback pool (%)");axes[1].set_ylabel("Median RMSE / initial RMSE");axes[1].legend(frameon=False);axes[1].set_title("Development-set feedback experiment");fig.tight_layout();save(fig,"decision_feedback")
    selected=m.loc[(m.variant=="fusion_simple") & m.set_index(["material","target"]).index.isin(primary)].copy()
    selected["Material"]=selected.material.map(lambda x:NAMES.get(x,x));selected["Response"]=selected.target.map(TARGET)
    selected["Raw RMSE"]=[wide.loc[(a,b),"raw_simple"] for a,b in zip(selected.material,selected.target)]
    selected["Fusion RMSE"]=selected.rmse;selected["Fusion R²"]=selected.r2
    selected["Model"]=selected.algorithm.str.replace("_"," ")
    result_table=table(selected[["Material","Response","Model","Raw RMSE","Fusion RMSE","Fusion R²"]])
    # Select median development-target cases, not the most favorable errors.
    comparisons=s.loc[(s.variant=="full_score") & s.set_index(["material","target"]).index.isin(primary[:3])].groupby(["material","target"],sort=True).nth(1).copy()
    comparisons["Material"]=comparisons.material.map(lambda x:NAMES.get(x,x))
    comparison_table=table(comparisons.rename(columns={"nominal":"Nominal target (μm)","predicted":"Predicted (μm)","measured":"Measured (μm)","absolute_target_error":"Target error (μm)"})[["Material","Nominal target (μm)","Predicted (μm)","Measured (μm)","Target error (μm)"]])
    def g(material,target):return float(gain.loc[(material,target)])
    rate_counts=s.groupby("variant").satisfied.agg(["sum","count"])
    improved=int((gain>0).sum());total=len(gain)
    counts=pd.read_csv(DATA/"split_manifest.csv").groupby("material").size()
    count_text=", ".join(f"{NAMES.get(name,name)} ({count})" for name,count in counts.items())
    manuscript=rf'''# {TITLE}

## Abstract

Ultrafast laser parameter recommendation requires a connection between measured process records and knowledge of pulse delivery, scanning geometry and cumulative exposure. A language model can identify relevant relationships, but numerical recommendation requires a computable representation and independent validation. This study develops a knowledge-guided transformation from recorded process inputs to intermediate variables, followed by material-specific regression and history-first decision making. Reviewed relationships define the input fields, unit conversions and applicability conditions; deterministic calculations supply the model features. Fourteen library estimators are organized into simple and nonlinear comparison families, with model selection performed by grouped validation within the development data. The evaluation uses {provenance['rows']} machining records and a fixed parameter-group holdout. Mechanism variables reduce simple-model test RMSE in {improved} of {total} material–response tasks. Depth RMSE decreases by {g('BF33','depth_um'):.1f}% for BF33, {g('AlSiC','depth_um'):.1f}% for AlSiC and {g('ZrO2','depth_um'):.1f}% for ZrO₂. The contribution depends on the response: additional variables do not improve every task. A separate decision rule reuses qualifying measured settings before considering model-generated candidates and returns one setting at a time. Measured feedback updates the next recommendation while preserving the original observations.

**Keywords:** ultrafast laser processing; intermediate variables; knowledge-guided regression; parameter recommendation; grouped validation

## 1. Introduction

Ultrafast laser machining provides a flexible route to material removal and surface modification, but the selection of process parameters remains strongly coupled. Repetition frequency and scanning speed determine how pulses are distributed along a path; line spacing and repeated scans determine how exposure accumulates over an area. Pulse energy and duration affect the energy delivered during each interaction. A process setting therefore cannot be evaluated by treating its recorded fields as unrelated controls. The practical objective is to select a setting that meets a specified depth, roughness or feature-size requirement while remaining compatible with available equipment and supporting measurements.

Experimental and physical studies provide useful relationships for this task. Ben-Yakar and Byer examined femtosecond ablation of borosilicate glass and its threshold-dependent response [1]. Žemaitis et al. connected scanning parameters, incubation and depth saturation in a model of cavity ablation [2]. These studies motivate variables describing spatial pulse separation and accumulated exposure. Such relationships are useful even when the available database does not contain every quantity required for a complete ablation model. Their use nevertheless requires a clear distinction between a directly computable geometric variable and a proxy whose physical interpretation depends on missing energy or spot-size information.

Machine learning offers a complementary way to estimate process–response relationships from measured records. Physical model-guided learning has been investigated for laser-induced plasma micromachining, where physical information is incorporated into prediction and process optimization [3]. This establishes a relevant precedent for using process knowledge as a model input. The challenge addressed here is the conversion of heterogeneous knowledge into a consistent representation that can be applied to existing machining tables, rather than the design of a new regression estimator. The same representation must support validation, explanation and the calculation of candidate settings.

A second difficulty arises at the decision stage. A prediction score and a measured historical result describe different kinds of evidence. If an existing setting already satisfies the requested quality, replacing it merely because a model assigns another setting a higher score is unnecessary. When the target has no qualifying historical match, prediction becomes useful for selecting a new setting. This distinction motivates a history-first policy with an explicit matching rule, followed by constrained candidate evaluation only when needed.

The proposed method combines knowledge-guided intermediate-variable construction with material-specific model selection and one-setting recommendation. The main methodological contribution is the mapping from documented relationships to computable inputs, including field requirements, units and applicability. Simple regression models test whether that representation contributes useful predictive information without requiring a complex estimator. Nonlinear alternatives provide a broader comparison. The decision procedure separates target matching from prediction uncertainty and data support, and uses measured feedback to update subsequent recommendations. The experiments examine these contributions separately: representation quality, model-family comparison, candidate ranking and feedback-driven updating.

## 2. Problem and Data Description

### 2.1 Problem description

Let x denote adjustable process settings, m the material and processing context, and y the measured quality responses. A user specifies target values or one-sided bounds together with tolerances. The recommendation problem is to return one setting within the admissible equipment domain that satisfies all requested responses. A historical record consists of the setting, its measured responses and its source identifier. Knowledge consists of documented relationships with defined inputs, units and conditions of use.

The solution has three connected transformations. First, knowledge K and settings x produce intermediate variables z = φ(x; K). Second, a fitted response model estimates y from x and z under the material context. Third, the target rule checks observed records and, if necessary, ranks supported candidate settings. Figure 1 shows how these transformations enter a single decision process. Feedback supplies an additional measured input–output pair for the next decision; it is not treated as confirmation of a prediction until a measurement is recorded.

![Figure 1. Inputs, intermediate-variable construction, quality prediction and history-first recommendation.](figures/method.png)

### 2.2 Data description and preprocessing

The dataset contains {provenance['rows']} records: {count_text}. The sources include original Excel machining tables and four instrument-export CSV datasets. They describe pulse duration, repetition frequency, scanning speed, line spacing, repeated processing, defocus or energy-related settings according to the source experiment. Depth, roughness and diameter are treated as separate response tasks. The label “roughness” follows the definition in each source table; material-specific fitting avoids pooling differently defined roughness measurements into a common response model.

Preprocessing preserves the source file and row for every observation. Frequencies, scanning speeds and geometric quantities are represented with explicit units. CSV line spacing recorded in millimetres is converted to micrometres. Missing responses are excluded only from their corresponding regression task. Inequality-marked observations are retained as censored records and are not substituted by their reported limit in ordinary regression. Near-zero descriptions are encoded as zero with a retained flag. Negative datum-relative depths remain available for inspection but do not enter nonnegative quality prediction or historical matching.

Repeated observations with the same recorded process settings form one parameter group. Groups are allocated to development or test data before task-specific response filtering. This prevents repeated measurements of a setting from appearing on both sides of the evaluation. Missing predictor values are imputed using training-fold medians. Scaling, response-dependent reference quantities and estimator fitting are likewise performed within the training fold. Columns without observed training values are excluded in that fold. These rules are shared by the model comparisons and intermediate-variable ablations.

## 3. Methodology

### 3.1 Knowledge-Guided Intermediate Variable Construction

The input to this stage is a set of process fields with units and a documented relationship. Its output is a numerical variable with a specified meaning and applicability condition. A knowledge record identifies the source passage or equation, the required fields, their unit conversions and the applicable material or processing context. AI assists with retrieval and interpretation of these records. The proposed relationship is reviewed before it enters the calculation registry. Numerical evaluation is deterministic, so a language-model response cannot directly introduce a new process value or execute a formula as arbitrary code.

For repetition frequency f in kHz and scanning speed v in mm/s, the pulse line density and spacing are

$$N_L = 1000f/v, \qquad \Delta x = v/f.$$

Here N_L is expressed in pulses/mm and Δx in μm. Their reciprocal relation makes their physical roles explicit: frequency and speed jointly determine spatial pulse delivery. This representation follows the scanning interpretation used in ablation studies [2]. The quantities are calculated from the input settings and are not additional measured responses to be predicted.

When the number of scans n and line spacing h in μm are available, cumulative line density and a spacing-normalized exposure index are

$$N_{{cum}} = N_L n, \qquad I_A = N_L n/h.$$

The index I_A has the recorded mixed-unit convention pulses/(mm·μm); conversion to pulses/mm² multiplies it by 1000. It represents geometric exposure and does not substitute for energy fluence. Pulse energy and illuminated area would be required to calculate fluence. A normalized line density N_L/N_c can also be formed, where N_c is the minimum positive-response line density in the training data for the applicable material. N_c is an empirical reference scale, not an independently measured ablation threshold, and is re-estimated inside each training fold.

Other source-supported fields permit duration–time interaction τt, duty-cycle proxy τf × 10⁻¹² for τ in fs and f in kHz, and average-power or per-mark proxies. Their interpretation is restricted to the recorded experiment. In particular, a quantity obtained by dividing average power by a field described as marking frequency or count retains that source convention; it is not presented as a universal energy measurement. Table 1 summarizes the transformation contract. An unavailable input yields an unavailable intermediate value rather than an AI-invented substitute.

Table 1. Intermediate-variable inputs and outputs.

| Input fields | Output | Interpretation and condition |
|---|---|---|
| Frequency f, speed v | N_L and Δx | Spatial pulse delivery; positive v and f |
| f, v, scan count n | N_cum | Accumulated line exposure |
| f, v, n, line spacing h | I_A | Spacing-normalized exposure index; positive h |
| N_L, training responses | N_L/N_c | Empirical relative density; training-only reference |
| Duration τ, processing time t | τt | Prespecified time interaction when both fields exist |
| τ, f, energy/power fields | Duty and power proxies | Source-specific energy-delivery representation |

### 3.2 Data–Mechanism Fusion Modeling

Each response is fitted using the augmented vector [x, φ(x; K)]. The purpose of the intermediate variables is to expose process relationships that a model using raw inputs would otherwise need to infer from the available samples. A linear or regularized model can then represent a nonlinear relationship in the original settings through a linear combination of these variables. This is the reason for assessing simple models explicitly: improved performance with a simple estimator is evidence that the representation itself is useful.

The simple family contains ordinary least squares, Ridge, ElasticNet, Bayesian Ridge and Huber regression. The comparison family contains nearest-neighbour regression, support-vector regression, a decision tree, random forest, Extra Trees, gradient boosting, histogram gradient boosting, Gaussian-process regression and a multilayer perceptron. These families cover linear regularization, local similarity, kernel methods, tree partitions, ensembles and neural approximation. Their inclusion therefore follows modelling assumptions rather than an arbitrary limit on the number of algorithms.

Three-fold parameter-group validation within the development set selects the estimator with the lowest RMSE for each response and representation. The same preprocessing pipeline is fitted separately in every fold. The selected estimator is refitted on the complete development set and evaluated on the fixed test set. The test responses do not select the estimator or representation. Candidate failures and selection scores are retained. In the application, AI may propose a subset from the registered algorithms, but numerical validation determines the final choice. Manual selection restricts the candidate set to the requested estimator.

### 3.3 Scoring Function for Constraint-Aware Recommendation

For response j, let t_j be the nominal target and ε_j its tolerance. The deviation d_j is |y_j − t_j| for an equality target, max(0, y_j − t_j) for an upper bound, and max(0, t_j − y_j) for a lower bound. A response satisfies the requirement when d_j ≤ ε_j. The normalized matching loss and matching score are

$$L_{{match}} = \frac{{1}}{{q}}\sum_{{j=1}}^q \frac{{d_j}}{{\max(\varepsilon_j,0.01|t_j|,0.001)}},\qquad S_{{match}}=\frac{{1}}{{1+L_{{match}}}}.$$

The 0.001 floor is in the response unit μm and prevents division by zero; it does not widen the acceptance tolerance. An observed record evaluated against its own measured target has zero matching loss and score 1. A historical record is eligible only if all requested responses are observed and satisfy their constraints. Among eligible records, target deviation is followed by repeated-measurement stability and supporting observation count. This rule operates before predictive ranking, so a prediction score cannot displace a qualifying measured record.

If no historical record qualifies, the model evaluates candidates within the observed parameter bounds and the stated equipment steps. Unspecified adjustable dimensions retain recorded settings. Previously measured settings are excluded from this generated pool to avoid replacing known responses with more favourable predictions. For a generated candidate, the ranking loss is

$$J(x)=L_{{match}}(\hat y(x))+0.2U(x)+0.2D(x).$$

U is grouped-validation RMSE normalized by the target scale. D is the minimum root-mean-square distance to a training setting after scaling each process field by its training interquartile range. A zero interquartile range uses a unit scale. Candidates require complete predicted targets, predicted tolerance satisfaction and D ≤ 1. The application returns the admissible candidate with the lowest J, together with its nearest case evidence. It returns a request for additional information when no supported candidate remains. Matching score, validation error and support distance are reported as separate quantities because they answer different questions.

### 3.4 Online Decision Workflow for Laser Parameter Recommendation

The decision state comprises the material context, target specification, available knowledge and current measured dataset. A dialogue collects the missing target fields and displays one result. The state first passes through historical matching; only the unmatched branch invokes model selection and candidate generation. Thus, the online procedure preserves a direct path from an already demonstrated setting to reuse, while reserving inference for an unmet target.

After machining, the user records the actual settings and quality measurements against the recommendation identifier. The measurement becomes an additional observation after validation. The next decision uses the updated dataset and refits its response models. This is sequential evidence-based updating: the new observation changes the model and the next selected setting. No acquisition-function or Bayesian-optimization claim is required for this update rule.

Knowledge retrieval and numerical computation have separate responsibilities. Documents supply relationships and explanations with source locations; the calculation registry supplies executable numerical operations. Public source data can support all users, whereas private measurements and documents enter only their owner's state. Each recommendation records its data version and model-selection evidence. Corrections, removal and restoration of feedback change the active data view through appended events, preserving the earlier measurements and allowing the decision history to be reconstructed.

## 4. Experimental Validation

### 4.1 Experimental Setup

The experiment uses an approximately 80%/20% development/test split for each material, with random seed 42 and complete parameter groups kept together. A response task requires at least 20 nonnegative development observations and four test observations; materials require at least eight parameter groups before splitting. The resulting {total} tasks cover depth, roughness and diameter. Response-specific counts are retained with the result tables rather than presented as a separate sample-count table.

Raw-input and full-fusion representations are compared under both estimator families. Geometry-only and time/power-only additions are also assessed using the simple family. The estimator settings are fixed in the experiment configuration and selection uses three grouped folds, with the same 120-second family budget for each representation. The nearest historical-setting baseline uses training-median imputation and interquartile-scaled parameter distance. RMSE, MAE and R² are calculated on the same observed test responses for every method within a task.

Candidate ranking is assessed separately using nominal targets at the development-response quartiles. The tolerance is 10% of the development interquartile range, with a 0.001 μm minimum. For each target, the held-out settings form a common candidate set: models predict their quality, the score selects one candidate, and the recorded response evaluates target error. This design makes nominal target, predicted quality and measured quality directly comparable. Constraint-only, uncertainty-augmented and full-support scores are tested without changing the predictive model.

The feedback experiment is contained within the development data. Twenty percent of its parameter groups form a fixed evaluation subset. The remaining groups are revealed in a seeded order at 50%, 75% and 100% of the feedback pool. The simple models are reselected and refitted after each increment. This separates the effect of additional measurements from the final test-set comparison. All transformations, split identifiers, predictions and selections are saved with the configuration and data hash.

### 4.2 Experimental Results

Figure 2 shows the change in simple-model test RMSE across all {total} tasks. The mechanism representation reduces RMSE in {improved} tasks. The improvement is particularly clear for AlSiC depth ({g('AlSiC','depth_um'):.1f}%), ZrO₂ depth ({g('ZrO2','depth_um'):.1f}%) and BF33 depth ({g('BF33','depth_um'):.1f}%). Table 2 gives the corresponding models and several additional informative tasks. Figure 3 displays every test observation for the three depth examples against the identity line, making both systematic bias and individual errors visible.

![Figure 2. Change in test RMSE after adding intermediate variables to the simple model family. Positive values indicate improvement; all material–response tasks are retained.](figures/mechanism_gain.png)

Table 2. Selected task comparisons. RMSE is expressed in μm; models are selected within development data.

{result_table}

![Figure 3. Predicted versus measured depth on the fixed test groups. The dashed line denotes equality.](figures/prediction_parity.png)

The comparisons support a response-dependent interpretation of the representation. Scan-density and cumulative-exposure variables allow a simple model to express coupled input effects in tasks where those effects are informative. They do not guarantee a gain when the response is weakly described by the recorded fields. For example, SiC depth remains poorly predicted, and adding all intermediate variables degrades the simple-model diamond-depth result. These outcomes argue for validating feature families rather than automatically including every derived quantity. The complete raw, geometry, time/power and fusion comparisons are supplied in the accompanying results.

The nonlinear family provides a distinct comparison. It can improve some tasks further, including the tested ZrO₂ and CFRP depth tasks, while a simple fusion model is competitive on others. This pattern separates the benefit of the representation from estimator flexibility. The evidence supports the use of the intermediate construction as a useful modelling component, rather than a claim that simple regression universally dominates nonlinear methods.

Across {int(rate_counts.loc['full_score','count'])} nominal-target tasks, constraint-only ranking satisfies {int(rate_counts.loc['constraint_only','sum'])} targets and the full score satisfies {int(rate_counts.loc['full_score','sum'])}. Adding a task-level validation-error term alone leaves the selected candidate unchanged because that uncertainty term is constant across the candidates of a single response model. The observed ranking changes therefore arise from the support-distance term. Figure 4 reports the target satisfaction rates alongside the feedback comparison. This distinction prevents assigning an empirical ranking benefit to an uncertainty component that is not candidate-specific.

Table 3 compares nominal targets, predictions and recorded measurements for the median-development-target case in each of the three depth examples. Cases are selected by that fixed rule, not by their final error. The difference between predicted and measured quality is a prediction error; the difference between nominal and measured quality is the actual target deviation. The two quantities are kept separate when assessing whether a selected setting meets the requirement.

{comparison_table}

![Figure 4. Left: target satisfaction under scoring ablations. Right: median normalized prediction error as development feedback groups are added; each task is normalized by its initial error.](figures/decision_feedback.png)

### 4.3 Integrated Analysis and Decision Workflow

The experiments locate the useful contribution at the conversion from recorded settings to process-related variables. The improvement in several depth tasks shows that a compact regression model can exploit this representation. The mixed results across responses also identify its boundary: a geometric exposure proxy cannot supply an unrecorded material state, measurement condition or energy-distribution variable. Additional complexity does not uniformly resolve that missing information. Task-specific grouped validation is therefore part of the method, not merely a final reporting step.

Historical matching and predictive candidate ranking serve different purposes. The self-target property gives an observed record score 1 without claiming that every historical setting is suitable for every target. The priority rule then prevents a model's internal score from competing directly with qualifying measurements. For unmet targets, nominal–predicted–measured comparison exposes whether a score-selected candidate delivers the intended quality. The modest satisfaction counts under tight tolerances motivate explicit tolerances and support conditions in the user interaction rather than an unqualified optimality claim.

The feedback comparison examines how the same modelling procedure responds when more independent parameter groups become available. Error need not decrease at every increment because new groups can change the fitted relation and the selected model. The application follows the same logic: it saves the new measurement, updates the data version and calculates a new recommendation. It presents the result as one setting with a concise case basis; detailed model comparison and knowledge locations remain available for inspection. The interface therefore reflects the decision sequence established by the method.

## 5. Conclusion

A knowledge-guided intermediate-variable construction connects literature relationships with recorded laser settings through explicit fields, units and applicability conditions. Material-specific grouped validation then determines how those variables contribute to quality prediction. The fixed test comparison finds reduced simple-model RMSE in {improved} of {total} tasks, with substantial depth improvements for BF33, AlSiC and ZrO₂, alongside tasks where added variables do not help. These differences make the representation and its applicability more informative than a general claim of model superiority.

The recommendation rule reuses qualifying historical measurements before evaluating new settings. A target-matching score with a defined self-target value, a separate support-aware ranking loss and explicit equipment steps produce one candidate per decision. Appended machining feedback supplies the next measured input–output pair and updates subsequent recommendations. Together, the representation, validation and history-first decision rule provide a concrete connection between knowledge, prediction and practical parameter selection.

## References

[1] Ben-Yakar, A., and Byer, R. L. Femtosecond laser ablation properties of borosilicate glass. Journal of Applied Physics, 96, 5316–5323 (2004). https://doi.org/10.1063/1.1787145

[2] Žemaitis, A., Gaidys, M., Brikas, M., Gečys, P., Račiukaitis, G., and Gedvilas, M. Advanced laser scanning for highly-efficient ablation and ultrafast surface structuring: experiment and model. Scientific Reports, 8, 17376 (2018). https://doi.org/10.1038/s41598-018-35604-z

[3] Zhang, Z., Jia, M., Wang, L., et al. Physical model-guided machine learning for accelerating laser induced plasma micro-machining process optimization. Optics & Laser Technology, 183, 112402 (2025). https://doi.org/10.1016/j.optlastec.2024.112402
'''
    manuscript=manuscript.replace("A second difficulty arises at the decision stage.", "Related work also distinguishes prediction from sequential optimization. Li et al. compare KNN, SVR, random forest and XGBoost for predicting the heat-affected zone and material removal rate of femtosecond-machined CFRP, followed by parameter optimization [4]. Low et al. combine evolutionary selection with Bayesian acquisition to address constrained multi-objective experimental design [5]. The former emphasizes response approximation and optimized settings; the latter explicitly controls the selection of subsequent experiments. The present study focuses on the representation connecting knowledge to measured fields and the priority of existing satisfactory measurements. Model-family breadth provides a test of that representation rather than a contribution by itself.\n\nA second difficulty arises at the decision stage.")
    manuscript=manuscript.replace("No acquisition-function or Bayesian-optimization claim is required for this update rule.", "The next setting is selected after refitting with the newly available measurement.")
    manuscript=manuscript.replace("Response-specific counts are retained with the result tables rather than presented as a separate sample-count table.", "Response-specific development and test counts accompany the complete comparison results.")
    manuscript=manuscript.replace(comparison_table, "Table 3. Nominal targets, predicted responses and measured responses for the median-target ranking cases.\n\n"+comparison_table)
    manuscript += "\n[4] Li, K., Xu, J., Sun, S., et al. Prediction and optimization of femtosecond laser processing parameters for CFRP surface microgrooves based on machine learning. Optics and Lasers in Engineering, 198, 109547 (2026). https://doi.org/10.1016/j.optlaseng.2025.109547\n\n[5] Low, A. K. Y., Mekki-Berrada, F., Gupta, A., et al. Evolution-guided Bayesian optimization for constrained multi-objective optimization in self-driving labs. npj Computational Materials, 10, 104 (2024). https://doi.org/10.1038/s41524-024-01274-x\n"
    parts=re.split(r'(\$\$.*?\$\$)', manuscript, flags=re.S)
    for i in range(0,len(parts),2):
        parts[i]=re.sub(r'(?<![A-Za-z])(?:N_L/N_c|N_cum|N_L|N_c|I_A|t_j|d_j|y_j|ε_j)(?![A-Za-z])', lambda m:'$'+m.group(0).replace('ε_j',r'\varepsilon_j').replace('N_cum',r'N_{\mathrm{cum}}')+'$', parts[i])
    manuscript=''.join(parts)
    (OUT/(TITLE+".md")).write_text(manuscript,encoding="utf-8")
    complete=m.copy();complete.material=complete.material.map(lambda x:NAMES.get(x,x));complete.target=complete.target.map(TARGET)
    (OUT/"Supplementary Results.md").write_text("# Supplementary Results\n\nComplete fixed-group test results. RMSE and MAE are in μm.\n\n"+table(complete)+"\n\n## Scoring comparisons\n\n"+table(s.groupby('variant').agg(tasks=('satisfied','size'),satisfied=('satisfied','sum'),mean_normalized_error=('normalized_target_error','mean')).reset_index()),encoding="utf-8")
    print(OUT/(TITLE+".md"))

if __name__=="__main__":build()
