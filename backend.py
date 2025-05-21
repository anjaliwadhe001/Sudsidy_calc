from flask import Flask, request, jsonify
from fpdf import FPDF
import pandas as pd
import smtplib
from email.message import EmailMessage
import os

app = Flask(__name__)

# Load zone database
df = pd.read_csv("Zone_database.csv")
df.columns = df.columns.str.strip()
df['Subdistrict'] = df['Subdistrict'].str.strip().str.lower()

# Zone-wise data
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


@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        data = request.json
        subdistrict = data.get("subdistrict", "").strip().lower()
        matched_row = df[df['Subdistrict'] == subdistrict]

        if matched_row.empty:
            return jsonify({"error": "Subdistrict not found"}), 400

        zone = matched_row.iloc[0]['Zone']

        # Input values
        user_name = data.get("name", "")
        organization_name = data.get("organization_name", "")
        state = data.get("state", "")
        district = data.get("district", "")
        enterprise_size = data.get("enterprise_size", "")
        buisness_nature = data.get("business_nature", "")
        industry_type = data.get("industry_type", "")
        plant_machinery = float(data.get("plant_machinery", 0))
        building_civil_work = float(data.get("building_civil_work", 0))
        land_cost = float(data.get("land_cost", 0))
        term_loan_amount = float(data.get("term_loan_amount", 0))
        loan_tenure = data.get("loan_tenure", "N/A")
        net_sgst_paid_cash_ledger = float(data.get("sgst_paid", 0))
        user_email = data.get("email", "")

        zone_info = zone_df[zone_df["Zone"] == zone].iloc[0]
        capital_investment = plant_machinery + building_civil_work

        # Capital Investment Subsidy
        if enterprise_size.strip().capitalize() in ["Micro", "Small"]:
            capital_subsidy = min(0.15 * capital_investment, 2000000)
        else:
            capital_subsidy = 0

        stamp_duty_subsidy = (zone_info["Stamp Duty (%)"]) * (0.07 * land_cost)
        annual_interest = term_loan_amount * (zone_info["Interest Rate (%)"] / 100)
        interest_subsidy = min(annual_interest, 2000000) * zone_info["Interest Years"]
        sgst_reimbursement = (
            net_sgst_paid_cash_ledger * (zone_info["SGST Initial (%)"] / 100) +
            net_sgst_paid_cash_ledger * (zone_info["SGST Extended (%)"] / 100)
        )

        total_subsidy = capital_subsidy + stamp_duty_subsidy + interest_subsidy + sgst_reimbursement

        result = {
            "capital_investment_subsidy": round(capital_subsidy, 2),
            "stamp_duty_exemption": round(stamp_duty_subsidy, 2),
            "interest_subsidy": round(interest_subsidy, 2),
            "sgst_reimbursement": round(sgst_reimbursement, 2),
            "total_subsidy": round(total_subsidy, 2)
        }

        # PDF generation
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(200, 10, txt="Subsidy Calculation Report", ln=True, align='C')

        pdf.set_font("Arial", "B", 12)
        pdf.cell(200, 10, txt="Input Details", ln=True)

        pdf.set_font("Arial", "", 11)
        inputs = {
            "Name": user_name,
            "Organization Name": organization_name,
            "State": state,
            "District": district,
            "Subdistrict": subdistrict.title(),
            "Enterprise Size": enterprise_size,
            "Business Nature": buisness_nature,
            "Industry Type": industry_type,
            "Plant & Machinery(Rs)": plant_machinery,
            "Building & Civil Work (Rs)": building_civil_work,
            "Land Cost (Rs.)": land_cost,
            "Term Loan Amount (Rs)": term_loan_amount,
            "Loan tenure": loan_tenure,
            "SGST Paid (Rs.)": net_sgst_paid_cash_ledger
        }

        for k, v in inputs.items():
            pdf.cell(200, 8, txt=f"{k}: {v}", ln=True)

        pdf.ln(5)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(200, 10, txt="Subsidy Calculation Result", ln=True)

        pdf.set_font("Arial", "", 11)
        for k, v in result.items():
            pdf.cell(200, 8, txt=f"{k}: Rs.{v:,.2f}", ln=True)

        file_path = "/tmp/Subsidy_Calculation_Report.pdf"
        pdf.output(file_path)

        # Send email
        msg = EmailMessage()
        msg['Subject'] = "Subsidy Calculation Report"
        msg['From'] = os.getenv("SMTP_USER")  # your-email@yourdomain.com
        msg['To'] = user_email

        msg.set_content("Dear {},\n\nPlease find attached your subsidy calculation report.".format(user_name))

        with open(file_path, "rb") as f:
            msg.add_attachment(f.read(), maintype="application", subtype="pdf", filename="Subsidy_Calculation_Report.pdf")

        with smtplib.SMTP_SSL("smtp.zoho.in", 465) as smtp:
            smtp.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASS"))
            smtp.send_message(msg)

        return jsonify({"status": "success", "result": result})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
