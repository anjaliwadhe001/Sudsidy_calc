from flask import Flask, request, jsonify
from fpdf import FPDF
import pandas as pd
import os

app = Flask(__name__)

# Load Zone Database CSV
df = pd.read_csv("Zone_database.csv")
df.columns = df.columns.str.strip()
df['Subdistrict'] = df['Subdistrict'].str.strip().str.lower()

# Zone-wise subsidy data
zone_data = {
    "Zone": ["A", "B", "C", "D"],
    "SGST Initial (%)": [50, 60, 70, 75],
    "SGST Initial Years": [5, 7, 8, 10],
    "SGST Extended (%)": [25, 30, 30, 35],
    "SGST Extended Years": [3, 3, 3, 3],
    "Stamp Duty (%)": [0, 0.60, 0.75, 1.00],
    "Interest Rate (%)": [5, 5, 6, 6],
    "Interest Years": [5, 5, 7, 7],
    "Capital Investment Subsidy": [15] * 4,
    "Max Investment Subsidy (Rs.)": [2000000] * 4,
    "Max Interest/Year (Rs.)": [2000000] * 4
}

zone_df = pd.DataFrame(zone_data)

# Subsidy calculation logic
def calculate_subsidy(zone, enterprise_size, plant_machinery, building_civil_work,
                      term_loan_amount, land_cost, net_sgst_paid_cash_ledger):
    zone_info = zone_df[zone_df["Zone"] == zone].iloc[0]
    capital_investment = plant_machinery + building_civil_work

    capital_subsidy = 0
    if enterprise_size in ["Micro", "Small"]:
        capital_subsidy = min(0.15 * capital_investment, 2000000)

    stamp_duty_subsidy = zone_info["Stamp Duty (%)"] * (0.07 * land_cost)
    annual_interest = term_loan_amount * (zone_info["Interest Rate (%)"] / 100)
    interest_subsidy = min(annual_interest, 2000000) * zone_info["Interest Years"]

    sgst_reimbursement = (
        net_sgst_paid_cash_ledger * (zone_info["SGST Initial (%)"] / 100) +
        net_sgst_paid_cash_ledger * (zone_info["SGST Extended (%)"] / 100)
    )

    total_subsidy = capital_subsidy + stamp_duty_subsidy + interest_subsidy + sgst_reimbursement

    return {
        "capital_investment_subsidy": round(capital_subsidy, 2),
        "stamp_duty_exemption": round(stamp_duty_subsidy, 2),
        "interest_subsidy": round(interest_subsidy, 2),
        "sgst_reimbursement": round(sgst_reimbursement, 2),
        "total_subsidy": round(total_subsidy, 2)
    }

# PDF generation
def generate_pdf(user_data, result):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, txt="Subsidy Calculation Report", ln=True, align='C')

    pdf.set_font("Arial", "B", 12)
    pdf.cell(200, 10, txt="Input Details", ln=True)

    pdf.set_font("Arial", "", 11)
    for k, v in user_data.items():
        pdf.cell(200, 8, txt=f"{k}: {v}", ln=True)

    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(200, 10, txt="Subsidy Calculation Result", ln=True)

    pdf.set_font("Arial", "", 11)
    for k, v in result.items():
        pdf.cell(200, 8, txt=f"{k}: Rs.{v:,.2f}", ln=True)

    file_path = "Subsidy_Calculation_Report.pdf"
    pdf.output(file_path)
    return file_path

# === API Endpoint ===
@app.route("/calculate-subsidy", methods=["POST"])
def calculate():
    data = request.get_json(force=True)

    subdistrict = data["subdistrict"].strip().lower()
    row = df[df["Subdistrict"] == subdistrict]
    if row.empty:
        return jsonify({"error": "Subdistrict not found."}), 400

    zone = row.iloc[0]["Zone"]

    # Extract all other inputs
    user_data = {
        "Name": data.get("name"),
        "Organization Name": data.get("organization_name"),
        "State": data.get("state"),
        "District": data.get("district"),
        "Subdistrict": subdistrict.title(),
        "Enterprise Size": data.get("enterprise_size"),
        "Business Nature": data.get("buisness_nature"),
        "Industry Type": data.get("industry_type"),
        "Plant & Machinery": data.get("plant_machinery"),
        "Building & Civil Work": data.get("building_civil_work"),
        "Land Owned": data.get("land_owned"),
        "Land Cost": data.get("land_cost", 0.0),
        "Loan": data.get("loan"),
        "Term Loan Amount": data.get("term_loan_amount", 0.0),
        "Loan Tenure": data.get("loan_tenure"),
        "SGST Paid": data.get("net_sgst_paid_cash_ledger")
    }

    result = calculate_subsidy(
        zone,
        data["enterprise_size"].capitalize(),
        float(data["plant_machinery"]),
        float(data["building_civil_work"]),
        float(data.get("term_loan_amount", 0.0)),
        float(data.get("land_cost", 0.0)),
        float(data["net_sgst_paid_cash_ledger"])
    )

    pdf_path = generate_pdf(user_data, result)

    return jsonify({
        "zone": zone,
        "subsidy_breakup": result,
        "pdf_path": pdf_path
    })

if __name__ == "__main__":
    app.run(debug=True)
