# 🏦 TaxMaximizer Wizard - ITR Return filing & Tax Optimizer

TaxMaximizer Wizard is a professional, interactive Streamlit web application designed to compute, optimize, and generate e-filing packages for Indian Income Tax Returns. It performs real-time comparisons between the **Old and New Tax Regimes** using the latest **Union Budget (FY 2025-26 / AY 2026-27)** tax slabs and deductions.

---

## 🌟 Key Features

1. **📄 Automated PDF Parsing & Auto-Fill**:
   - Upload your official **Form 16 Part B**, **Form 16A**, or **Form 16B** TDS certificates in PDF format.
   - The app automatically extracts gross salary, HRA/exempt allowances, professional tax, Section 80C/80D investments, home loan interest, and NPS contributions, pre-populating the wizard tabs.

2. **⚙️ Robust Wizard Interface**:
   - Structured step-by-step layout split into Personal & Bank info, Income Sources, Documents Upload, Deductions Matrix, and Tax Summary.
   - Designed with a decoupled state-persistence system to prevent Streamlit widget value reset issues when navigating back and forth.

3. **⚖️ Real-Time Tax Regime Engine**:
   - **New Tax Regime Slabs (FY 2025-26)**:
     - Up to ₹4,0,000: Nil
     - ₹4,00,001 – ₹8,00,000: 5%
     - ₹8,00,001 – ₹12,00,000: 10%
     - ₹12,00,001 – ₹16,00,000: 15%
     - ₹16,00,001 – ₹20,00,000: 20%
     - ₹20,00,001 – ₹24,00,000: 25%
     - Above ₹24,00,000: 30%
   - **Enhanced Section 87A Rebate**: Full tax rebate (up to ₹60,000) for taxable income up to ₹12,00,000 (effective tax-free threshold of ₹12.75 Lakhs for salaried individuals with the ₹75,000 Standard Deduction).
   - **Marginal Relief**: Dynamically caps New Regime tax liability for incomes slightly above ₹12 Lakhs.
   - **Old Tax Regime**: Fully supports standard deductions (₹50,000), senior citizen exemption limits (₹3 Lakhs), and custom Chapter VI-A deductions.

4. **📥 Direct e-Filing Schema Generator**:
   - Generates a structured filing payload JSON file compatible with the official **Indian Income Tax Department ([incometax.gov.in](https://www.incometax.gov.in))** upload utilities. You can download the JSON file and upload it directly to pre-fill your returns.

5. **🔍 Filing Validation Checklist**:
   - Displays real-time validation checks for mandatory requirements:
     - PAN number formatting (validation for `ABCDE1234F` structure)
     - Aadhaar number formatting (validation for 12 digits)
     - Bank account verification (verifies IFSC formats and account presence for tax refunds)
     - Income presence (alerts for zero salary filing)

6. **💡 Actionable Tax Savings Advice**:
   - Recommends customized investments to minimize liability and maximize refund amounts (such as 80C gaps, 80D limits, and Section 80CCD NPS routes).

---

## 🛠️ Getting Started

### Prerequisites
- Python 3.10 or higher.

### Installation & Run
1. Clone the repository to your local system:
   ```bash
   git clone https://github.com/your-username/ITR-RETURN.git
   cd ITR-RETURN
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Launch the application:
   ```bash
   streamlit run app.py
   ```

4. Open the local address in your web browser:
   [http://localhost:8501](http://localhost:8501)

---

## 📁 Repository Structure

- `app.py`: Core application code containing the PDF parsing regex engines, detailed tax computation formulas, state controllers, and Plotly graphics.
- `requirements.txt`: Dependencies lists (`streamlit`, `pypdf`, `plotly`).
- `README.md`: General documentation file.
