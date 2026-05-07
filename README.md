# 🚀 Consumer360 – Customer Segmentation & Lifetime Value Engine

<p align="center">
  <img src="https://readme-typing-svg.herokuapp.com?color=00F7FF&size=28&center=true&vCenter=true&width=900&lines=Retail+Analytics+System;RFM+Segmentation+%7C+Cohort+Analysis;Market+Basket+%7C+CLV+Modeling;Power+BI+Dashboard+%7C+Customer+Intelligence" />
</p>

---

## 📊 Overview

**Consumer360** is a production-grade retail analytics system designed to transform raw transactional data into actionable customer intelligence.

It enables businesses to:

* 🐋 Identify high-value customers (**Whales**)
* ⚠️ Detect churn-risk customers
* 📈 Understand behavioral and lifecycle patterns
* 🎯 Drive data-driven marketing strategies

---

## 🧠 Use Case (Production Scenario)

A major retail chain is experiencing significant customer churn.

The objective is to build a **scalable analytical framework** that:

* Segments customers using **RFM (Recency, Frequency, Monetary)**
* Identifies high-value vs at-risk users
* Enables targeted retention and engagement strategies

---

## ✨ Product Features

### 📊 Core Analytics

* Sales Trends Over Time
* Revenue by Geographical Region
* Top 10 Bestselling Products

---

### ⚡ Advanced Intelligence

#### 🔹 RFM Segmentation

* Algorithmic scoring (1–5 scale)
* Customer classification:

  * Champions
  * Loyal Customers
  * At Risk
  * Lost Customers

---

#### 🔹 Cohort Analysis

* Retention tracking across time
* Customer lifecycle behavior
* Answers:

  > Do holiday-acquired customers retain better than others?

---

#### 🔹 Market Basket Analysis

* Association Rule Mining (Apriori / FP-Growth)
* Product affinity detection
* Example:

  > Customers buying Product A also buy Product B

---

#### 🔹 Customer Lifetime Value (CLV)

* Predict future purchase behavior
* Estimate long-term customer value using probabilistic models

---

## ⚙️ Tech Stack

<p align="center">

![SQL](https://img.shields.io/badge/SQL-CC2927?style=for-the-badge\&logo=microsoftsqlserver)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge\&logo=python\&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-013243?style=for-the-badge\&logo=numpy)
![Pandas](https://img.shields.io/badge/Pandas-150458?style=for-the-badge\&logo=pandas)
![Power BI](https://img.shields.io/badge/PowerBI-F2C811?style=for-the-badge\&logo=powerbi)

</p>

---

## 🔄 System Pipeline

```mermaid
graph LR
A[Raw Retail Data] --> B[ELT Processing]
B --> C[SQL Database]
C --> D[RFM Segmentation]
D --> E[Cohort Analysis]
E --> F[Market Basket Analysis]
F --> G[CLV Modeling]
G --> H[Power BI Dashboard]
```

---

## 📊 Dashboard Preview

<p align="center">
  <img src="dashboards/dashboard_preview.png" width="70%" />
</p>

---

## 📁 Project Structure

```
Consumer360-Customer-Analytics/
│
├── dashboards/
│   ├── Consumer 360.pbix
│   └── Consumer 360 - BI dashboard.pdf
│
├── datasets/
│   └── dataset (CSV and DB files).zip
│
├── notebooks/
│   ├── ELT processing.ipynb
│   ├── LOAD TO SQL.ipynb
│   ├── RFM + SEGEMENTATION.ipynb
│   ├── COHORT ANALYSIS.ipynb
│   └── MARKET BASKET ANALYSIS.ipynb
│
├── README.md
└── MIT LICENSE
```

---

## 📌 Workflow

1. Data Extraction & Cleaning (ELT)
2. Load structured data into SQL
3. Perform RFM Segmentation
4. Conduct Cohort Retention Analysis
5. Generate Market Basket Rules
6. Build Power BI Dashboard

---

## 🧪 Key Concepts

* RFM Segmentation
* Cohort Analysis
* Association Rule Mining
* Customer Lifetime Value (CLV)
* Behavioral Analytics

---

## 🚀 Key Insights

* Customer retention drops sharply after the first month (early churn)
* High-value customers drive a disproportionate share of revenue
* Retention stabilizes after initial lifecycle stage
* Product associations enable effective cross-selling strategies

---

## 🔮 Future Scope

* ML-based churn prediction
* Recommendation systems
* Real-time streaming analytics
* Cloud deployment (AWS / GCP)

---

## 👩‍💻 Author

**Riddhima**
B.Tech CSE (Data Science)
Aspiring Data Analyst / ML Engineer

---

<p align="center">
✨ Transforming Data into Customer Intelligence ✨
</p>
