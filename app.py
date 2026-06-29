import streamlit as st
from pypdf import PdfReader
import re
import datetime
import json
import plotly.graph_objects as go

# --- CONFIGURATION & THEME ---
st.set_page_config(page_title="TaxMaximizer Wizard", page_icon="🏦", layout="wide")

# Custom CSS for polished, colorful tab styling and navigation buttons
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        html, body, [data-testid="stAppViewContainer"] {
            font-family: 'Inter', sans-serif;
            background-color: #fcfdfd;
        }
        .wizard-title {
            font-size: 2.5rem;
            font-weight: 700;
            color: #0f172a;
            margin-bottom: 0.2rem;
        }
        .wizard-subtitle {
            font-size: 1rem;
            color: #64748b;
            margin-bottom: 1.5rem;
        }
        /* Make tab buttons and action buttons uniform in height and spacing */
        .stButton > button {
            min-height: 55px !important;
            height: 55px !important;
            font-size: 0.95rem !important;
            font-weight: 600 !important;
            border-radius: 8px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }
        /* Custom layout accents */
        .summary-card {
            padding: 1.2rem;
            border-radius: 10px;
            margin-bottom: 1rem;
            color: #ffffff;
            font-weight: 600;
        }
        .rec-card {
            background-color: #f8fafc;
            border-left: 5px solid #10b981;
            padding: 1rem;
            border-radius: 6px;
            margin-bottom: 10px;
        }
    </style>
""", unsafe_allow_html=True)

# --- HELPER PARSING CODES ---
def extract_text_from_pdf(uploaded_file):
    try:
        reader = PdfReader(uploaded_file)
        return "".join([p.extract_text() or "" for p in reader.pages])
    except:
        return ""

def parse_form16_text(text):
    parsed = {}
    
    # 1. Gross Salary
    gross_patterns = [
        r'17\(1\)\s*\(a\)?\s*([\d,]+(?:\.\d{1,2})?)',
        r'Salary\s+as\s+per\s+provisions\s+contained\s+in\s+section\s+17\(1\).*?([\d,]+(?:\.\d{1,2})?)',
        r'Salary\s+as\s+per\s+provisions\s+of\s+section\s+17\(1\).*?([\d,]+(?:\.\d{1,2})?)',
        r'Income\s+under\s+the\s+head\s+Salaries.*?([\d,]+(?:\.\d{1,2})?)',
        r'Gross\s+Salary.*?([\d,]+(?:\.\d{1,2})?)',
        r'Gross\s+Total\s+Income.*?([\d,]+(?:\.\d{1,2})?)'
    ]
    for p in gross_patterns:
        match = re.search(p, text, re.IGNORECASE | re.DOTALL)
        if match:
            parsed['gross'] = float(match.group(1).replace(',', ''))
            break
            
    # 2. TDS
    tds_patterns = [
        r'(?:Total\s+TDS|Tax\s+Deposited|Total\s+Tax\s+Deducted|Tax\s+deducted\s+at\s+source|TDS\s+Deposited).*?([\d,]+(?:\.\d{1,2})?)'
    ]
    for p in tds_patterns:
        matches = re.findall(p, text, re.IGNORECASE)
        if matches:
            parsed['tds_pool'] = max([float(v.replace(',', '')) for v in matches])
            break

    # 3. 80C
    c_patterns = [
        r'Section\s+80C.*?([\d,]+(?:\.\d{1,2})?)',
        r'Sec\s+80C.*?([\d,]+(?:\.\d{1,2})?)',
        r'80C.*?([\d,]+(?:\.\d{1,2})?)'
    ]
    for p in c_patterns:
        match = re.search(p, text, re.IGNORECASE | re.DOTALL)
        if match:
            parsed['ded_80c_elss_ppf'] = float(match.group(1).replace(',', ''))
            break

    # 4. 80D
    d_patterns = [
        r'Section\s+80D.*?([\d,]+(?:\.\d{1,2})?)',
        r'Sec\s+80D.*?([\d,]+(?:\.\d{1,2})?)',
        r'80D.*?([\d,]+(?:\.\d{1,2})?)'
    ]
    for p in d_patterns:
        match = re.search(p, text, re.IGNORECASE | re.DOTALL)
        if match:
            parsed['ded_80d_self'] = float(match.group(1).replace(',', ''))
            break

    # 5. HRA
    hra_patterns = [
        r'10\(13A\).*?([\d,]+(?:\.\d{1,2})?)',
        r'House\s+Rent\s+Allowance.*?([\d,]+(?:\.\d{1,2})?)',
        r'Allowance\s+in\s+respect\s+of\s+house\s+rent.*?([\d,]+(?:\.\d{1,2})?)',
        r'HRA.*?([\d,]+(?:\.\d{1,2})?)'
    ]
    for p in hra_patterns:
        match = re.search(p, text, re.IGNORECASE | re.DOTALL)
        if match:
            parsed['exempt_allowances'] = float(match.group(1).replace(',', ''))
            break

    # 6. Home Loan Interest (Section 24)
    loan_patterns = [
        r'24\(b\).*?([\d,]+(?:\.\d{1,2})?)',
        r'Section\s+24\(b\).*?([\d,]+(?:\.\d{1,2})?)',
        r'Interest\s+on\s+borrowed\s+capital.*?([\d,]+(?:\.\d{1,2})?)',
        r'Interest\s+payable\s+on\s+borrowed\s+capital.*?([\d,]+(?:\.\d{1,2})?)',
        r'Interest\s+on\s+house\s+property.*?([\d,]+(?:\.\d{1,2})?)'
    ]
    for p in loan_patterns:
        match = re.search(p, text, re.IGNORECASE | re.DOTALL)
        if match:
            parsed['hp_loan_interest_self'] = float(match.group(1).replace(',', ''))
            break

    # 7. NPS Employer Component (80CCD(2))
    nps_patterns = [
        r'80CCD\(2\).*?([\d,]+(?:\.\d{1,2})?)',
        r'Section\s+80CCD\(2\).*?([\d,]+(?:\.\d{1,2})?)',
        r'Sec\s+80CCD\(2\).*?([\d,]+(?:\.\d{1,2})?)'
    ]
    for p in nps_patterns:
        match = re.search(p, text, re.IGNORECASE | re.DOTALL)
        if match:
            parsed['nps_emp'] = float(match.group(1).replace(',', ''))
            break

    # 8. NPS Self Component (80CCD(1B))
    nps1b_patterns = [
        r'80CCD\(1B\).*?([\d,]+(?:\.\d{1,2})?)',
        r'Section\s+80CCD\(1B\).*?([\d,]+(?:\.\d{1,2})?)'
    ]
    for p in nps1b_patterns:
        match = re.search(p, text, re.IGNORECASE | re.DOTALL)
        if match:
            parsed['ded_80ccd1b'] = float(match.group(1).replace(',', ''))
            break

    # 9. Professional Tax
    pt_patterns = [
        r'Professional\s+Tax.*?([\d,]+(?:\.\d{1,2})?)',
        r'Tax\s+on\s+Employment.*?([\d,]+(?:\.\d{1,2})?)'
    ]
    for p in pt_patterns:
        match = re.search(p, text, re.IGNORECASE | re.DOTALL)
        if match:
            parsed['professional_tax'] = float(match.group(1).replace(',', ''))
            break

    # 10. Savings Interest (Other Income)
    savings_patterns = [
        r'Savings\s+Interest.*?([\d,]+(?:\.\d{1,2})?)',
        r'Interest\s+on\s+Savings.*?([\d,]+(?:\.\d{1,2})?)'
    ]
    for p in savings_patterns:
        match = re.search(p, text, re.IGNORECASE | re.DOTALL)
        if match:
            parsed['other_inc_savings'] = float(match.group(1).replace(',', ''))
            break

    # 11. EPF u/s 80C
    epf_patterns = [
        r'EPF.*?([\d,]+(?:\.\d{1,2})?)',
        r'Provident\s+Fund.*?([\d,]+(?:\.\d{1,2})?)'
    ]
    for p in epf_patterns:
        match = re.search(p, text, re.IGNORECASE | re.DOTALL)
        if match:
            parsed['ded_80c_epf'] = float(match.group(1).replace(',', ''))
            break

    return parsed

def parse_form16a_16b_text(text):
    parsed = {}
    
    # 1. TDS Deposited/Deducted
    tds_patterns = [
        r'Total\s+tax\s+(?:deducted|deposited).*?([\d,]+(?:\.\d{1,2})?)',
        r'Amount\s+of\s+tax\s+deducted.*?([\d,]+(?:\.\d{1,2})?)',
        r'Tax\s+Deducted\s+at\s+Source.*?([\d,]+(?:\.\d{1,2})?)'
    ]
    for p in tds_patterns:
        match = re.search(p, text, re.IGNORECASE | re.DOTALL)
        if match:
            parsed['tds_pool'] = float(match.group(1).replace(',', ''))
            break
            
    # 2. Amount Paid/Credited (Other Income - FD/Deposits interest or transaction value)
    amount_patterns = [
        r'Total\s+amount\s+paid\s*/\s*credited.*?([\d,]+(?:\.\d{1,2})?)',
        r'Amount\s+paid\s*/\s*credited.*?([\d,]+(?:\.\d{1,2})?)',
        r'Gross\s+Amount\s+Paid.*?([\d,]+(?:\.\d{1,2})?)',
        r'Transaction\s+Value.*?([\d,]+(?:\.\d{1,2})?)',
        r'Purchase\s+Price.*?([\d,]+(?:\.\d{1,2})?)'
    ]
    for p in amount_patterns:
        match = re.search(p, text, re.IGNORECASE | re.DOTALL)
        if match:
            parsed['other_income'] = float(match.group(1).replace(',', ''))
            break
            
    return parsed

def calculate_tax_detailed(regime, is_senior, gross_sal, exempt_allowances, professional_tax,
                           hp_rent, hp_taxes, hp_loan_self, hp_loan_letout,
                           inc_savings, inc_deposits, inc_dividends, inc_misc,
                           ded_80c, ded_80d_self, ded_80d_parents, ded_80ccd1b, nps_emp, ded_80e, ded_80g):
    
    # 1. Income from Salary
    if regime == "OLD":
        net_salary = max(0.0, gross_sal - exempt_allowances)
        salary_standard_deduction = 50000.0 if net_salary > 0 else 0.0
        income_salary = max(0.0, net_salary - salary_standard_deduction - professional_tax)
    else:
        # New regime (FY 2025-26 / AY 2026-27): standard deduction is 75,000
        salary_standard_deduction = 75000.0 if gross_sal > 0 else 0.0
        income_salary = max(0.0, gross_sal - salary_standard_deduction)
        
    # 2. Income from House Property
    nav_letout = max(0.0, hp_rent - hp_taxes)
    std_ded_letout = 0.3 * nav_letout
    income_hp_letout = nav_letout - std_ded_letout - hp_loan_letout
    
    if regime == "OLD":
        income_hp_self = -min(200000.0, hp_loan_self)
    else:
        income_hp_self = 0.0
        
    income_house_property = income_hp_letout + income_hp_self
    
    hp_loss_to_set_off = 0.0
    if income_house_property < 0:
        if regime == "OLD":
            hp_loss_to_set_off = max(-200000.0, income_house_property)
        else:
            hp_loss_to_set_off = 0.0
    else:
        hp_loss_to_set_off = income_house_property
        
    # 3. Income from Other Sources
    income_other = inc_savings + inc_deposits + inc_dividends + inc_misc
    
    # 4. Gross Total Income (GTI)
    gti = income_salary + hp_loss_to_set_off + income_other
    
    # 5. Deductions (Chapter VI-A)
    total_deductions = 0.0
    if regime == "OLD":
        allowed_80c = min(150000.0, ded_80c)
        
        limit_80d_self = 50000.0 if is_senior else 25000.0
        limit_80d_parents = 50000.0
        allowed_80d = min(limit_80d_self, ded_80d_self) + min(limit_80d_parents, ded_80d_parents)
        
        allowed_80ccd1b = min(50000.0, ded_80ccd1b)
        allowed_nps_emp = min(0.1 * gross_sal, nps_emp)
        allowed_80e = ded_80e
        allowed_80g = min(0.1 * gti, ded_80g)
        
        if is_senior:
            allowed_80ttb = min(50000.0, inc_savings + inc_deposits)
            allowed_80tta = 0.0
        else:
            allowed_80tta = min(10000.0, inc_savings)
            allowed_80ttb = 0.0
            
        total_deductions = allowed_80c + allowed_80d + allowed_80ccd1b + allowed_nps_emp + allowed_80e + allowed_80g + allowed_80tta + allowed_80ttb
    else:
        allowed_nps_emp = min(0.1 * gross_sal, nps_emp)
        total_deductions = allowed_nps_emp
        
    # 6. Taxable Income
    taxable_income = max(0.0, gti - total_deductions)
    
    # 7. Tax Slabs
    tax = 0.0
    if regime == "NEW":
        # FY 2025-26 Slabs:
        # Up to 4L: Nil
        # 4L - 8L: 5%
        # 8L - 12L: 10%
        # 12L - 16L: 15%
        # 16L - 20L: 20%
        # 20L - 24L: 25%
        # Above 24L: 30%
        if taxable_income > 400000:
            tax += min(taxable_income - 400000, 400000) * 0.05
        if taxable_income > 800000:
            tax += min(taxable_income - 800000, 400000) * 0.10
        if taxable_income > 1200000:
            tax += min(taxable_income - 1200000, 400000) * 0.15
        if taxable_income > 1600000:
            tax += min(taxable_income - 1600000, 400000) * 0.20
        if taxable_income > 2000000:
            tax += min(taxable_income - 2000000, 400000) * 0.25
        if taxable_income > 2400000:
            tax += (taxable_income - 2400000) * 0.30
            
        # Rebate 87A: If taxable income <= 12L, rebate up to ₹60,000 (100% tax rebate)
        if taxable_income <= 1200000:
            tax = 0.0
        # Marginal Relief for income slightly above 12L
        elif taxable_income > 1200000:
            excess_income = taxable_income - 1200000
            if tax > excess_income:
                tax = excess_income
    else:
        # Old Regime Slabs
        exemption_limit = 300000.0 if is_senior else 250000.0
        
        if taxable_income > exemption_limit:
            tax += min(taxable_income - exemption_limit, 500000.0 - exemption_limit) * 0.05
        if taxable_income > 500000:
            tax += min(taxable_income - 500000, 500000) * 0.20
        if taxable_income > 1000000:
            tax += (taxable_income - 1000000) * 0.30
            
        if taxable_income <= 500000:
            tax = 0.0
            
    # 8. Health & Education Cess
    cess = round(tax * 0.04, 2)
    total_tax = round(tax + cess, 2)
    
    return {
        "net_salary": income_salary,
        "hp_income": hp_loss_to_set_off,
        "other_sources": income_other,
        "gti": gti,
        "deductions": total_deductions,
        "taxable_income": taxable_income,
        "tax_before_cess": tax,
        "cess": cess,
        "total_tax": total_tax
    }

# --- TAX OPTIMIZATION ENGINE ---
def generate_recommendations(is_senior, gross_sal, exempt_allowances, professional_tax,
                             hp_rent, hp_taxes, hp_loan_self, hp_loan_letout,
                             inc_savings, inc_deposits, inc_dividends, inc_misc,
                             ded_80c, ded_80d_self, ded_80d_parents, ded_80ccd1b, nps_emp, ded_80e, ded_80g):
    
    res_old = calculate_tax_detailed("OLD", is_senior, gross_sal, exempt_allowances, professional_tax,
                                     hp_rent, hp_taxes, hp_loan_self, hp_loan_letout,
                                     inc_savings, inc_deposits, inc_dividends, inc_misc,
                                     ded_80c, ded_80d_self, ded_80d_parents, ded_80ccd1b, nps_emp, ded_80e, ded_80g)
                                     
    res_new = calculate_tax_detailed("NEW", is_senior, gross_sal, exempt_allowances, professional_tax,
                                     hp_rent, hp_taxes, hp_loan_self, hp_loan_letout,
                                     inc_savings, inc_deposits, inc_dividends, inc_misc,
                                     ded_80c, ded_80d_self, ded_80d_parents, ded_80ccd1b, nps_emp, ded_80e, ded_80g)
    
    recs = []
    
    # 1. 80C Gap
    if ded_80c < 150000:
        gap = 150000 - ded_80c
        res_old_opt = calculate_tax_detailed("OLD", is_senior, gross_sal, exempt_allowances, professional_tax,
                                             hp_rent, hp_taxes, hp_loan_self, hp_loan_letout,
                                             inc_savings, inc_deposits, inc_dividends, inc_misc,
                                             150000, ded_80d_self, ded_80d_parents, ded_80ccd1b, nps_emp, ded_80e, ded_80g)
        saved = res_old["total_tax"] - res_old_opt["total_tax"]
        if saved > 0:
            recs.append({
                "category": "Section 80C (PPF, ELSS, EPF, Life Insurance)",
                "action": f"Invest an additional ₹{gap:,.0f} in tax-saving financial instruments u/s 80C.",
                "tax_saving": saved,
                "regime": "OLD"
            })
            
    # 2. NPS 80CCD(1B) Gap
    if ded_80ccd1b < 50000:
        gap = 50000 - ded_80ccd1b
        res_old_opt = calculate_tax_detailed("OLD", is_senior, gross_sal, exempt_allowances, professional_tax,
                                             hp_rent, hp_taxes, hp_loan_self, hp_loan_letout,
                                             inc_savings, inc_deposits, inc_dividends, inc_misc,
                                             ded_80c, ded_80d_self, ded_80d_parents, 50000, nps_emp, ded_80e, ded_80g)
        saved = res_old["total_tax"] - res_old_opt["total_tax"]
        if saved > 0:
            recs.append({
                "category": "Section 80CCD(1B) (National Pension Scheme - Additional)",
                "action": f"Contribute ₹{gap:,.0f} more to NPS to claim exclusive additional deductions.",
                "tax_saving": saved,
                "regime": "OLD"
            })
            
    # 3. 80D Gap
    limit_self = 50000.0 if is_senior else 25000.0
    if ded_80d_self < limit_self:
        gap = limit_self - ded_80d_self
        res_old_opt = calculate_tax_detailed("OLD", is_senior, gross_sal, exempt_allowances, professional_tax,
                                             hp_rent, hp_taxes, hp_loan_self, hp_loan_letout,
                                             inc_savings, inc_deposits, inc_dividends, inc_misc,
                                             ded_80c, limit_self, ded_80d_parents, ded_80ccd1b, nps_emp, ded_80e, ded_80g)
        saved = res_old["total_tax"] - res_old_opt["total_tax"]
        if saved > 0:
            recs.append({
                "category": "Section 80D (Health Insurance - Self/Family)",
                "action": f"Acquire health insurance or claim premium payments up to ₹{limit_self:,.0f} (Gap: ₹{gap:,.0f}).",
                "tax_saving": saved,
                "regime": "OLD"
            })
            
    if ded_80d_parents < 50000:
        gap = 50000 - ded_80d_parents
        res_old_opt = calculate_tax_detailed("OLD", is_senior, gross_sal, exempt_allowances, professional_tax,
                                             hp_rent, hp_taxes, hp_loan_self, hp_loan_letout,
                                             inc_savings, inc_deposits, inc_dividends, inc_misc,
                                             ded_80c, ded_80d_self, 50000, ded_80ccd1b, nps_emp, ded_80e, ded_80g)
        saved = res_old["total_tax"] - res_old_opt["total_tax"]
        if saved > 0:
            recs.append({
                "category": "Section 80D (Health Insurance - Parents)",
                "action": f"Buy health insurance / pay medical expenses for senior parents up to ₹50,000 (Gap: ₹{gap:,.0f}).",
                "tax_saving": saved,
                "regime": "OLD"
            })

    # 4. Employer NPS contribution (allowed in BOTH regimes)
    if nps_emp == 0 and gross_sal > 0:
        est_contribution = 0.1 * gross_sal
        res_new_opt = calculate_tax_detailed("NEW", is_senior, gross_sal, exempt_allowances, professional_tax,
                                             hp_rent, hp_taxes, hp_loan_self, hp_loan_letout,
                                             inc_savings, inc_deposits, inc_dividends, inc_misc,
                                             ded_80c, ded_80d_self, ded_80d_parents, ded_80ccd1b, est_contribution, ded_80e, ded_80g)
        saved_new = res_new["total_tax"] - res_new_opt["total_tax"]
        
        res_old_opt = calculate_tax_detailed("OLD", is_senior, gross_sal, exempt_allowances, professional_tax,
                                             hp_rent, hp_taxes, hp_loan_self, hp_loan_letout,
                                             inc_savings, inc_deposits, inc_dividends, inc_misc,
                                             ded_80c, ded_80d_self, ded_80d_parents, ded_80ccd1b, est_contribution, ded_80e, ded_80g)
        saved_old = res_old["total_tax"] - res_old_opt["total_tax"]
        
        if saved_new > 0 or saved_old > 0:
            recs.append({
                "category": "Section 80CCD(2) (Employer NPS - Joint Scheme)",
                "action": f"Ask your employer to route 10% of basic salary (est. ₹{est_contribution:,.0f}) to NPS. This is exempt under BOTH regimes.",
                "tax_saving": max(saved_new, saved_old),
                "regime": "BOTH"
            })
            
    # 5. Regime Transition Note
    if res_new["total_tax"] < res_old["total_tax"]:
        diff = res_old["total_tax"] - res_new["total_tax"]
        recs.append({
            "category": "Regime Selection",
            "action": f"Opt for the New Tax Regime, which is currently ₹{diff:,.0f} cheaper without adjustments.",
            "tax_saving": diff,
            "regime": "NEW"
        })
    elif res_old["total_tax"] < res_new["total_tax"]:
        diff = res_new["total_tax"] - res_old["total_tax"]
        recs.append({
            "category": "Regime Selection",
            "action": f"Opt for the Old Tax Regime, which is currently ₹{diff:,.0f} cheaper due to your deductions.",
            "tax_saving": diff,
            "regime": "OLD"
        })

    return recs

# --- JSON SCHEMA E-FILING GENERATOR ---
def generate_itr1_json(is_senior, name, pan, aadhaar, dob, filing_section, bank_name, ifsc_code, account_number,
                       gross, exempt_allowances, professional_tax, hp_rent_received, hp_taxes_paid, hp_loan_interest_self, hp_loan_interest_letout,
                       other_inc_savings, other_inc_deposits, other_inc_dividends, other_inc_misc,
                       ded_80c, ded_80d_self, ded_80d_parents, ded_80ccd1b, nps_emp, ded_80e, ded_80g,
                       tds_pool, advance_tax, self_assessment_tax):
                       
    res_new = calculate_tax_detailed("NEW", is_senior, gross, exempt_allowances, professional_tax,
                                     hp_rent_received, hp_taxes_paid, hp_loan_interest_self, hp_loan_interest_letout,
                                     other_inc_savings, other_inc_deposits, other_inc_dividends, other_inc_misc,
                                     ded_80c, ded_80d_self, ded_80d_parents, ded_80ccd1b, nps_emp, ded_80e, ded_80g)
                                     
    res_old = calculate_tax_detailed("OLD", is_senior, gross, exempt_allowances, professional_tax,
                                     hp_rent_received, hp_taxes_paid, hp_loan_interest_self, hp_loan_interest_letout,
                                     other_inc_savings, other_inc_deposits, other_inc_dividends, other_inc_misc,
                                     ded_80c, ded_80d_self, ded_80d_parents, ded_80ccd1b, nps_emp, ded_80e, ded_80g)
                                     
    selected_regime = "NEW" if res_new["total_tax"] <= res_old["total_tax"] else "OLD"
    selected_res = res_new if selected_regime == "NEW" else res_old
    
    itr_data = {
        "Declaration": {
            "FilingSection": filing_section,
            "Regime": selected_regime,
            "FilingDate": str(datetime.date.today()),
            "AssessmentYear": "2026-27",
            "FinancialYear": "2025-26"
        },
        "PersonalInfo": {
            "FullName": name,
            "PAN": pan,
            "AadhaarNumber": aadhaar,
            "DOB": dob,
            "IsSeniorCitizen": is_senior
        },
        "BankDetails": {
            "BankName": bank_name,
            "IFSC": ifsc_code,
            "AccountNumber": account_number,
            "RefundEligible": True
        },
        "IncomeDetails": {
            "SalaryIncome": {
                "GrossSalary": gross,
                "ExemptAllowances": exempt_allowances,
                "ProfessionalTax": professional_tax,
                "StandardDeduction": 75000.0 if selected_regime == "NEW" else 50000.0,
                "NetSalary": selected_res["net_salary"]
            },
            "HousePropertyIncome": {
                "RentReceived": hp_rent_received,
                "MunicipalTaxesPaid": hp_taxes_paid,
                "LoanInterestSelfOccupied": hp_loan_interest_self,
                "LoanInterestLetOut": hp_loan_interest_letout,
                "NetIncomeHP": selected_res["hp_income"]
            },
            "OtherSourcesIncome": {
                "SavingsInterest": other_inc_savings,
                "DepositsInterest": other_inc_deposits,
                "DividendIncome": other_inc_dividends,
                "MiscIncome": other_inc_misc,
                "TotalOtherIncome": selected_res["other_sources"]
            },
            "GrossTotalIncome": selected_res["gti"]
        },
        "Deductions": {
            "ChapterVIA": {
                "Section80C": ded_80c,
                "Section80D_Self": ded_80d_self,
                "Section80D_Parents": ded_80d_parents,
                "Section80CCD_1B": ded_80ccd1b,
                "Section80CCD_2": nps_emp,
                "Section80E": ded_80e,
                "Section80G": ded_80g,
                "TotalDeductionsClaimed": selected_res["deductions"]
            }
        },
        "TaxComputation": {
            "TaxableIncome": selected_res["taxable_income"],
            "TaxBeforeCess": selected_res["tax_before_cess"],
            "Cess": selected_res["cess"],
            "TotalTaxPayable": selected_res["total_tax"],
            "PrepaidTaxes": {
                "TDS": tds_pool,
                "AdvanceTax": advance_tax,
                "SelfAssessmentTax": self_assessment_tax,
                "TotalPrepaid": tds_pool + advance_tax + self_assessment_tax
            },
            "NetRefund": max(0.0, (tds_pool + advance_tax + self_assessment_tax) - selected_res["total_tax"]),
            "NetPayable": max(0.0, selected_res["total_tax"] - (tds_pool + advance_tax + self_assessment_tax))
        }
    }
    return json.dumps(itr_data, indent=4)

# --- STATE INITIALIZATION ---
keys = [
    "name", "pan", "aadhaar", "dob", "is_senior", "filing_section",
    "bank_name", "ifsc_code", "account_number",
    "gross", "exempt_allowances", "professional_tax",
    "hp_rent_received", "hp_taxes_paid", "hp_loan_interest_self", "hp_loan_interest_letout",
    "other_inc_savings", "other_inc_deposits", "other_inc_dividends", "other_inc_misc",
    "ded_80c_elss_ppf", "ded_80c_epf", "ded_80c_others",
    "ded_80d_self", "ded_80d_parents", "ded_80ccd1b", "nps_emp", "ded_80e", "ded_80g",
    "tds_pool", "advance_tax", "self_assessment_tax"
]
defaults = {
    "name": "",
    "pan": "",
    "aadhaar": "",
    "dob": "",
    "is_senior": False,
    "filing_section": "139(1) - On or before due date",
    "bank_name": "",
    "ifsc_code": "",
    "account_number": "",
    "gross": 0.0,
    "exempt_allowances": 0.0,
    "professional_tax": 0.0,
    "hp_rent_received": 0.0,
    "hp_taxes_paid": 0.0,
    "hp_loan_interest_self": 0.0,
    "hp_loan_interest_letout": 0.0,
    "other_inc_savings": 0.0,
    "other_inc_deposits": 0.0,
    "other_inc_dividends": 0.0,
    "other_inc_misc": 0.0,
    "ded_80c_elss_ppf": 100000.0,
    "ded_80c_epf": 30000.0,
    "ded_80c_others": 20000.0,
    "ded_80d_self": 15000.0,
    "ded_80d_parents": 10000.0,
    "ded_80ccd1b": 0.0,
    "nps_emp": 0.0,
    "ded_80e": 0.0,
    "ded_80g": 0.0,
    "tds_pool": 0.0,
    "advance_tax": 0.0,
    "self_assessment_tax": 0.0
}
for key in keys:
    if key not in st.session_state:
        st.session_state[key] = defaults[key]

# --- COPY FROM WIDGET TO PERSISTENT STATE ---
widget_to_persistent = {
    "widget_name": "name",
    "widget_pan": "pan",
    "widget_aadhaar": "aadhaar",
    "widget_dob": "dob",
    "widget_is_senior": "is_senior",
    "widget_filing_section": "filing_section",
    "widget_bank_name": "bank_name",
    "widget_ifsc_code": "ifsc_code",
    "widget_account_number": "account_number",
    "widget_gross": "gross",
    "widget_exempt_allowances": "exempt_allowances",
    "widget_professional_tax": "professional_tax",
    "widget_hp_rent_received": "hp_rent_received",
    "widget_hp_taxes_paid": "hp_taxes_paid",
    "widget_hp_loan_interest_self": "hp_loan_interest_self",
    "widget_hp_loan_interest_letout": "hp_loan_interest_letout",
    "widget_other_inc_savings": "other_inc_savings",
    "widget_other_inc_deposits": "other_inc_deposits",
    "widget_other_inc_dividends": "other_inc_dividends",
    "widget_other_inc_misc": "other_inc_misc",
    "widget_ded_80c_elss_ppf": "ded_80c_elss_ppf",
    "widget_ded_80c_epf": "ded_80c_epf",
    "widget_ded_80c_others": "ded_80c_others",
    "widget_ded_80d_self": "ded_80d_self",
    "widget_ded_80d_parents": "ded_80d_parents",
    "widget_ded_80ccd1b": "ded_80ccd1b",
    "widget_nps_emp": "nps_emp",
    "widget_ded_80e": "ded_80e",
    "widget_ded_80g": "ded_80g",
    "widget_tds_pool": "tds_pool",
    "widget_advance_tax": "advance_tax",
    "widget_self_assessment_tax": "self_assessment_tax"
}

for w_key, p_key in widget_to_persistent.items():
    if w_key in st.session_state:
        st.session_state[p_key] = st.session_state[w_key]

# --- STEP CONTROLLER ---
if "active_tab" not in st.session_state:
    st.session_state["active_tab"] = 0

# --- REAL-TIME CALCULATIONS ---
ded_80c_total = st.session_state["ded_80c_elss_ppf"] + st.session_state["ded_80c_epf"] + st.session_state["ded_80c_others"]

res_old = calculate_tax_detailed(
    "OLD", st.session_state["is_senior"], st.session_state["gross"], st.session_state["exempt_allowances"], st.session_state["professional_tax"],
    st.session_state["hp_rent_received"], st.session_state["hp_taxes_paid"], st.session_state["hp_loan_interest_self"], st.session_state["hp_loan_interest_letout"],
    st.session_state["other_inc_savings"], st.session_state["other_inc_deposits"], st.session_state["other_inc_dividends"], st.session_state["other_inc_misc"],
    ded_80c_total, st.session_state["ded_80d_self"], st.session_state["ded_80d_parents"], st.session_state["ded_80ccd1b"], st.session_state["nps_emp"], st.session_state["ded_80e"], st.session_state["ded_80g"]
)

res_new = calculate_tax_detailed(
    "NEW", st.session_state["is_senior"], st.session_state["gross"], st.session_state["exempt_allowances"], st.session_state["professional_tax"],
    st.session_state["hp_rent_received"], st.session_state["hp_taxes_paid"], st.session_state["hp_loan_interest_self"], st.session_state["hp_loan_interest_letout"],
    st.session_state["other_inc_savings"], st.session_state["other_inc_deposits"], st.session_state["other_inc_dividends"], st.session_state["other_inc_misc"],
    ded_80c_total, st.session_state["ded_80d_self"], st.session_state["ded_80d_parents"], st.session_state["ded_80ccd1b"], st.session_state["nps_emp"], st.session_state["ded_80e"], st.session_state["ded_80g"]
)

total_taxes_paid = st.session_state["tds_pool"] + st.session_state["advance_tax"] + st.session_state["self_assessment_tax"]

ref_old = max(0.0, total_taxes_paid - res_old["total_tax"])
ref_new = max(0.0, total_taxes_paid - res_new["total_tax"])

payable_old = max(0.0, res_old["total_tax"] - total_taxes_paid)
payable_new = max(0.0, res_new["total_tax"] - total_taxes_paid)

# --- SIDEBAR AUTOMATIC CALCULATOR ---
with st.sidebar:
    st.markdown("### 📊 Real-Time Refund Tracker")
    st.caption("Calculated automatically based on inputs (FY 2025-26 rules):")
    
    payable_old_html = f"<div style='font-size: 0.75rem; color: #f87171;'>Payable: ₹{payable_old:,.0f}</div>" if payable_old > 0 else ""
    payable_new_html = f"<div style='font-size: 0.75rem; color: #f87171;'>Payable: ₹{payable_new:,.0f}</div>" if payable_new > 0 else ""
    
    st.markdown(f"""
        <div style="padding: 1rem; border-radius: 8px; background-color: #2563eb; color: white; margin-bottom: 10px;">
            <div style="font-size: 0.85rem; opacity: 0.9;">Old Regime Refund</div>
            <div style="font-size: 1.5rem; font-weight: 700;">₹{ref_old:,.0f}</div>
            <div style="font-size: 0.75rem; opacity: 0.8;">Tax Liability: ₹{res_old["total_tax"]:,.0f}</div>
            {payable_old_html}
        </div>
        <div style="padding: 1rem; border-radius: 8px; background-color: #16a34a; color: white; margin-bottom: 15px;">
            <div style="font-size: 0.85rem; opacity: 0.9;">New Regime Refund</div>
            <div style="font-size: 1.5rem; font-weight: 700;">₹{ref_new:,.0f}</div>
            <div style="font-size: 0.75rem; opacity: 0.8;">Tax Liability: ₹{res_new["total_tax"]:,.0f}</div>
            {payable_new_html}
        </div>
    """, unsafe_allow_html=True)
    
    # Recommendation
    if res_old["total_tax"] < res_new["total_tax"]:
        diff = res_new["total_tax"] - res_old["total_tax"]
        st.info(f"💡 **Old Regime** is cheaper by **₹{diff:,.0f}**")
    elif res_new["total_tax"] < res_old["total_tax"]:
        diff = res_old["total_tax"] - res_new["total_tax"]
        st.success(f"💡 **New Regime** is cheaper by **₹{diff:,.0f}**")
    else:
        st.warning("⚖️ Both regimes yield identical tax.")

# --- SIMULATED NAVIGATION TABS ---
tab_cols = st.columns(5)
tab_labels = [
    "👤 Step 1: Profile & Bank",
    "💼 Step 2: Income Sources",
    "📂 Step 3: Upload Docs",
    "🛡️ Step 4: Deductions",
    "📈 Step 5: Tax Summary"
]

for idx, label in enumerate(tab_labels):
    with tab_cols[idx]:
        is_active = (st.session_state["active_tab"] == idx)
        btn_type = "primary" if is_active else "secondary"
        if st.button(label, key=f"tab_btn_{idx}", type=btn_type, use_container_width=True):
            st.session_state["active_tab"] = idx
            st.rerun()

st.divider()

# --- RENDER SELECTED TAB CONTENT ---
active_tab = st.session_state["active_tab"]

# --- TAB 1: PERSONAL & BANK DETAILS ---
if active_tab == 0:
    st.markdown("### Personal Profile & Bank Details")
    st.caption("Fields marked with PAN, Aadhaar, and Bank accounts are required for ITR validation.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("##### 👤 Personal Details")
        st.text_input("Full Name", value=st.session_state["name"], key="widget_name")
        st.text_input("PAN Number (Permanent Account Number)", value=st.session_state["pan"], key="widget_pan", placeholder="ABCDE1234F")
        pan_val = st.session_state.get("pan", "").upper()
        if pan_val and not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', pan_val):
            st.warning("⚠️ Invalid PAN format (expected ABCDE1234F)")
            
        st.text_input("Aadhaar Number", value=st.session_state["aadhaar"], key="widget_aadhaar", placeholder="12-digit number")
        aad_val = st.session_state.get("aadhaar", "").replace(" ", "")
        if aad_val and not re.match(r'^[0-9]{12}$', aad_val):
            st.warning("⚠️ Invalid Aadhaar number (expected 12 digits)")
            
        st.text_input("Date of Birth (DD/MM/YYYY)", value=st.session_state["dob"], key="widget_dob")
        st.toggle("Are you a Senior Citizen (Age >= 60)?", value=st.session_state["is_senior"], key="widget_is_senior")
        
        options = [
            "139(1) - On or before due date", 
            "139(4) - Belated return", 
            "139(5) - Revised return"
        ]
        try:
            def_idx = options.index(st.session_state["filing_section"])
        except:
            def_idx = 0
        st.selectbox("Filing Section", options, index=def_idx, key="widget_filing_section")
        
    with col2:
        st.markdown("##### 🏦 Bank Account for Refund")
        st.text_input("Bank Name", value=st.session_state["bank_name"], key="widget_bank_name")
        st.text_input("IFSC Code", value=st.session_state["ifsc_code"], key="widget_ifsc_code", placeholder="ABCD0123456")
        ifsc_val = st.session_state.get("ifsc_code", "").upper()
        if ifsc_val and not re.match(r'^[A-Z]{4}0[A-Z0-9]{6}$', ifsc_val):
            st.warning("⚠️ Invalid IFSC format (expected ABCD0123456)")
            
        st.text_input("Account Number", value=st.session_state["account_number"], key="widget_account_number")
        
    st.markdown("<br><hr>", unsafe_allow_html=True)
    if st.button("Save & Proceed to Income Sources ➡️", type="primary", use_container_width=True):
        st.session_state["active_tab"] = 1
        st.rerun()

# --- TAB 2: INCOME SOURCES ---
elif active_tab == 1:
    st.markdown("### Declare Income Sources")
    st.caption("Flesh out your salary details, house property loss/rent, and other interest holdings.")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("##### 💼 Income from Salary")
        st.number_input("Gross Annual Salary (17(1) + 17(2) + 17(3)) (₹)", value=st.session_state["gross"], key="widget_gross", step=10000.0)
        st.number_input("Exempt Allowances (HRA, LTA, etc.) (₹)", value=st.session_state["exempt_allowances"], key="widget_exempt_allowances", step=5000.0)
        st.number_input("Professional Tax Paid (₹)", value=st.session_state["professional_tax"], key="widget_professional_tax", step=500.0)
        
    with col2:
        st.markdown("##### 🏠 Income from House Property")
        st.number_input("Rent Received (if let out) (₹)", value=st.session_state["hp_rent_received"], key="widget_hp_rent_received", step=10000.0)
        st.number_input("Municipal Taxes Paid (₹)", value=st.session_state["hp_taxes_paid"], key="widget_hp_taxes_paid", step=1000.0)
        st.number_input("Home Loan Interest (Self-Occupied) (₹)", value=st.session_state["hp_loan_interest_self"], key="widget_hp_loan_interest_self", step=10000.0)
        st.number_input("Home Loan Interest (Let-Out) (₹)", value=st.session_state["hp_loan_interest_letout"], key="widget_hp_loan_interest_letout", step=10000.0)
        
    with col3:
        st.markdown("##### 🏦 Income from Other Sources")
        st.number_input("Savings Bank Interest (₹)", value=st.session_state["other_inc_savings"], key="widget_other_inc_savings", step=1000.0)
        st.number_input("FD / Deposits / Post Office Interest (₹)", value=st.session_state["other_inc_deposits"], key="widget_other_inc_deposits", step=1000.0)
        st.number_input("Dividend Income (₹)", value=st.session_state["other_inc_dividends"], key="widget_other_inc_dividends", step=1000.0)
        st.number_input("Other Miscellaneous Income (₹)", value=st.session_state["other_inc_misc"], key="widget_other_inc_misc", step=1000.0)

    st.markdown("<br><hr>", unsafe_allow_html=True)
    col_prev, col_next = st.columns(2)
    with col_prev:
        if st.button("⬅️ Back to Personal Details", use_container_width=True):
            st.session_state["active_tab"] = 0
            st.rerun()
    with col_next:
        if st.button("Save & Proceed to Documents Upload ➡️", type="primary", use_container_width=True):
            st.session_state["active_tab"] = 2
            st.rerun()

# --- TAB 3: UPLOAD & AUTOMATED EXTRACTION ---
elif active_tab == 2:
    st.markdown("### Upload Form 16, 16A, or 16B Certificates")
    st.caption("Our parser reads your financial tables directly to populate income entries securely.")
    
    f16 = st.file_uploader("Form 16 Part B (Salary Income)", type=["pdf"], key="t1_f16")
    f16a = st.file_uploader("Form 16A / 16B (FD Interest & Property Sales)", type=["pdf"], key="t1_f16a")
    
    if f16:
        if st.session_state.get('parsed_f16_name') != f16.name:
            text = extract_text_from_pdf(f16)
            parsed_data = parse_form16_text(text)
            
            # Constrain values
            if 'ded_80c_elss_ppf' in parsed_data:
                parsed_data['ded_80c_elss_ppf'] = float(min(150000.0, max(0.0, parsed_data['ded_80c_elss_ppf'])))
            if 'ded_80d_self' in parsed_data:
                parsed_data['ded_80d_self'] = float(min(75000.0, max(0.0, parsed_data['ded_80d_self'])))
            if 'hp_loan_interest_self' in parsed_data:
                parsed_data['hp_loan_interest_self'] = min(200000.0, max(0.0, parsed_data['hp_loan_interest_self']))
                
            # Update session state keys with parsed values
            for k, v in parsed_data.items():
                st.session_state[k] = v
                
            st.session_state['parsed_f16_name'] = f16.name
            st.session_state['extraction_summary_f16'] = parsed_data
            st.rerun()
            
    if f16a:
        if st.session_state.get('parsed_f16a_name') != f16a.name:
            text = extract_text_from_pdf(f16a)
            parsed_data = parse_form16a_16b_text(text)
            
            # For 16A/B, we accumulate TDS and other income
            if 'tds_pool' in parsed_data:
                st.session_state['tds_pool'] += parsed_data['tds_pool']
            if 'other_income' in parsed_data:
                # Map generic other income to deposits interest appropriately
                st.session_state['other_inc_deposits'] += parsed_data['other_income']
                
            st.session_state['parsed_f16a_name'] = f16a.name
            st.session_state['extraction_summary_f16a'] = parsed_data
            st.rerun()
            
    if f16 or f16a:
        st.success("✅ Files processed successfully. Your calculations have been updated.")
        
        # Display extraction summaries
        if st.session_state.get('extraction_summary_f16'):
            st.info("ℹ️ **Extracted from Form 16 Part B:**\n" + "\n".join(
                [f"- **{k.replace('_', ' ').title() if k != 'hra' else 'HRA'}:** ₹{v:,.2f}" for k, v in st.session_state['extraction_summary_f16'].items() if v > 0]
            ))
        if st.session_state.get('extraction_summary_f16a'):
            st.info("ℹ️ **Extracted from Form 16A/16B:**\n" + "\n".join(
                [f"- **{k.replace('_', ' ').title() if k != 'hra' else 'HRA'}:** ₹{v:,.2f}" for k, v in st.session_state['extraction_summary_f16a'].items() if v > 0]
            ))
            
    st.markdown("<br><hr>", unsafe_allow_html=True)
    col_prev, col_next = st.columns(2)
    with col_prev:
        if st.button("⬅️ Back to Income Sources", use_container_width=True):
            st.session_state["active_tab"] = 1
            st.rerun()
    with col_next:
        if st.button("Save & Proceed to Deductions Matrix ➡️", type="primary", use_container_width=True):
            st.session_state["active_tab"] = 3
            st.rerun()

# --- TAB 4: DEDUCTIONS MATRIX ---
elif active_tab == 3:
    st.markdown("### Declare Investments & Exemptions")
    
    col_old, col_new = st.columns(2)
    with col_old:
        st.markdown("##### 🟢 Section 80C Investments Pool (Capped at ₹1,50,000)")
        st.number_input("ELSS Mutual Funds, PPF, Life Insurance Premium (₹)", value=st.session_state["ded_80c_elss_ppf"], key="widget_ded_80c_elss_ppf", step=5000.0)
        st.number_input("Employee Provident Fund (EPF) (₹)", value=st.session_state["ded_80c_epf"], key="widget_ded_80c_epf", step=5000.0)
        st.number_input("Others (Home loan principal repayment, School fees) (₹)", value=st.session_state["ded_80c_others"], key="widget_ded_80c_others", step=5000.0)
        st.caption(f"**Total Section 80C Claimed:** ₹{ded_80c_total:,.0f} / ₹1,50,000")
        
        st.write("")
        st.markdown("##### 🟢 Section 80D Health Insurance Premiums")
        st.number_input("Medical Premium: Self, Spouse & Dependent Children (₹)", value=st.session_state["ded_80d_self"], key="widget_ded_80d_self", step=1000.0)
        st.number_input("Medical Premium: Parents (₹)", value=st.session_state["ded_80d_parents"], key="widget_ded_80d_parents", step=1000.0)
        
    with col_new:
        st.markdown("##### 🔵 Section 80CCD (National Pension Scheme - NPS)")
        st.number_input("Self Voluntary NPS Contribution (Sec 80CCD(1B)) (₹)", value=st.session_state["ded_80ccd1b"], key="widget_ded_80ccd1b", step=5000.0)
        st.number_input("Employer NPS Contribution (Sec 80CCD(2)) (₹)", value=st.session_state["nps_emp"], key="widget_nps_emp", step=5000.0)
        st.caption("Note: Employer NPS is eligible for tax exemption under BOTH Old and New Regimes.")
        
        st.write("")
        st.markdown("##### 🔵 Other Allowed Deductions")
        st.number_input("Interest on Education Loan (Sec 80E) (₹)", value=st.session_state["ded_80e"], key="widget_ded_80e", step=5000.0)
        st.number_input("Donations to Charitable Institutions (Sec 80G) (₹)", value=st.session_state["ded_80g"], key="widget_ded_80g", step=5000.0)
        
        st.write("")
        st.markdown("##### ⚖️ Taxes Paid / TDS")
        st.number_input("Total TDS Deducted (as per Form 16/26AS) (₹)", value=st.session_state["tds_pool"], key="widget_tds_pool", step=1000.0)
        st.number_input("Advance Tax Paid (₹)", value=st.session_state["advance_tax"], key="widget_advance_tax", step=1000.0)
        st.number_input("Self-Assessment Tax Paid (₹)", value=st.session_state["self_assessment_tax"], key="widget_self_assessment_tax", step=1000.0)

    st.markdown("<br><hr>", unsafe_allow_html=True)
    col_prev, col_next = st.columns(2)
    with col_prev:
        if st.button("⬅️ Back to Upload Documents", use_container_width=True):
            st.session_state["active_tab"] = 2
            st.rerun()
    with col_next:
        if st.button("Save & Proceed to Summary ➡️", type="primary", use_container_width=True):
            st.session_state["active_tab"] = 4
            st.rerun()

# --- TAB 5: OPTIMIZATION SUMMARY & RECOMMENDATIONS ---
elif active_tab == 4:
    st.markdown("### Final Refund Strategy & Recommendations Dashboard")
    st.caption("Review your final comparison and apply specific actions to maximize your tax refund.")
    
    # 1. Summary Cards
    mc1, mc2 = st.columns(2)
    with mc1:
        bg_col = "#2563eb" if ref_old >= ref_new else "#475569"
        st.markdown(f'<div class="summary-card" style="background-color: {bg_col};">Old Regime Estimated Refund<br><span style="font-size: 28px;">₹{ref_old:,.0f}</span></div>', unsafe_allow_html=True)
    with mc2:
        bg_col = "#16a34a" if ref_new >= ref_old else "#475569"
        st.markdown(f'<div class="summary-card" style="background-color: {bg_col};">New Regime Estimated Refund<br><span style="font-size: 28px;">₹{ref_new:,.0f}</span></div>', unsafe_allow_html=True)

    # 2. Detailed Breakdown Table
    st.markdown("#### 📋 Comparative Tax Computation Table (FY 2025-26 Rules)")
    breakdown_data = {
        "Particulars": [
            "Gross Salary Income",
            "Less: Exempt Allowances (HRA, LTA, etc.)",
            "Less: Standard Deduction u/s 16(ia)",
            "Less: Professional Tax",
            "Net Salary Income",
            "Income / Loss from House Property",
            "Income from Other Sources (Interest, Dividends)",
            "Gross Total Income (GTI)",
            "Less: Chapter VI-A Deductions",
            "Taxable Income",
            "Tax before Cess",
            "Health & Education Cess (4%)",
            "Total Tax Liability",
            "Taxes Paid (TDS + Advance + Self-Assessment)",
            "Refund Amount / (Balance Payable)"
        ],
        "Old Regime": [
            f"₹{st.session_state['gross']:,.0f}",
            f"-₹{st.session_state['exempt_allowances']:,.0f}",
            f"-₹{50000.0 if st.session_state['gross'] > 0 else 0.0:,.0f}",
            f"-₹{st.session_state['professional_tax']:,.0f}",
            f"₹{res_old['net_salary']:,.0f}",
            f"₹{res_old['hp_income']:,.0f}",
            f"₹{res_old['other_sources']:,.0f}",
            f"₹{res_old['gti']:,.0f}",
            f"-₹{res_old['deductions']:,.0f}",
            f"₹{res_old['taxable_income']:,.0f}",
            f"₹{res_old['tax_before_cess']:,.0f}",
            f"₹{res_old['cess']:,.0f}",
            f"₹{res_old['total_tax']:,.0f}",
            f"₹{total_taxes_paid:,.0f}",
            f"₹{ref_old:,.0f}" if ref_old > 0 else f"-₹{payable_old:,.0f}"
        ],
        "New Regime": [
            f"₹{st.session_state['gross']:,.0f}",
            "N/A",
            f"-₹{75000.0 if st.session_state['gross'] > 0 else 0.0:,.0f}",
            "N/A",
            f"₹{res_new['net_salary']:,.0f}",
            f"₹{res_new['hp_income']:,.0f}",
            f"₹{res_new['other_sources']:,.0f}",
            f"₹{res_new['gti']:,.0f}",
            f"-₹{res_new['deductions']:,.0f}",
            f"₹{res_new['taxable_income']:,.0f}",
            f"₹{res_new['tax_before_cess']:,.0f}",
            f"₹{res_new['cess']:,.0f}",
            f"₹{res_new['total_tax']:,.0f}",
            f"₹{total_taxes_paid:,.0f}",
            f"₹{ref_new:,.0f}" if ref_new > 0 else f"-₹{payable_new:,.0f}"
        ]
    }
    st.table(breakdown_data)

    # 3. Optimization suggestions
    st.markdown("#### 💡 Tax Saving Recommendations & Refund Maximizers")
    recs = generate_recommendations(
        st.session_state["is_senior"], st.session_state["gross"], st.session_state["exempt_allowances"], st.session_state["professional_tax"],
        st.session_state["hp_rent_received"], st.session_state["hp_taxes_paid"], st.session_state["hp_loan_interest_self"], st.session_state["hp_loan_interest_letout"],
        st.session_state["other_inc_savings"], st.session_state["other_inc_deposits"], st.session_state["other_inc_dividends"], st.session_state["other_inc_misc"],
        ded_80c_total, st.session_state["ded_80d_self"], st.session_state["ded_80d_parents"], st.session_state["ded_80ccd1b"], st.session_state["nps_emp"], st.session_state["ded_80e"], st.session_state["ded_80g"]
    )
    
    if recs:
        for r in recs:
            with st.container():
                st.markdown(f"""
                <div class="rec-card">
                    <span style="font-weight: 700; color: #065f46; font-size: 1.1rem;">{r['category']}</span><br>
                    <span style="color: #374151;">{r['action']}</span><br>
                    <span style="font-weight: 600; color: #2563eb;">Estimated Tax Saved: ₹{r['tax_saving']:,.2f}</span>
                    <span style="font-size: 0.85rem; color: #6b7280; margin-left: 10px;">(Applicable to: {r['regime']} Regime)</span>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("🎉 Excellent job! You have fully optimized all available tax-saving opportunities.")

    # 4. Bar chart
    fig = go.Figure(data=[
        go.Bar(name='Tax Liability', x=['Old Regime', 'New Regime'], y=[res_old["total_tax"], res_new["total_tax"]], marker_color='#ef4444'),
        go.Bar(name='Refund Generated', x=['Old Regime', 'New Regime'], y=[ref_old, ref_new], marker_color='#22c55e')
    ])
    fig.update_layout(barmode='stack', height=300, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig, use_container_width=True)

    # 5. ITR filing verification & validation checklist
    st.markdown("#### 🔍 ITR Filing Verification & Validation Checklist")
    pan_ok = bool(re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', st.session_state["pan"].upper()))
    aadhaar_ok = bool(re.match(r'^[0-9]{12}$', st.session_state["aadhaar"].replace(" ", "")))
    bank_ok = bool(st.session_state["bank_name"] and re.match(r'^[A-Z]{4}0[A-Z0-9]{6}$', st.session_state["ifsc_code"].upper()) and st.session_state["account_number"])
    salary_ok = st.session_state["gross"] > 0
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        if pan_ok:
            st.success("✅ **PAN Number:** Valid and ready.")
        else:
            st.error("❌ **PAN Number:** Missing or invalid format.")
            
        if aadhaar_ok:
            st.success("✅ **Aadhaar Number:** Valid and ready.")
        else:
            st.error("❌ **Aadhaar Number:** Missing or invalid format.")
            
    with col_c2:
        if bank_ok:
            st.success("✅ **Bank Account details:** Complete (IFSC & Account No).")
        else:
            st.error("❌ **Bank Account details:** Missing or invalid IFSC.")
            
        if salary_ok:
            st.success(f"✅ **Salary Income:** Declared (₹{st.session_state['gross']:,.2f}).")
        else:
            st.warning("⚠️ **Salary Income:** Zero declared (Filing Nil Return).")

    # 6. Generate ITR e-Filing JSON Download
    st.markdown("#### 📥 Download Official ITR e-Filing Payload")
    st.caption("Once validation passes, download the structured ITR-1 e-filing payload to upload directly to the Indian Income Tax Portal.")
    
    itr_json = generate_itr1_json(
        st.session_state["is_senior"], st.session_state["name"], st.session_state["pan"], st.session_state["aadhaar"], st.session_state["dob"], st.session_state["filing_section"], st.session_state["bank_name"], st.session_state["ifsc_code"], st.session_state["account_number"],
        st.session_state["gross"], st.session_state["exempt_allowances"], st.session_state["professional_tax"], st.session_state["hp_rent_received"], st.session_state["hp_taxes_paid"], st.session_state["hp_loan_interest_self"], st.session_state["hp_loan_interest_letout"],
        st.session_state["other_inc_savings"], st.session_state["other_inc_deposits"], st.session_state["other_inc_dividends"], st.session_state["other_inc_misc"],
        ded_80c_total, st.session_state["ded_80d_self"], st.session_state["ded_80d_parents"], st.session_state["ded_80ccd1b"], st.session_state["nps_emp"], st.session_state["ded_80e"], st.session_state["ded_80g"],
        st.session_state["tds_pool"], st.session_state["advance_tax"], st.session_state["self_assessment_tax"]
    )
    
    st.download_button(
        label="📥 Download ITR-1 Schema JSON File",
        data=itr_json,
        file_name=f"ITR1_AY2026-27_{st.session_state['pan'] or 'TAX_PAYER'}.json",
        mime="application/json",
        use_container_width=True,
        type="primary"
    )
    
    st.markdown("<br><hr>", unsafe_allow_html=True)
    if st.button("⬅️ Back to Deductions", use_container_width=True):
        st.session_state["active_tab"] = 3
        st.rerun()
