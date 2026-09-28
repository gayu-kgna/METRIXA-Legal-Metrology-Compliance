# Metrixa: SIH 2026 Live Demonstration Guide

> **Audience**: Evaluation Jury & Stakeholders  
> **Duration**: 3 to 5 Minutes  
> **Goal**: Demonstrate how Metrixa empowers Legal Metrology Officers to catch deceptive packaging, dual pricing, and missing statutory declarations with cryptographic legal defensibility.

---

## 1. Quick Access & Credentials

| Role | Username / Email | Password | Primary Purpose |
| :--- | :--- | :--- | :--- |
| **Legal Metrology Inspector** | `officer@metrixa.gov.in` | `Password@123` | Six-surface capture, OCR perception, inspection filing |
| **Senior Adjudicator** | `adjudicator@metrixa.gov.in`| `AdjudicatorPass123!` | Reviewing conflicts, manual overrides, dossier approvals |
| **System Administrator** | `admin@metrixa.gov.in` | `AdminPass123!` | Regulatory rule definitions, jurisdiction audits |

- **Web Application URL**: `http://localhost:5173`
- **Backend API Docs**: `http://127.0.0.1:8080/api/v1/docs`

---

## 2. 3-Minute Live Demonstration Script

```
Timeline:
[0:00 - 0:45] Intro & Dashboard: Real-time National Packaging Compliance Overview
[0:45 - 2:00] Act I: Intelligent Six-Surface Capture & Camera Guard
[2:00 - 3:15] Act II: Live Human Adjudication (Dual Pricing Conflict Resolution)
[3:15 - 4:15] Act III: The Product Ledger (Catching Clandestine Shrinkflation)
[4:15 - 5:00] Act IV: Cryptographic Legal PDF Dossier & Wrap-up
```

---

### Step 1: National Dashboard Overview [0:00 - 0:45]
1. Open `http://localhost:5173` and log in as `officer@metrixa.gov.in` / `Password@123`.
2. Point out the **Dashboard KPI Cards**:
   - Total Inspections, Compliance Rate, Pending Adjudication count.
   - **Talking Point**: *"Metrixa gives state controllers and central ministries real-time, tamper-evident visibility into retail packaging compliance under the Packaged Commodities Rules, 2011."*
3. Highlight the **Statutory Defect Breakdown Chart** showing non-compliant trends (e.g. missing Country of Origin on imported commodities, missing USP).

---

### Step 2: Six-Surface Capture & Camera Guard [0:45 - 2:00]
1. Click **New Inspection** in the navigation header.
2. Enter retail outlet details:
   - Retailer: `Reliance Smart Superstore, Dwarka`
   - Location: `New Delhi 110075`
3. Enter the Six-Surface Inspection Workspace:
   - Point out the 6 canonical spatial surfaces (`FRONT_PDP`, `BACK`, `LEFT`, `RIGHT`, `TOP`, `BOTTOM`).
4. **Key Safeguard Showcase (Camera Guard)**:
   - **Talking Point**: *"Notice the camera has NOT automatically turned on. Metrixa strictly enforces tactile user consent — preventing unintended battery drain, video stream leaks, or unauthorized surveillance."*
5. Click **[Camera HUD]** on the `Front (Principal Display Panel)` surface:
   - Point out the real-time target framing reticle and visual guidance.
   - Point out the seamless **[Upload Photo]** button for field environments where camera hardware is restricted.
6. Upload or capture the front panel:
   - Point out the instantaneous **SHA-256 cryptographic seal** calculated on the original image bytes.

---

### Step 3: Live Adjudication of Dual Pricing Conflict [2:00 - 3:15]
1. Navigate to **Inspections** and select the pending inspection for **"Royal Basmati Reserve"** (or use the one seeded by `seed_phase10_demo.py`).
2. Point out the statutory alert:
   - **Warning**: `Multiple conflicting MRP values detected: [180.0, 210.0]`.
   - **Legal Reference**: *Legal Metrology Act, 2009 - Rule 6(1)(da) (Single Retail Price Mandate).*
3. **Talking Point**: *"An unauthorized retail sticker was pasted over the factory-printed MRP of ₹180 with an inflated ₹210 price. Rather than having AI guess which price is correct, Metrixa automatically designates this as `CONFLICTING` and routes it to the officer's Adjudication Desk."*
4. Click **[Adjudicate Conflict]**:
   - Select the factory-printed declaration (₹180.00).
   - Enter officer rationale: `Factory print confirmed; retail sticker rejected under Rule 6(1)(da)`.
   - Click **[Confirm Adjudication]**.
5. Re-run rules: the inspection status updates deterministically to **COMPLIANT**.

---

### Step 4: Product Ledger & Shrinkflation Detection [3:15 - 4:15]
1. In the sidebar, navigate to **Product Ledger**.
2. Search for `Himalayan Gold` or GTIN `8901234567890`.
3. Open the **Product Detail & Timeline** view:
   - Observe **Version 1.0** (Net Quantity: `250 g`, MRP: `Rs. 250.00`).
   - Observe **Version 2.0** (Net Quantity: `220 g`, MRP: `Rs. 280.00`).
4. Click **[Compare Versions (Diff)]**:
   - The side-by-side diff highlights the sneaky **30g shrinkflation** and price hike:
     - `NET_QUANTITY: 250 g -> 220 g (DECREASED)`
     - `MRP: ₹ 250.00 -> ₹ 280.00 (INCREASED)`
     - `UNIT_SALE_PRICE: ₹ 1.00/g -> ₹ 1.27/g (+27% increase)`
5. **Talking Point**: *"Manufacturers frequently conceal shrinkflation by keeping the package dimensions identical while reducing contents. Metrixa's Product Ledger catches this automatically through persistent GTIN version diffing."*

---

### Step 5: Cryptographic Legal PDF Dossier [4:15 - 5:00]
1. Click **[Generate Legal Report]** (or view the pre-generated report).
2. Download or view the PDF dossier:
   - Point out the **Government of India / Legal Metrology header**.
   - Point out the statutory rule breakdown with exact citations (*Rule 6(1)(a)*, *Rule 6(1)(da)*, *Rule 7*).
   - Point out the **Cryptographic Evidence Seal (SHA-256)** and officer digital sign-off.
3. Conclude:
   - *"Metrixa bridges the gap between field inspection and court-admissible evidence, ensuring zero ambiguity and complete statutory compliance across India's packaging ecosystem."*

---

## 3. Judge FAQ & Ready Answers

**Q1: Why doesn't Metrixa let GPT-4 or an LLM evaluate whether the package is legal?**  
*Answer*: Under the Legal Metrology Act, 2009, legal non-compliance carries civil and criminal liabilities. AI perception models suffer from probabilistic hallucinations and non-determinism. Metrixa uses neural networks exclusively for perceptual OCR, but all legal decisions are made by our deterministic, transparent rule engine citing authoritative statutory provisions.

**Q2: What happens if an image is blurred or has severe glare?**  
*Answer*: Metrixa includes computer vision preprocessing (CLAHE, bilateral filtering, Laplacian variance blur estimation, and specular hotspot detection). Degraded images are marked `INDETERMINATE` rather than guessing, prompting the inspector with helpful framing guidance.

**Q3: How is evidence tampering prevented?**  
*Answer*: The exact raw bytes of every package surface are hashed with SHA-256 upon initial receipt and permanently stored in our immutable audit chain. No image can be cropped or altered without invalidating the cryptographic checksum.
