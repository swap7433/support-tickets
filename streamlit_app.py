import datetime
import pandas as pd
import streamlit as st
import os
import altair as alt

# App configuration
st.set_page_config(page_title="Support Tickets", page_icon="🎫")

# Departments - added "Exam Cell"
departments = ["Comp", "Mech", "Electronic", "Civil", "IT", "Exam Cell"]
TICKET_FILE = "tickets.xlsx"
POC_FILE = "poc_details.xlsx"

# --- Load or initialize POC DataFrame ---
def load_or_init_poc():
    if os.path.exists(POC_FILE):
        poc_df = pd.read_excel(POC_FILE)
        # Ensure all departments present
        missing_depts = [d for d in departments if d not in poc_df["Department"].values]
        for md in missing_depts:
            poc_df = pd.concat(
                [poc_df, pd.DataFrame({"Department": [md], "POC Name": ["No Name"], "POC Phone": ["0000000000"]})],
                ignore_index=True,
            )
        # Convert POC Phone to string to avoid Streamlit editing issues
        poc_df["POC Phone"] = poc_df["POC Phone"].astype(str)
        return poc_df
    else:
        # Initialize dummy POC details for all departments
        data = {
            "Department": departments,
            "POC Name": ["No Name"] * len(departments),
            "POC Phone": ["0000000000"] * len(departments),
        }
        poc_df = pd.DataFrame(data)
        # Ensure POC Phone is string type
        poc_df["POC Phone"] = poc_df["POC Phone"].astype(str)
        poc_df.to_excel(POC_FILE, index=False)
        return poc_df

poc_df = load_or_init_poc()

# Load or initialize DataFrame for tickets
if "df" not in st.session_state:
    if os.path.exists(TICKET_FILE):
        st.session_state.df = pd.read_excel(TICKET_FILE)
        # Keep only TICKET-1101, discard others (optional, can remove this filter if you want all tickets)
        st.session_state.df = st.session_state.df[st.session_state.df["ID"] == "TICKET-1101"]
        st.session_state.df.to_excel(TICKET_FILE, index=False)
    else:
        # Initialize with just one ticket TICKET-1101
        data = {
            "ID": ["TICKET-1101"],
            "Issue": ["Sample issue for TICKET-1101"],
            "Status": ["Open"],
            "Priority": ["Medium"],
            "Date Submitted": [datetime.date(2023, 6, 1)],
            "Full Name": ["John Doe"],
            "Mobile No": ["1234567890"],
            "Department": ["Comp"],
            "Resolution": [""],
        }
        st.session_state.df = pd.DataFrame(data)
        st.session_state.df.to_excel(TICKET_FILE, index=False)

# Convert 'ID' column to string to avoid dtype issues
st.session_state.df["ID"] = st.session_state.df["ID"].astype(str)

# Sidebar for user role selection
st.sidebar.title("Navigation")
user_role = st.sidebar.selectbox("Select user type", ["User", "Admin"])

# =============== USER TAB ================
if user_role == "User":
    st.title("🎫 Support Ticket Portal")

    # --- Add Ticket Section ---
    st.header("Add a ticket")
    with st.form("add_ticket_form"):
        full_name = st.text_input("Full Name")
        mobile = st.text_input("Mobile No")
        dept = st.selectbox("Department", departments)
        issue = st.text_area("Describe the issue")
        priority = st.selectbox("Priority", ["High", "Medium", "Low"])
        submitted = st.form_submit_button("Submit")

    if submitted:
        # Calculate next ticket number
        try:
            recent_ticket_number = max(
                st.session_state.df["ID"].str.split("-").str[1].astype(int)
            )
        except Exception:
            recent_ticket_number = 1101  # fallback default
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
        st.dataframe(df_new, use_container_width=True, hide_index=True)  # Shows new ticket

        # Show POC details for submitted department
        poc_row = poc_df[poc_df["Department"] == dept]
        st.markdown(
            f"### Contact POC for **{dept}** Department\n"
            f"- **Name:** {poc_row['POC Name'].values[0]}\n"
            f"- **Phone No:** {poc_row['POC Phone'].values[0]}"
        )

    # --- Search Ticket Section ---
    st.header("Search tickets")
    search_term = st.text_input("Search by keyword or ticket ID")
    if search_term:
        result_df = st.session_state.df[
            st.session_state.df["ID"].str.contains(search_term, case=False)
            | st.session_state.df["Issue"].str.contains(search_term, case=False)
        ]
        st.write(f"Found {len(result_df)} matching tickets:")
        st.dataframe(result_df, use_container_width=True, hide_index=True)  # Shows all columns

# =============== ADMIN TAB ================
elif user_role == "Admin":
    st.title("🔐 Admin Dashboard")
    dept_login = st.selectbox("Select Department", ["Super Admin"] + departments)
    password = st.text_input("Enter admin password", type="password")

    if password == "admin123":  # Use secure method in production
        st.success("Access granted")

        # For departments other than super admin, filter tickets accordingly
        if dept_login != "Super Admin":
            df_filtered = st.session_state.df[
                st.session_state.df["Department"] == dept_login
            ].copy()
        else:
            df_filtered = st.session_state.df.copy()

        # Admin Search box
        search_term_admin = st.text_input("Search tickets (ID or keyword)", key="admin_search")
        if search_term_admin:
            df_filtered = df_filtered[
                df_filtered["ID"].str.contains(search_term_admin, case=False)
                | df_filtered["Issue"].str.contains(search_term_admin, case=False)
            ]

        # Show department POC info for department admins (not super admin)
        if dept_login != "Super Admin":
            poc_row = poc_df[poc_df["Department"] == dept_login]
            st.markdown(
                f"### POC for **{dept_login}** Department\n"
                f"- **Name:** {poc_row['POC Name'].values[0]}\n"
                f"- **Phone No:** {poc_row['POC Phone'].values[0]}"
            )

        # If Super Admin, show graphs + delete tickets tab
        if dept_login == "Super Admin":
            st.header("📊 Support Tickets Overview")

            # Tickets count by Department
            dept_counts = df_filtered["Department"].value_counts().reset_index()
            dept_counts.columns = ["Department", "Count"]
            dept_chart = alt.Chart(dept_counts).mark_bar().encode(
                x=alt.X("Department", sort="-y"),
                y="Count",
                tooltip=["Department", "Count"],
                color=alt.Color("Department", legend=None),
            ).properties(title="Tickets by Department")
            st.altair_chart(dept_chart, use_container_width=True)

            # Tickets count by Status
            status_counts = df_filtered["Status"].value_counts().reset_index()
            status_counts.columns = ["Status", "Count"]
            status_chart = alt.Chart(status_counts).mark_bar(color="#1f77b4").encode(
                x=alt.X("Status", sort="-y"),
                y="Count",
                tooltip=["Status", "Count"],
                color=alt.Color("Status", legend=None),
            ).properties(title="Tickets by Status")
            st.altair_chart(status_chart, use_container_width=True)

            # Tickets count by Priority
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

        # Notification box bottom-right corner with ticket count
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

        # Add some padding and bigger scrollbar to the data editor with custom CSS
        st.markdown(
            """
            <style>
            /* Increase padding for table cells */
            div[data-testid="stDataEditorContainer"] div[data-baseweb="table-cell"] {
                padding: 12px 15px !important;
            }
            /* Customize scrollbar */
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

        # Save changes back to session_state.df but only for tickets visible to this admin
        if dept_login == "Super Admin":
            # Update entire df for superadmin edits
            st.session_state.df.update(edited_df)
        else:
            # Update only rows for this department
            idxs = st.session_state.df[st.session_state.df["Department"] == dept_login].index
            st.session_state.df.loc[idxs, :] = edited_df.values

        # Save updated dataframe to Excel
        st.session_state.df.to_excel(TICKET_FILE, index=False)

        # POC edit only for Super Admin
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

        # DELETE TICKETS - only for Super Admin
        if dept_login == "Super Admin":
            st.header("🗑️ Delete Tickets")

            ticket_to_delete = st.selectbox(
                "Select ticket to delete", options=st.session_state.df["ID"].tolist()
            )
            if st.button("Delete Ticket"):
                # Confirm delete
                if ticket_to_delete:
                    st.session_state.df = st.session_state.df[
                        st.session_state.df["ID"] != ticket_to_delete
                    ]
                    st.session_state.df.to_excel(TICKET_FILE, index=False)
                    st.success(f"Ticket {ticket_to_delete} deleted!")

    else:
        st.warning("Enter correct admin password to access admin features.")
