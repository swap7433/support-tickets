import datetime 
import pandas as pd
import streamlit as st
import os
import altair as alt
import openai

# App configuration
st.set_page_config(page_title="Support Tickets", page_icon="🎫", layout="wide")

# Departments
departments = ["Comp", "Mech", "Electronic", "Civil", "IT", "Exam Cell"]
TICKET_FILE = "tickets.xlsx"
POC_FILE = "poc_details.xlsx"

# --- Load or initialize POC DataFrame ---
def load_or_init_poc():
    if os.path.exists(POC_FILE):
        poc_df = pd.read_excel(POC_FILE)
        missing_depts = [d for d in departments if d not in poc_df["Department"].values]
        for md in missing_depts:
            poc_df = pd.concat(
                [poc_df, pd.DataFrame({"Department": [md], "POC Name": ["No Name"], "POC Phone": ["0000000000"]})],
                ignore_index=True,
            )
        poc_df["POC Phone"] = poc_df["POC Phone"].astype(str)
        return poc_df
    else:
        data = {
            "Department": departments,
            "POC Name": ["No Name"] * len(departments),
            "POC Phone": ["0000000000"] * len(departments),
        }
        poc_df = pd.DataFrame(data)
        poc_df["POC Phone"] = poc_df["POC Phone"].astype(str)
        poc_df.to_excel(POC_FILE, index=False)
        return poc_df

poc_df = load_or_init_poc()

if "df" not in st.session_state:
    if os.path.exists(TICKET_FILE):
        st.session_state.df = pd.read_excel(TICKET_FILE)
    else:
        data = {
            "ID": [],
            "Issue": [],
            "Status": [],
            "Priority": [],
            "Date Submitted": [],
            "Full Name": [],
            "Mobile No": [],
            "Department": [],
            "Resolution": [],
        }
        st.session_state.df = pd.DataFrame(data)
        st.session_state.df.to_excel(TICKET_FILE, index=False)
st.session_state.df["ID"] = st.session_state.df["ID"].astype(str)


# ---------- TAB-BASED NAVIGATION ----------
tabs = st.tabs(["Submit Ticket", "Admin Panel", "Chatbot"])


# =============== USER TAB ================
with tabs[0]:
    st.title("🎫 Support Ticket Portal")
    st.header("Add a ticket")
    with st.form("add_ticket_form"):
        full_name = st.text_input("Full Name")
        mobile = st.text_input("Mobile No")
        dept = st.selectbox("Department", departments)
        issue = st.text_area("Describe the issue")
        priority = st.selectbox("Priority", ["High", "Medium", "Low"])
        submitted = st.form_submit_button("Submit")

    if submitted:
        try:
            recent_ticket_number = max(
                st.session_state.df["ID"].str.split("-").str[1].astype(int)
            )
        except Exception:
            recent_ticket_number = 1101
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        df_new = pd.DataFrame(
            [
                {
                    "ID": f"TICKET-{recent_ticket_number + 1}",
                    "Issue": issue,
                    "Status": "Open",
                    "Priority": priority,
                    "Date Submitted": today,
                    "Full Name": full_name,
                    "Mobile No": mobile,
                    "Department": dept,
                    "Resolution": "",
                }
            ]
        )
        st.session_state.df = pd.concat([df_new, st.session_state.df], axis=0)
        st.session_state.df.to_excel(TICKET_FILE, index=False)
        st.success("Ticket submitted!")
        st.dataframe(df_new, use_container_width=True, hide_index=True)

        poc_row = poc_df[poc_df["Department"] == dept]
        st.markdown(
            f"### Contact POC for **{dept}** Department\n"
            f"- **Name:** {poc_row['POC Name'].values[0]}\n"
            f"- **Phone No:** {poc_row['POC Phone'].values[0]}"
        )

    st.header("Search tickets")
    search_term = st.text_input("Search by keyword or ticket ID")
    if search_term:
        result_df = st.session_state.df[
            st.session_state.df["ID"].str.contains(search_term, case=False)
            | st.session_state.df["Issue"].str.contains(search_term, case=False)
        ]
        st.write(f"Found {len(result_df)} matching tickets:")
        st.dataframe(result_df, use_container_width=True, hide_index=True)


# =============== ADMIN TAB ================
with tabs[1]:
    st.title("🔐 Admin Dashboard")
    dept_login = st.selectbox("Select Department", ["Super Admin"] + departments)
    password = st.text_input("Enter admin password", type="password")

    if password == "admin123":
        st.success("Access granted")

        if dept_login != "Super Admin":
            df_filtered = st.session_state.df[
                st.session_state.df["Department"] == dept_login
            ].copy()
        else:
            df_filtered = st.session_state.df.copy()

        search_term_admin = st.text_input("Search tickets (ID or keyword)", key="admin_search")
        if search_term_admin:
            df_filtered = df_filtered[
                df_filtered["ID"].str.contains(search_term_admin, case=False)
                | df_filtered["Issue"].str.contains(search_term_admin, case=False)
            ]

        if dept_login != "Super Admin":
            poc_row = poc_df[poc_df["Department"] == dept_login]
            st.markdown(
                f"### POC for **{dept_login}** Department\n"
                f"- **Name:** {poc_row['POC Name'].values[0]}\n"
                f"- **Phone No:** {poc_row['POC Phone'].values[0]}"
            )

        if dept_login == "Super Admin":
            st.header("📊 Support Tickets Overview")

            dept_counts = df_filtered["Department"].value_counts().reset_index()
            dept_counts.columns = ["Department", "Count"]
            dept_chart = alt.Chart(dept_counts).mark_bar().encode(
                x=alt.X("Department", sort="-y"),
                y="Count",
                tooltip=["Department", "Count"],
                color=alt.Color("Department", legend=None),
            ).properties(title="Tickets by Department")
            st.altair_chart(dept_chart, use_container_width=True)

            status_counts = df_filtered["Status"].value_counts().reset_index()
            status_counts.columns = ["Status", "Count"]
            status_chart = alt.Chart(status_counts).mark_bar(color="#1f77b4").encode(
                x=alt.X("Status", sort="-y"),
                y="Count",
                tooltip=["Status", "Count"],
                color=alt.Color("Status", legend=None),
            ).properties(title="Tickets by Status")
            st.altair_chart(status_chart, use_container_width=True)

            priority_counts = df_filtered["Priority"].value_counts().reset_index()
            priority_counts.columns = ["Priority", "Count"]
            priority_chart = alt.Chart(priority_counts).mark_bar(color="#ff7f0e").encode(
                x=alt.X("Priority", sort="-y"),
                y="Count",
                tooltip=["Priority", "Count"],
                color=alt.Color("Priority", legend=None),
            ).properties(title="Tickets by Priority")
            st.altair_chart(priority_chart, use_container_width=True)

        st.header(f"Tickets for {dept_login}")
        st.write(f"Total Tickets: `{len(df_filtered)}`")

        if len(df_filtered) > 0:
            st.sidebar.markdown(
                f"""
                <div style="
                    position: fixed; 
                    bottom: 10px; 
                    right: 10px; 
                    background-color: #90ee90; 
                    padding: 10px; 
                    border-radius: 5px; 
                    box-shadow: 0 0 5px gray;
                    font-weight: bold;
                    z-index: 9999;
                ">
                    {len(df_filtered)} ticket(s) in {dept_login} department
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown(
            """
            <style>
            div[data-testid="stDataEditorContainer"] div[data-baseweb="table-cell"] {
                padding: 12px 15px !important;
            }
            div[data-testid="stDataEditorContainer"]::-webkit-scrollbar {
                height: 16px;
                width: 16px;
            }
            div[data-testid="stDataEditorContainer"]::-webkit-scrollbar-thumb {
                background: #888;
                border-radius: 8px;
            }
            div[data-testid="stDataEditorContainer"]::-webkit-scrollbar-thumb:hover {
                background: #555;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        edited_df = st.data_editor(
            df_filtered,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
        )

        if dept_login == "Super Admin":
            st.session_state.df.update(edited_df)
        else:
            idxs = st.session_state.df[st.session_state.df["Department"] == dept_login].index
            st.session_state.df.loc[idxs, :] = edited_df.values

        st.session_state.df.to_excel(TICKET_FILE, index=False)

        if dept_login == "Super Admin":
            st.header("📝 Edit POC Details")
            edited_poc = st.data_editor(
                poc_df,
                num_rows="dynamic",
                use_container_width=True,
                hide_index=True,
            )
            if not edited_poc.equals(poc_df):
                poc_df = edited_poc.copy()
                poc_df.to_excel(POC_FILE, index=False)
                st.success("POC details updated!")

            st.header("🗑️ Delete Tickets")
            ticket_to_delete = st.selectbox(
                "Select ticket to delete", options=st.session_state.df["ID"].tolist()
            )
            if st.button("Delete Ticket"):
                if ticket_to_delete:
                    st.session_state.df = st.session_state.df[
                        st.session_state.df["ID"] != ticket_to_delete
                    ]
                    st.session_state.df.to_excel(TICKET_FILE, index=False)
                    st.success(f"Ticket {ticket_to_delete} deleted!")
    else:
        st.warning("Enter correct admin password to access admin features.")



import openai
from openai import OpenAI  # For new client-based usage

# ... inside your chatbot tab ...
with tabs[2]:
    st.title("🤖 Ticket Chatbot Assistant")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    def format_df_as_md_table(df):
        if df.empty:
            return "No data available."
        return df.to_markdown(index=False)

    def handle_chat_input(user_input):
        input_lower = user_input.lower().strip()

        # Handle POC listing
        if "poc" in input_lower and ("list" in input_lower or "show" in input_lower):
            return "Here are all the Points of Contact (POCs):", poc_df[["Department", "POC Name", "POC Phone"]]

        # Handle ticket listing
        elif "ticket" in input_lower and ("list" in input_lower or "show" in input_lower):
            if st.session_state.df.empty:
                return "No tickets found.", pd.DataFrame()
            return f"Here are all the tickets ({len(st.session_state.df)} total):", st.session_state.df[
                ["ID", "Issue", "Status", "Priority", "Department"]
            ]

        # Handle ticket status by ID
        elif "status" in input_lower and "ticket" in input_lower:
            words = input_lower.split()
            ticket_ids = [word for word in words if word.startswith("ticket")]
            if ticket_ids:
                ticket_id = ticket_ids[0].upper()
                ticket_row = st.session_state.df[st.session_state.df["ID"] == ticket_id]
                if not ticket_row.empty:
                    status = ticket_row.iloc[0]["Status"]
                    return f"Status of {ticket_id} is **{status}**.", ticket_row[["ID", "Status", "Priority", "Issue","Resolution"]]
                else:
                    return f"Ticket ID {ticket_id} not found.", pd.DataFrame()
            else:
                return "Please specify a valid Ticket ID (e.g., 'ticket-1101').", pd.DataFrame()

        else:
            return "Sorry, I didn't understand your query. You can ask things like:\n- 'list all the tickets'\n- 'list all the POCs'\n- 'status of ticket-1101'", pd.DataFrame()

    user_input = st.text_input("Ask me something about tickets or POCs:")

    if user_input:
        answer_text, answer_df = handle_chat_input(user_input)
        st.session_state.chat_history.append(("User", user_input))
        st.session_state.chat_history.append(("Bot", answer_text))

        # Display the conversation
        for sender, message in st.session_state.chat_history:
            if sender == "User":
                st.markdown(f"🧑‍💼 **{sender}:** {message}")
            else:
                st.markdown(f"🤖 **{sender}:** {message}")
        if not answer_df.empty:
            st.dataframe(answer_df, use_container_width=True)

        if st.button("Clear Chat History"):
            st.session_state['chat_history'] = []
            # Display a message to refresh manually because st.experimental_rerun() is missing
            st.info("Chat history cleared! Please refresh the page to see the changes.")

