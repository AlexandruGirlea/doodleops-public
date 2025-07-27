# [DoodleOps](https://doodleops.com)

<img src="app_web/static/logo.png" alt="DoodleOps logo" width="180">

*Modular SaaS Platform & Starter Kit – maintained by [Alexandru Girlea](https://github.com/AlexandruGirlea)*

One‑person project supporting NGOs and individual learners.

If you would like to connect, you can do so via [LinkedIn](https://www.linkedin.com/in/alexandru-girlea/) or email: [alex@doodleops.com](mailto:alex@doodleops.com).

---

## ✨ Why choose DoodleOps

* **Complete SaaS backbone:** OAuth.2, SSO, username + password, API‑key auth, full Stripe billing, admin dashboard.  
* **GenAI‑ready:** ChatGPT plugin integration, WhatsApp bot demo powered by LangGraph.  
* **Cloud‑agnostic:** containerised; runs today on Google Cloud and deploys the same to AWS, Azure or on‑prem.  
* **Infrastructure‑as‑Code:** Terraform modules and Cloud.Build CI/CD pipelines included. 
* **Live demo:** <https://doodleops.com>
---

## 💼 Licensing at a glance

| Audience             | Rights                                          | Cost                                                                                   |
|----------------------|-------------------------------------------------|----------------------------------------------------------------------------------------|
| Learners & hobbyists | Non‑production use (≤ 25 users)                 | **Free**                                                                               |
| Recognised NGOs      | Full production use (logo attribution required) | **Free**                                                                               |
| Startups             | Production use                                  | **Startups** can trade **3% future gross revenue** (up to €50.000) for an OEM licence  |
| Businesses           | Production use                                  | One‑time licence: Training €3.000 · Growth €12.000 · Enterprise €25.000 · OEM €50.000  |

*Full terms:* see [**LICENSE**](LICENSE.md) (BSL 1.1) and [**COMMERCIAL_LICENSE.md**](COMMERCIAL_LICENSE.md).

---

## 🤝 Community & support

* Private **Slack** for licensees and NGOs (1 named contact for Training/Growth, 3 for Enterprise, 5 for OEM; **max.5 support tickets per month**; response 2‑3 business days).  
* Feature requests & bug reports: open a GitHub issue **or** email [alex@doodleops.com](mailto:alex@doodleops.com).  
* If this repo helps you, please **star ★** it!

---

## 🛠️ Project structure

***Production Network Topology***

```mermaid
flowchart LR
    subgraph Internet
        A[Internet<br/>Client]
    end

    A -->|HTTPS| B[Cloudflare]
    B --> C[GCP<br/>Load&nbsp;Balancer]

    subgraph DMZ["Public&nbsp;Zone"]
        direction LR
        D[Web&nbsp;Service]:::public
        E[API&nbsp;Service]:::public
        F[GCP&nbsp;CDN]:::public
        D --> E
        D --> F
    end

    C --> D
    C --> E

    subgraph VPC["Private&nbsp;VPC"]
        direction TB
        G[AI&nbsp;Service]
        H[PDF&nbsp;Service]
        I[Excel&nbsp;Service]
        J[Image&nbsp;Service]
        K[ePub&nbsp;Service]
    end

    E --> G
    E --> H
    E --> I
    E --> J
    E --> K

    classDef public fill:#dfe7fd,stroke:#3b82f6,stroke-width:2px;
```
***How Users Connect to DoodleOps***
```mermaid
flowchart TD
    user[User / Client]

    subgraph Entry_Points
        WebUI["Web UI<br>🔒 Google SSO / Password"]
        APIKey["Custom API Endpoint<br>🔑 API Key"]
        WhatsApp["WhatsApp Bot<br>🔒 Twilio Auth"]
        ChatGPT["ChatGPT Plugin (DoodleOps PDF)<br>🔒 OAuth"]
    end

    subgraph Core
        DOps[DoodleOps Core Services]
    end

    user --> WebUI
    user --> APIKey
    user --> WhatsApp
    user --> ChatGPT

    WebUI --> DOps
    APIKey --> DOps
    WhatsApp --> DOps
    ChatGPT --> DOps
```

***Example Stripe Billing Flow***
```mermaid
%%{init: {'flowchart': {'title': 'Stripe Billing Options for DoodleOps'}}}%%
flowchart TB
    direction LR

    U["User<br/>Checkout<br/>(Stripe)"]

    U --> A1[[One-Time<br/>Credit Packs]]
    U --> B1[[Subscriptions]]
    U --> C1[[Enterprise<br/>Pay-as-You-Go]]

    %% ───────── Credit Packs ─────────
    subgraph "Credit Packs (expire after X days)"
        A2["$5 ⇒ 400 credits"]
        A3["$10 ⇒ 1 000 credits"]
        A4["$20 ⇒ 2 200 credits"]
    end
    A1 --> A2 & A3 & A4

    %% ───────── Subscriptions ─────────
    subgraph "Base & Pro Tiers"
        direction TB
        B2["Base<br/>550 credits / mo"]
        B3["Pro<br/>1 100 credits / mo"]
        class B2 tierBase
        class B3 tierPro
    end
    B1 --> B2 & B3

    Bnote["Monthly or yearly billing<br/>Unused credits roll over<br/>until subscription ends"]
    B1 --> Bnote

    %% ───────── Enterprise ─────────
    subgraph "Metered Billing"
        C2["Cost = credits_used × $0.01<br/>+ flat $20 / month"]
        class C2 tierEnt
    end
    C1 --> C2

    %% Styles
    classDef tierBase fill:#fef9c3,stroke:#f59e0b,stroke-width:2px;
    classDef tierPro  fill:#fee2e2,stroke:#ef4444,stroke-width:2px;
    classDef tierEnt  fill:#e0f2fe,stroke:#0284c7,stroke-width:2px;
    classDef note     fill:#ffffff,stroke-dasharray:3 3,color:#6b7280,font-style:italic;
    class Bnote note
```
***WhatsApp → LangGraph Hierarchical Agents Workflow***
```mermaid
%%{init: {'flowchart': {'title': 'WhatsApp → LangGraph Hierarchical Agents Workflow'}}}%%
flowchart TB
    direction TB

    A["Incoming WhatsApp<br/>Message"]
    R["WhatsApp<br/>Response"]

    B{"User authorised<br/>AND<br/>has credits?"}
    C["Reject & prompt<br/>to top-up / sign-in"]

    D{"Clear<br/>conversation history?"}
    E["Conversation cleared<br/>and user notified"]

    F["Detect user<br/>language"]
    G["Load conversation<br/>history"]

    H["LangGraph<br/>Intent Router"]
    I["Specialised<br/>Router"]

    %% ───────── Capability Nodes ─────────
    subgraph Caps["Capability Nodes"]
        direction TB
        J["Multimodal<br/>Handler"]
        K["AI Translation<br/>Handler"]
        L["Web Search<br/>(Perplexity / Google / YouTube)"]
        M["Stock & Finance<br/>Handler"]
        N["Other<br/>Handlers …"]
    end

    %% ───────── Core flow ─────────
    A --> B
    B -- No --> C --> R
    B -- Yes --> D
    D -- Yes --> E --> R
    D -- No --> F --> G --> H --> I
    I --> J
    I --> K
    I --> L
    I --> M
    I --> N
    Caps --> R
```

## 👐 Contributing
* **Contributions welcome!** By submitting code you agree to the DoodleOps CLA
  – see [CONTRIBUTING.md](CONTRIBUTING.md) for the legal details.

© 2025 Alexandru Girlea.