import streamlit as st
import plotly.graph_objects as go
import pandas as pd

# --- 2026 Mobile-First Styling ---
st.set_page_config(page_title="UK Tax Master", page_icon="💰", layout="centered")

# Custom CSS for a "Premium App" feel
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 42px !important; font-weight: 700 !important; color: #00CC96; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { 
        background-color: #f0f2f6; border-radius: 8px; padding: 10px 20px; border: none;
    }
    .stTabs [aria-selected="true"] { background-color: #00CC96 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- Constants ---
ANN_PEN_ALLOWANCE = 60000

# --- Core Logic Engine ---
def calculate_finances(gross, bonus, ee_pct, er_pct, p_on_b, ev_lease, ev_p11d, other_sac_m, kids):
    total_gross = gross + bonus
    pensionable = gross + (bonus if p_on_b else 0)
    ann_ee_pen = pensionable * (ee_pct / 100)
    ann_er_pen = pensionable * (er_pct / 100)
    
    ann_ev_lease = ev_lease * 12
    ann_other_sac = other_sac_m * 12
    
    taxable_gross = total_gross - ann_ee_pen - ann_ev_lease - ann_other_sac
    bik_val = ev_p11d * 0.02
    adj_net_income = taxable_gross + bik_val
    
    # Personal Allowance Taper
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
    
    # Child Benefit Charge
    cb_charge = 0
    if kids > 0 and adj_net_income > 60000:
        total_cb = 1331.20 + ((kids - 1) * 881.40 if kids > 1 else 0)
        charge_pct = min(1.0, (adj_net_income - 60000) / 20000)
        cb_charge = total_cb * charge_pct
        
    take_home = taxable_gross - tax - ni - cb_charge
    return {
        "take_home": take_home, "tax": tax, "ni": ni, "cb_charge": cb_charge,
        "ee_pen": ann_ee_pen, "er_pen": ann_er_pen, "total_pot": ann_ee_pen + ann_er_pen,
        "adj_net": adj_net_income, "total_package": total_gross + ann_er_pen
    }

# --- Main UI Dashboard ---
st.title("🇬🇧 UK Tax Master")

# 1. Input Cards (Expanders)
with st.expander("💸 Salary & Bonus", expanded=True):
    s_base = st.number_input("Base Salary (£)", value=110000, step=1000)
    b_type = st.segmented_control("Bonus Type", ["Amount (£)", "Percentage (%)"], default="Amount (£)")
    if b_type == "Amount (£)":
        s_bonus = st.number_input("Bonus Amount (£)", value=0, step=500)
    else:
        b_pct = st.number_input("Bonus %", value=0.0, step=0.5)
        s_bonus = s_base * (b_pct / 100)

with st.expander("🏦 Pension & Family"):
    # Pills for quick selection
    ee_p = st.segmented_control("Your Pension %", [0, 3, 5, 8, 10, 15, 20, 25], default=5)
    if ee_p is None: ee_p = st.number_input("Manual Pension %", 0, 80, 5)
    
    er_p = st.number_input("Employer Contribution %", 0, 25, 3)
    p_on_b = st.toggle("Pension on Bonus", value=True)
    kids = st.segmented_control("Children", [0, 1, 2, 3, 4], default=0)

with st.expander("⚡ EV & Extras"):
    s_ev_m = st.number_input("Monthly EV Lease (£)", value=0)
    s_p11d = st.number_input("Car P11D Value (£)", value=40000)
    s_other = st.number_input("Other Sacrifice (£/mo)", value=0)

# --- Process Calculations ---
res = calculate_finances(s_base, s_bonus, ee_p, er_p, p_on_b, s_ev_m, s_p11d, s_other, kids)
res_no = calculate_finances(s_base, s_bonus, ee_p, er_p, p_on_b, 0, 0, s_other, kids)

st.divider()

# 2. Key Result
st.metric("Monthly Take Home", f"£{res['take_home']/12:,.2f}")

# 3. Interactive Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📊 Split", "🔄 Compare", "🚀 Optimizer", "📄 Details"])

with tab1:
    fig = go.Figure(data=[go.Pie(
        labels=['Take Home', 'Tax', 'NI', 'EE Pension', 'EV Lease', 'CB Charge'],
        values=[res['take_home'], res['tax'], res['ni'], res['ee_pen'], s_ev_m*12, res['cb_charge']],
        hole=.5, marker_colors=['#00CC96', '#EF553B', '#636EFA', '#AB63FA', '#FFA15A', '#FF6666']
    )])
    fig.update_layout(margin=dict(t=30, b=0, l=0, r=0), legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig, width='stretch')

with tab2:
    st.subheader("Comparison: With vs Without EV")
    comp_df = pd.DataFrame({
        "Metric": ["Monthly Net", "Annual Net", "Total Tax", "CB Charge", "Total Value"],
        "Current": [f"£{res['take_home']/12:,.2f}", f"£{res['take_home']:,.2f}", f"£{res['tax']+res['ni']:,.2f}", f"£{res['cb_charge']:,.2f}", f"£{res['total_package']:,.2f}"],
        "No EV": [f"£{res_no['take_home']/12:,.2f}", f"£{res_no['take_home']:,.2f}", f"£{res_no['tax']+res_no['ni']:,.2f}", f"£{res_no['cb_charge']:,.2f}", f"£{res_no['total_package']:,.2f}"]
    })
    st.table(comp_df)
    
    eff_cost = (res_no['take_home'] - res['take_home']) / 12
    st.info(f"💡 Real monthly cost of car: **£{eff_cost:,.2f}**")

with tab3:
    st.subheader("Actionable Insights")
    
    # Tax Trap Resolver
    if 100000 < res['adj_net'] < 125140:
        st.error("🚨 60% Tax Trap Active")
        top_up = res['adj_net'] - 100000
        st.write(f"Top up pension by **£{top_up:,.0f}** to save your Personal Allowance.")
        if st.button("Fix the Trap"):
            new_ee_p = ((res['ee_pen'] + top_up) / (s_base + (s_bonus if p_on_b else 0))) * 100
            st.success(f"New Target: {new_ee_p:.1f}%")

    # Child Benefit Warning
    if res['cb_charge'] > 0:
        st.warning(f"Child Benefit Charge is costing you **£{res['cb_charge']:,.2f}/yr**.")

    st.divider()
    st.subheader("Pension Tracker")
    usage = (res['total_pot'] / ANN_PEN_ALLOWANCE)
    st.progress(usage if usage <= 1 else 1.0)
    st.metric("Remaining Allowance", f"£{ANN_PEN_ALLOWANCE - res['total_pot']:,.2f}")

with tab4:
    csv = comp_df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Export CSV", data=csv, file_name="uk_tax_export.csv")
    st.caption("Calculated based on 2025/26 UK Tax Rules.")
