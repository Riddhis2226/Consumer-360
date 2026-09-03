<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0F2027,50:2C5364,100:00F7FF&height=220&section=header&text=Consumer360&fontSize=60&fontColor=ffffff&animation=fadeIn&fontAlignY=38&desc=Customer%20Segmentation%20%26%20Lifetime%20Value%20Engine&descAlignY=58&descSize=20" width="100%"/>

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=24&duration=2500&pause=800&color=00F7FF&center=true&vCenter=true&width=800&lines=RFM+Segmentation+%E2%80%A2+Cohort+Analysis;Market+Basket+Mining+%E2%80%A2+CLV+Modeling;SQL+%E2%80%A2+Python+%E2%80%A2+Power+BI+%E2%80%A2+Production-Ready" />

<br/>

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![SQL](https://img.shields.io/badge/SQL-CC2927?style=for-the-badge&logo=microsoftsqlserver&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-013243?style=for-the-badge&logo=numpy&logoColor=white)
![Power BI](https://img.shields.io/badge/Power%20BI-F2C811?style=for-the-badge&logo=powerbi&logoColor=black)
![Jupyter](https://img.shields.io/badge/Jupyter-F37626?style=for-the-badge&logo=jupyter&logoColor=white)

<img src="https://img.shields.io/badge/status-production--ready-brightgreen?style=flat-square"/>
<img src="https://img.shields.io/badge/license-MIT-blue?style=flat-square"/>
<img src="https://img.shields.io/badge/domain-Retail%20Analytics-orange?style=flat-square"/>
<img src="https://img.shields.io/github/last-commit/YOUR-USERNAME/Consumer360-Customer-Analytics?style=flat-square&color=00F7FF"/>

</div>

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.gif" width="100%">

## 🎯 What This Is

A retail chain is bleeding customers and doesn't know why. **Consumer360** turns raw POS/transaction logs into a decision-ready customer intelligence layer — who's about to churn, who's secretly a whale, and what to sell them next — packaged end-to-end from raw CSV to a live Power BI dashboard.

<table align="center">
<tr>
<td align="center" width="25%">

### 🐋
**Whale Detection**
Surface the top-value customers driving disproportionate revenue

</td>
<td align="center" width="25%">

### ⚠️
**Churn Signals**
Flag at-risk and lapsed customers before they're gone

</td>
<td align="center" width="25%">

### 📈
**Lifecycle Insight**
Cohort retention curves across acquisition periods

</td>
<td align="center" width="25%">

### 🎯
**Growth Levers**
Product-affinity rules for cross-sell / bundling

</td>
</tr>
</table>

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.gif" width="100%">

## 🔄 Pipeline

```mermaid
%%{init: {'theme':'dark', 'themeVariables': {'primaryColor':'#0F2027','primaryTextColor':'#00F7FF','primaryBorderColor':'#00F7FF','lineColor':'#2C5364','secondaryColor':'#150458','tertiaryColor':'#1a1a2e'}}}%%
flowchart LR
    A(["🗂️ Raw Retail Data"]) --> B["⚙️ ELT Processing"]
    B --> C[("🗄️ SQL Database")]
    C --> D["🎯 RFM Segmentation"]
    D --> E["📊 Cohort Analysis"]
    E --> F["🛒 Market Basket Mining"]
    F --> G["💰 CLV Modeling"]
    G --> H(["📈 Power BI Dashboard"])

    style A fill:#0F2027,stroke:#00F7FF,color:#fff
    style H fill:#0F2027,stroke:#00F7FF,color:#fff
```

## ⚡ Core Modules

<details open>
<summary><b>🔹 RFM Segmentation</b></summary>
<br/>

Algorithmic 1–5 scoring across **Recency, Frequency, Monetary** dimensions, mapped into actionable tiers:

| Tier | Meaning |
|---|---|
| 🏆 Champions | Bought recently, often, and big |
| 💎 Loyal Customers | Consistent repeat buyers |
| ⚠️ At Risk | Used to buy often, gone quiet |
| ☠️ Lost | Long inactive, low value |

</details>

<details>
<summary><b>🔹 Cohort Analysis</b></summary>
<br/>

Tracks retention by acquisition month to answer questions like:
> *Do holiday-acquired customers retain better than customers acquired in an average month?*

Outputs a retention heatmap across the customer lifecycle.

</details>

<details>
<summary><b>🔹 Market Basket Analysis</b></summary>
<br/>

Apriori / FP-Growth association-rule mining over transaction baskets to surface rules like:
> *Customers who buy Product A are significantly more likely to also buy Product B.*

Powers cross-sell and bundling recommendations.

</details>

<details>
<summary><b>🔹 Customer Lifetime Value (CLV)</b></summary>
<br/>

Probabilistic modeling to project forward purchase behavior and estimate long-term customer value — used to prioritize retention spend where it actually pays off.

</details>

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.gif" width="100%">

## 📊 Dashboard

<div align="center">
<img src="dashboards/Screenshot 2026-06-03 175821.png" width="90%"/>
<br/><br/>
<img src="dashboards/Screenshot 2026-06-03 175841.png" width="90%"/>
<br/><br/>
<img src="dashboards/Screenshot 2026-06-03 175858.png" width="90%"/>
</div>

## 🧪 Key Insights

- 📉 **Early churn is the biggest leak** — retention drops sharply within the first month post-acquisition
- 💰 **Revenue is concentrated** — a small slice of "Champion" customers drives a disproportionate share of total revenue
- 📈 **Retention stabilizes** after the initial lifecycle stage, meaning early intervention matters most
- 🛒 **Product affinities are actionable** — clear cross-sell rules emerge from basket analysis

## 📁 Project Structure

```
Consumer360-Customer-Analytics/
│
├── 📊 dashboards/
│   ├── Consumer 360.pbix
│   ├── Consumer 360 - BI dashboard.pdf
│   └── *.png
│
├── 🗃️ datasets/
│   └── dataset (CSV + DB files).zip
│
├── 📓 notebooks/
│   ├── ELT processing.ipynb
│   ├── LOAD TO SQL.ipynb
│   ├── RFM + SEGMENTATION.ipynb
│   ├── COHORT ANALYSIS.ipynb
│   └── MARKET BASKET ANALYSIS.ipynb
│
├── README.md
└── LICENSE (MIT)
```

## 🔮 Future Scope

- 🤖 ML-based churn prediction
- 🎯 Recommendation engine
- ⏱️ Real-time streaming analytics
- ☁️ Cloud deployment (AWS / GCP)

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.gif" width="100%">

<div align="center">

### 🛠️ Built With

<img src="https://skillicons.dev/icons?i=python,postgres,git,powerbi&theme=dark" />

<br/><br/>

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:00F7FF,100:0F2027&height=100&section=footer" width="100%"/>

**⭐ If this project helped you, consider starring the repo!**

</div>
