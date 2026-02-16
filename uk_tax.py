import streamlit as st
import plotly.graph_objects as go
import pandas as pd

# --- Page Setup ---
st.set_page_config(page_title="UK Tax Master 2026", page_icon="🎯", layout="centered")

# --- Constants ---
ANN_PEN_ALLOWANCE = 60000

# --- Core Logic Engine ---
def calculate_finances(gross, bonus, ee_pct, er_pct, p_on_b, ev_lease, ev_p11d, other_sac_m, kids):
    total_gross = gross + bonus
    pensionable = gross + (bonus if p_on_b else 0)
    ann_ee_pen = pensionable * (ee_pct / 100)
    ann_er_pen = pensionable * (er_pct / 100)
    
    # Yearly values
    ann_ev_lease = ev_lease * 12
    ann_other_sac = other_sac_m * 12
    
    taxable_gross = total_gross - ann_ee_pen - ann_ev_lease - ann_other_sac
    bik_val = ev_p11d * 0.02
    adj_net_income = taxable_gross + bik_val
    
    # PA Taper
    pa = 12570
    if adj_net_income > 100000:
        pa = max(0, pa - (adj_net_income - 100000) / 2)
    
    # Income Tax
    rem = max(0, adj_net_income - pa)
    tax = 0
    for limit, rate in [(37700, 0.2), (74870, 0.4), (float('inf'), 0.45)]:
        chunk = min(rem, limit)
        tax += chunk * rate
        rem -= chunk
        if rem <= 0: break
    
    # NI
    ni = 0
    if taxable_gross > 12570: ni += (min(taxable_gross, 50270) - 12570) * 0.08
    if taxable_gross > 50270: ni += (taxable_gross - 50270) * 0.02
    
    # High Income Child Benefit Charge (HICBC)
    cb_charge = 0
    if kids > 0 and adj_net_income > 60000:
        total_cb = 1331.20 + ((kids - 1) * 881.40 if kids > 1 else 0)
        charge_pct = min(1.0, (adj_net_income - 60000) / 20000)
        cb_charge = total_cb * charge_pct
        
    take_home = taxable_gross - tax - ni - cb_charge
    total_pot = ann_ee_pen + ann_er_pen
    
    return {
        "take_home": take_home, "tax": tax, "ni": ni, "cb_charge": cb_charge,
        "ee_pen": ann_ee_pen, "er_pen": ann_er_pen, "total_pot": total_pot,
        "adj_net": adj_net_income, "total_package": total_gross + ann_er_pen,
        "er_pen_val": ann_er_pen
    }

# --- Sidebar UI (Hybrid Inputs Restored) ---
with st.sidebar:
    st.header("💵 1. Salary & Bonus")
    s_base_input = st.number_input("Base Salary (£)", value=110000, step=1000)
    s_base = st.slider("Fine-tune Base", 10000, 250000, int(s_base_input), label_visibility="collapsed")
    
    b_type = st.radio("Bonus Format", ["Amount (£)", "Percentage (%)"])
    if b_type == "Amount (£)":
        b_amt_input = st.number_input("Bonus Amount (£)", value=0, step=500)
        s_bonus = st.slider("Fine-tune Bonus", 0, 100000, int(b_amt_input), label_visibility="collapsed")
    else:
        b_pct_input = st.number_input("Bonus %", value=0.0, step=0.5)
        b_pct = st.slider("Fine-tune Bonus %", 0.0, 100.0, float(b_pct_input), label_visibility="collapsed")
        s_bonus = s_base * (b_pct / 100)

    st.header("👶 2. Family")
    kids = st.slider("Number of Children", 0, 5, 0)

    st.header("🏦 3. Pension & EV")
    s_ee_p = st.slider("Your Pension %", 0, 80, 5)
    s_er_p = st.slider("Employer Pension %", 0, 20, 3)
    s_p_on_b = st.toggle("Pension on Bonus", value=True)
    
    s_ev_m = st.number_input("Monthly EV Lease (£)", value=0)
    s_p11d = st.number_input("Car P11D Value (£)", value=40000)
    s_other = st.number_input("Other Sacrifice (£/mo)", value=0)

# --- Process Results ---
res_ev = calculate_finances(s_base, s_bonus, s_ee_p, s_er_p, s_p_on_b, s_ev_m, s_p11d, s_other, kids)
res_no = calculate_finances(s_base, s_bonus, s_ee_p, s_er_p, s_p_on_b, 0, 0, s_other, kids)

# --- Main Tabs ---
tab1, tab2, tab3, tab4 = st.tabs(["💰 Dashboard", "🔄 Comparison", "🚀 Optimizer", "📄 Export"])

with tab1:
    st.title(f"£{res_ev['take_home']/12:,.2f}")
    st.caption("Monthly Net Take Home")
    
    fig = go.Figure(data=[go.Pie(
        labels=['Take Home', 'Tax', 'NI', 'EE Pension', 'EV Sacrifice', 'CB Charge'],
        values=[res_ev['take_home'], res_ev['tax'], res_ev['ni'], res_ev['ee_pen'], s_ev_m*12, res_ev['cb_charge']],
        hole=.5, marker_colors=['#00CC96', '#EF553B', '#636EFA', '#AB63FA', '#FFA15A', '#FF6666']
    )])
    fig.update_layout(margin=dict(t=30, b=0, l=0, r=0))
    st.plotly_chart(fig, width='stretch')

with tab2:
    st.subheader("Comparison: EV & Child Benefit Impact")
    comp_df = pd.DataFrame({
        "Metric": ["Monthly Net", "Annual Net", "Income Tax", "Nat. Insurance", "CB Charge", "Total Package Value"],
        "Without EV": [f"£{res_no['take_home']/12:,.2f}", f"£{res_no['take_home']:,.2f}", f"£{res_no['tax']:,.2f}", f"£{res_no['ni']:,.2f}", f"£{res_no['cb_charge']:,.2f}", f"£{res_no['total_package']:,.2f}"],
        "With EV": [f"£{res_ev['take_home']/12:,.2f}", f"£{res_ev['take_home']:,.2f}", f"£{res_ev['tax']:,.2f}", f"£{res_ev['ni']:,.2f}", f"£{res_ev['cb_charge']:,.2f}", f"£{res_ev['total_package']:,.2f}"]
    })
    st.table(comp_df)
    
    eff_cost = (res_no['take_home'] - res_ev['take_home']) / 12
    st.info(f"💡 Lease is £{s_ev_m}, but your take-home only drops by **£{eff_cost:,.2f}**.")

with tab3:
    st.subheader("Smart Optimization")
    
    # Tax Trap Resolver
    if 100000 < res_ev['adj_net'] < 125140:
        st.error(f"⚠️ **60% Tax Trap Detected!**")
        top_up = res_ev['adj_net'] - 100000
        st.write(f"Add **£{top_up:,.0f}** to your pension to save your Personal Allowance.")
        if st.button("Fix Tax Trap"):
            new_ee_p = ((res_ev['ee_pen'] + top_up) / (s_base + (s_bonus if s_p_on_b else 0))) * 100
            st.success(f"New Pension Target: **{new_ee_p:.1f}%**")
    
    # Pension Allowance Tracker
    st.divider()
    st.subheader("Pension Allowance Tracker")
    usage = (res_ev['total_pot'] / ANN_PEN_ALLOWANCE)
    st.progress(usage if usage <= 1 else 1.0)
    st.metric("Remaining Allowance", f"£{ANN_PEN_ALLOWANCE - res_ev['total_pot']:,.2f}")

with tab4:
    csv = comp_df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download CSV", data=csv, file_name="tax_analysis.csv")
