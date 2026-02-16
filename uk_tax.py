import streamlit as st
import plotly.graph_objects as go
import pandas as pd

# --- Page Setup ---
st.set_page_config(page_title="UK Tax Master 2026", page_icon="🎯", layout="centered")

# Custom CSS for Mobile Metrics
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 40px !important; font-weight: 700 !important; color: #00CC96; }
    .stExpander { border: 1px solid #e6e9ef; border-radius: 8px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- Constants ---
ANN_PEN_ALLOWANCE = 60000

# --- State Management (Save Profile) ---
if 'profile' not in st.session_state:
    st.session_state.profile = {
        "base": 110000, "bonus": 0, "ee_p": 5, "er_p": 3, "kids": 0
    }

# --- Core Logic Engine ---
def calculate_finances(gross, bonus, ee_pct, er_pct, p_on_b, ev_lease, ev_p11d, other_sac_m, kids):
    total_gross = gross + bonus
    pensionable = gross + (bonus if p_on_b else 0)
    ann_ee_pen = pensionable * (ee_pct / 100)
    ann_er_pen = pensionable * (er_pct / 100)
    
    ann_ev_lease, ann_other_sac = ev_lease * 12, other_sac_m * 12
    taxable_gross = total_gross - ann_ee_pen - ann_ev_lease - ann_other_sac
    bik_val = ev_p11d * 0.02
    adj_net_income = taxable_gross + bik_val
    
    pa = 12570
    if adj_net_income > 100000:
        pa = max(0, pa - (adj_net_income - 100000) / 2)
    
    rem = max(0, adj_net_income - pa)
    tax = 0
    for limit, rate in [(37700, 0.2), (74870, 0.4), (float('inf'), 0.45)]:
        chunk = min(rem, limit); tax += chunk * rate; rem -= chunk
        if rem <= 0: break
    
    ni = 0
    if taxable_gross > 12570: ni += (min(taxable_gross, 50270) - 12570) * 0.08
    if taxable_gross > 50270: ni += (taxable_gross - 50270) * 0.02
    
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

# --- Main UI ---
st.title("🇬🇧 UK Tax Master")

# 1. Salary & Bonus (Hybrid)
with st.expander("💸 Salary & Bonus", expanded=True):
    s_base_in = st.number_input("Base Salary (£)", value=st.session_state.profile["base"], step=1000)
    s_base = st.slider("Adjust Base Salary", 10000, 250000, int(s_base_in), label_visibility="collapsed")
    
    b_type = st.segmented_control("Bonus Type", ["Amount (£)", "Percentage (%)"], default="Amount (£)")
    if b_type == "Amount (£)":
        b_amt_in = st.number_input("Bonus Amount (£)", value=st.session_state.profile["bonus"], step=500)
        s_bonus = st.slider("Adjust Bonus Amount", 0, 100000, int(b_amt_in), label_visibility="collapsed")
    else:
        b_pct_in = st.number_input("Bonus %", value=0.0, step=0.5)
        b_pct = st.slider("Adjust Bonus %", 0.0, 100.0, float(b_pct_in), label_visibility="collapsed")
        s_bonus = s_base * (b_pct / 100)

# 2. Pension & Family
with st.expander("🏦 Pension & Family"):
    ee_p_in = st.number_input("Your Pension %", value=st.session_state.profile["ee_p"], step=1)
    ee_p = st.slider("Adjust Pension %", 0, 80, int(ee_p_in), label_visibility="collapsed")
    
    er_p_in = st.number_input("Employer Pension %", value=st.session_state.profile["er_p"], step=1)
    er_p = st.slider("Adjust Employer %", 0, 25, int(er_p_in), label_visibility="collapsed")
    
    # UPDATED DEFAULT: Set to False
    p_on_b = st.toggle("Pension on Bonus", value=False)
    kids = st.segmented_control("Number of Children", [0, 1, 2, 3, 4], default=st.session_state.profile["kids"])

# 3. EV & Sacrifice
with st.expander("⚡ EV & Extras"):
    s_ev_m = st.number_input("Monthly EV Lease (£)", value=0)
    # UPDATED DEFAULT: Set to 0
    s_p11d = st.number_input("Car P11D Value (£)", value=0)
    s_other = st.number_input("Other Sacrifice (£/mo)", value=0)

# Save Profile Logic
if st.button("💾 Save Profile (Local)"):
    st.session_state.profile = {"base": s_base, "bonus": s_bonus, "ee_p": ee_p, "er_p": er_p, "kids": kids}
    st.success("Profile saved! These values will load the next time you refresh.")

# --- Calculations ---
res = calculate_finances(s_base, s_bonus, ee_p, er_p, p_on_b, s_ev_m, s_p11d, s_other, kids)
res_no = calculate_finances(s_base, s_bonus, ee_p, er_p, p_on_b, 0, 0, s_other, kids)

st.divider()
st.metric("Monthly Take Home", f"£{res['take_home']/12:,.2f}")

# --- Tabs ---
tab1, tab2, tab3 = st.tabs(["📊 Split", "🔄 Compare", "🚀 Optimizer"])

with tab1:
    fig = go.Figure(data=[go.Pie(
        labels=['Take Home', 'Tax', 'NI', 'EE Pension', 'EV Lease', 'CB Charge'],
        values=[res['take_home'], res['tax'], res['ni'], res['ee_pen'], s_ev_m*12, res['cb_charge']],
        hole=.5, marker_colors=['#00CC96', '#EF553B', '#636EFA', '#AB63FA', '#FFA15A', '#FF6666']
    )])
    fig.update_layout(margin=dict(t=30, b=0, l=0, r=0), legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig, width='stretch')

with tab2:
    st.subheader("Scenario Comparison")
    comp_df = pd.DataFrame({
        "Metric": ["Monthly Net", "Annual Net", "Total Tax + NI", "CB Charge", "Total Value"],
        "Current": [f"£{res['take_home']/12:,.2f}", f"£{res['take_home']:,.2f}", f"£{res['tax']+res['ni']:,.2f}", f"£{res['cb_charge']:,.2f}", f"£{res['total_package']:,.2f}"],
        "No EV": [f"£{res_no['take_home']/12:,.2f}", f"£{res_no['take_home']:,.2f}", f"£{res_no['tax']+res_no['ni']:,.2f}", f"£{res_no['cb_charge']:,.2f}", f"£{res_no['total_package']:,.2f}"]
    })
    st.table(comp_df)

with tab3:
    if 100000 < res['adj_net'] < 125140:
        st.error("🚨 60% Tax Trap Active")
        top_up = res['adj_net'] - 100000
        st.write(f"Sacrifice **£{top_up:,.0f}** more to pension to recover your Personal Allowance.")
        if st.button("Calculate Target %"):
            target = ((res['ee_pen'] + top_up) / (s_base + (s_bonus if p_on_b else 0))) * 100
            st.success(f"Set Your Pension to: **{target:.1f}%**")
    
    st.divider()
    st.subheader("Pension Allowance")
    usage = (res['total_pot'] / ANN_PEN_ALLOWANCE)
    st.progress(usage if usage <= 1 else 1.0)
    st.metric("Remaining 60k Allowance", f"£{ANN_PEN_ALLOWANCE - res['total_pot']:,.2f}")
