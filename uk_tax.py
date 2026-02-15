import streamlit as st
import plotly.graph_objects as go

# --- Page Config ---
st.set_page_config(page_title="UK Tax & EV Savings", page_icon="⚡", layout="centered")

def calc_logic(gross, bonus, ee_p, er_p, ev_lease_monthly, p11d):
    # Calculations
    total_gross = gross + bonus
    ann_ev_lease = ev_lease_monthly * 12
    ee_pen_ann = total_gross * (ee_p / 100)
    er_pen_ann = total_gross * (er_p / 100)
    
    # Taxable Gross (assuming Sal Sac for EV and Pension)
    taxable_gross = total_gross - ann_ev_lease - ee_pen_ann
    
    # BiK (Benefit in Kind) - 2% of P11D for EVs
    bik_value = p11d * 0.02
    
    # Adjusted Net Income (includes BiK for Personal Allowance testing)
    adj_net_income = taxable_gross + bik_value
    
    # Personal Allowance Taper
    pa = 12570
    if adj_net_income > 100000:
        pa = max(0, pa - (adj_net_income - 100000) / 2)
        
    # Income Tax
    taxable_pot = max(0, adj_net_income - pa)
    tax = 0
    if taxable_pot > 0:
        b1 = min(taxable_pot, 37700) # 20% band
        tax += b1 * 0.20
        taxable_pot -= b1
        b2 = min(taxable_pot, 125140 - 50270) # 40% band
        tax += b2 * 0.40
        taxable_pot -= b2
        if taxable_pot > 0: tax += taxable_pot * 0.45
        
    # National Insurance (8% and 2%)
    ni = 0
    if taxable_gross > 12570:
        ni += (min(taxable_gross, 50270) - 12570) * 0.08
    if taxable_gross > 50270:
        ni += (taxable_gross - 50270) * 0.02
        
    take_home = taxable_gross - tax - ni
    return take_home, tax, ni, ee_pen_ann, er_pen_ann

# --- Sidebar Inputs ---
st.title("⚡ UK EV Salary Sacrifice Calculator")

with st.sidebar:
    st.header("Income & Pension")
    gross = st.number_input("Base Salary (£)", value=65000)
    bonus = st.number_input("Bonus (£)", value=0)
    ee_p = st.slider("Employee Pension %", 0, 20, 5)
    er_p = st.slider("Employer Pension %", 0, 20, 3)
    
    st.header("EV Scheme")
    lease = st.number_input("Monthly Gross Lease (£)", value=500)
    p11d = st.number_input("Car P11D Value (£)", value=45000)

# Calculate both scenarios
home_ev, tax_ev, ni_ev, pen_ev, er_ev = calc_logic(gross, bonus, ee_p, er_p, lease, p11d)
home_no, tax_no, ni_no, pen_no, er_no = calc_logic(gross, bonus, ee_p, er_p, 0, 0)

# --- Comparison View ---
st.subheader("Comparison: Monthly Impact")
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Without EV", f"£{home_no/12:,.2f}")
with col2:
    st.metric("With EV", f"£{home_ev/12:,.2f}")
with col3:
    real_cost = (home_no - home_ev) / 12
    st.metric("Effective Cost", f"£{real_cost:,.2f}", delta="- Tax Efficient")

st.info(f"💡 A **£{lease:,.0f}** lease only costs you **£{real_cost:,.2f}** in take-home pay because the taxman pays for the rest!")

# --- Detailed Table ---
st.write("### Yearly Breakdown")
comparison_data = {
    "Category": ["Gross Salary", "Income Tax", "Nat. Insurance", "Pension (Your Contribution)", "Monthly Take Home"],
    "Without EV": [f"£{gross+bonus:,.0f}", f"£{tax_no:,.0f}", f"£{ni_no:,.0f}", f"£{pen_no:,.0f}", f"£{home_no/12:,.2f}"],
    "With EV": [f"£{gross+bonus:,.0f}", f"£{tax_ev:,.0f}", f"£{ni_ev:,.0f}", f"£{pen_ev:,.0f}", f"£{home_ev/12:,.2f}"]
}
st.table(comparison_data)

# Visualization
fig = go.Figure()
fig.add_trace(go.Bar(name='No EV', x=['Tax', 'NI', 'Take Home'], y=[tax_no, ni_no, home_no], marker_color='#636EFA'))
fig.add_trace(go.Bar(name='With EV', x=['Tax', 'NI', 'Take Home'], y=[tax_ev, ni_ev, home_ev], marker_color='#00CC96'))
fig.update_layout(barmode='group', title="Yearly Impact on Tax and Income")
st.plotly_chart(fig, use_container_width=True)
