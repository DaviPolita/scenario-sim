import streamlit as st
import datetime
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import numpy as np

from pulp import *
from sim_scripts import (
    convert_df_to_dict,
    calculate_item_results,
    calculate_group_results,
    split_results,
    get_table_download_link,
)


def main():

    #  selector for the app mode on the sidebar
    st.sidebar.title("What to do")
    app_mode = st.sidebar.selectbox(
        "Choose the app mode",
        ["Show Instructions", "Scenario Creation", "Scenario Comparison"],
    )
    if app_mode == "Show Instructions":
        st.markdown(get_file_content_as_string("README.md"))
        st.sidebar.success('To continue select "Scenario Creation".')
    elif app_mode == "Scenario Creation":
        create_scenario()
    elif app_mode == "Scenario Comparison":
        compare_scenario()


# @st.cache(show_spinner=False)
def get_file_content_as_string(filename):
    return Path(filename).read_text()


def create_scenario():

    project_date = datetime.datetime.now()
    st.title("Scenario Simulator _v2.2")
    file_name = st.text_input(
        "Project name (Used as the saved files filename)",
    )
    template_link = """ <a target="_blank" href="https://weg365-my.sharepoint.com/:x:/g/personal/davipolita_weg_net/EcRagwLBlexEhdUN0d_TERoBURc5OiscPfefktgrPC9FMg?download=1">Template file</a> """
    example_link = """ <a target="_blank" href="https://weg365-my.sharepoint.com/:x:/g/personal/davipolita_weg_net/EfcxkfbCMBpAusVRr1fZB7MBavRKleLlLT2mcnIYCvE_qw?download=1">Example file</a> """

    st.text("Click to downloda the template file:")
    st.markdown(template_link, unsafe_allow_html=True)

    st.text("Click to downloda a sample file:")
    st.markdown(example_link, unsafe_allow_html=True)

    uploaded_file = st.file_uploader("Choose a file", type=["csv", "xlsx", "xls"])
    if uploaded_file is not None:
        st.text("File uploaded successfully")

    # @st.cache
    def load_data():
        df = pd.read_excel(uploaded_file)
        # df.columns = map(str.lower, df.columns)
        df.columns = df.columns.str.replace(" ", "_")
        df.columns = df.columns.str.replace("-", "_")
        df = df.replace(0, np.nan)
        df = df.fillna(99990)
        return df

    if st.sidebar.checkbox("Show raw data"):
        st.subheader("Raw data")
        data = load_data()
        st.write(data)

    dict_data = []

    # if st.button("Create constraints"):
    st.subheader("Constraints")
    if uploaded_file is not None:
        data = load_data()
        dict_data = list(data.columns[3:])
    # st.write(supplier_list)

    const_list = {}

    if st.sidebar.checkbox("Constraint 1"):
        supp_list1 = st.multiselect("Constraint 1", dict_data)
        col1, col2 = st.beta_columns((1, 6))
        operator = col1.selectbox("Operator", [">=", "<="])
        share_val = col2.slider("Share", 0, 100, 0)
        const_list["con1"] = [supp_list1, operator, share_val]

    if st.sidebar.checkbox("Constraint 2"):
        supp_list2 = st.multiselect("Constraint 2", dict_data)
        col1, col2 = st.beta_columns((1, 6))
        operator = col1.selectbox("Operator2", [">=", "<="])
        share_val = col2.slider("Share2", 0, 100, 0)
        const_list["con2"] = [supp_list2, operator, share_val]

    if st.sidebar.checkbox("Constraint 3"):
        supp_list3 = st.multiselect("Constraint 3", dict_data)
        col1, col2 = st.beta_columns((1, 6))
        operator = col1.selectbox("Operator3", [">=", "<="])
        share_val = col2.slider("Share3", 0, 100, 0)
        const_list["con3"] = [supp_list3, operator, share_val]

    # st.write(const_list)

    calculation_type = st.sidebar.radio(
        "Chose the type of optimization", ("Per Item", "Per Group")
    )

    if st.button("Calculate share"):
        try:

            result = calculate_item_results(convert_df_to_dict(load_data()), const_list)

            if calculation_type == "Per Group":
                result = calculate_group_results((load_data()), const_list)

            share_df, share_percent_df, cost_df = split_results(result)

            share_name = []
            share_value = []
            t_share_df = share_df.transpose()
            for col in t_share_df.columns[2:]:
                share_sum = t_share_df[col].sum()
                if share_sum > 0:
                    share_name.append(col.replace("_", " "))
                    share_value.append(share_sum)

            cost_name = []
            cost_value = []
            t_cost_df = cost_df.transpose()
            for col in t_cost_df.columns[2:]:
                cost_sum = t_cost_df[col].sum()
                if cost_sum > 0:
                    cost_name.append(col.replace("_", " "))
                    cost_value.append(cost_sum)

            share_fig = go.Figure()
            share_fig.add_trace(
                go.Pie(
                    values=share_value, labels=share_name, title="Final Share (Units)"
                )
            )
            share_fig.update_traces(textinfo="percent+label+value")

            cost_fig = go.Figure()
            cost_fig.add_trace(
                go.Pie(values=cost_value, labels=cost_name, title="Final Share (USD)")
            )
            cost_fig.update_traces(textinfo="percent+label+value")

            bar_fig = go.Figure()
            clean_share_percent_df = share_percent_df.replace(0, np.nan)
            for row in clean_share_percent_df.iterrows():
                bar_fig.add_trace(
                    go.Bar(
                        name=row[0].replace("_", " "),
                        x=list(row[1].keys()),
                        y=row[1].values,
                    )
                )
            bar_fig.update_layout(barmode="stack")
            bar_fig.update_layout(hovermode="x")

            cost_table = pd.DataFrame(
                list(zip(cost_name, cost_value, share_value)),
                columns=["Supplier", "Cost", "Unit Share"],
            )
            cost_table["Cost Percentage"] = round(
                (cost_table["Cost"] / cost_table["Cost"].sum()) * 100
            )
            cost_table["Share Percentage"] = round(
                (cost_table["Unit Share"] / cost_table["Unit Share"].sum()) * 100
            )
            cost_table = cost_table.sort_values(by=["Cost Percentage"], ascending=False)
            cost_table.loc["Total"] = round(cost_table.sum(numeric_only=True))
            cost_table["Supplier"].loc["Total"] = " "
            cost_table["Cost"] = cost_table.apply(lambda x: round(x["Cost"]), axis=1)
            cost_table["Cost"] = cost_table.apply(
                lambda x: "{:,}".format(x["Cost"]), axis=1
            )
            cost_table["Unit Share"] = cost_table.apply(
                lambda x: round(x["Unit Share"]), axis=1
            )
            cost_table["Unit Share"] = cost_table.apply(
                lambda x: "{:,}".format(x["Unit Share"]), axis=1
            )
            # cost_table = cost_table.round(1)

            t_cost_df.insert(2, "item_total_cost", t_cost_df.iloc[:, 2:].sum(axis=1))
            for col in t_cost_df.columns:
                try:
                    t_cost_df[col] = t_cost_df.apply(lambda x: round(x[col]), axis=1)
                    t_cost_df[col] = t_cost_df.apply(
                        lambda x: "{:,}".format(x[col]), axis=1
                    )
                except Exception as e:
                    print(e)

            st.write(share_fig)
            st.write(cost_fig)
            st.write(cost_table)
            # st.markdown(get_table_download_link(cost_table), unsafe_allow_html=True)
            st.write(bar_fig)

            # st.write("Share Table")

            st.write("Share DataFrame (Units)")
            st.write(t_share_df)
            st.write("Share DataFrame (Percentage)")
            st.write(share_percent_df.transpose())
            st.write("Cost DataFrame")
            st.write(t_cost_df)

            t_share_df_e = t_share_df.reindex(
                columns=(
                    ["item", "item_consumption"]
                    + list(
                        [
                            a
                            for a in t_share_df.columns
                            if a not in ["item", "item_consumption"]
                        ]
                    )
                )
            ).loc[:, (t_share_df != 0).any(axis=0)]
            t_cost_df_e = t_cost_df.reindex(
                columns=(
                    ["item", "item_consumption"]
                    + list(
                        [
                            a
                            for a in t_cost_df.columns
                            if a not in ["item", "item_consumption"]
                        ]
                    )
                )
            ).loc[:, (t_cost_df != 0).any(axis=0)]

            df_export_list = [
                cost_table,
                t_share_df_e,
                t_cost_df_e,
                load_data(),
                pd.DataFrame().from_dict(const_list).transpose(),
            ]
            df_name_export_list = [
                "Supplier Share",
                "Supplier Share Units",
                "Item Costs",
                "Prices",
                "Constraints",
            ]

            st.markdown(
                get_table_download_link(
                    df_export_list,
                    df_name_export_list,
                    (str(file_name) + project_date.strftime("%d/%m/%Y-%X")),
                ),
                unsafe_allow_html=True,
            )

        except Exception as e:

            st.write("Select a dataset file first")
            st.write(e)


def compare_scenario():

    st.title("Scenario Comparison Test_v1")

    last_year_file = st.file_uploader("Last year result", type=["csv", "xlsx", "xls"])
    lowest_possible_file = st.file_uploader(
        "Lowest possible result", type=["csv", "xlsx", "xls"]
    )
    scenarios_files = st.file_uploader(
        "Scenarios results", type=["csv", "xlsx", "xls"], accept_multiple_files=True
    )

    def merge_df(base, lowest, sc_list):
        df_merged = pd.DataFrame()
        df_merged["item"] = base["item"]
        df_merged["base_cost"] = base["previous_budget"] * base["item_consumption"]

        lowest = lowest.rename(columns={"item_total_cost": "lowest_cost"})
        df_merged = df_merged.merge(lowest[["item", "lowest_cost"]], on="item")

        count = 1
        sc_col_names = []
        for sc in sc_list:
            sc_name = f"scenario_{count}"
            sc_col_names.append(sc_name)
            sc = sc.rename(columns={"item_total_cost": sc_name})
            df_merged = df_merged.merge(sc[["item", sc_name]], on="item")
            count += 1

        df_merged_perc = pd.DataFrame()
        df_merged_perc["item"] = base["item"]
        df_merged_perc["perc_base"] = np.zeros(len(df_merged))
        df_merged_perc["perc_lowest"] = (
            df_merged["lowest_cost"] / df_merged["base_cost"] - 1
        ) * 100
        for col in sc_col_names:
            df_merged_perc[f"perc_{col}"] = (
                df_merged[col] / df_merged["base_cost"] - 1
            ) * 100

        df_merged_perc["item"] = df_merged_perc["item"].astype("str")
        return df_merged, df_merged_perc

    if st.button("Compare"):
        try:
            sc_list = []
            for file in scenarios_files:
                sc_list.append(pd.read_excel(file, sheet_name="Item Costs"))

            df_merged, df_merged_perc = merge_df(
                pd.read_excel(last_year_file),
                pd.read_excel(lowest_possible_file, sheet_name="Item Costs"),
                sc_list,
            )
            st.write(df_merged)
            st.write(df_merged_perc)
            bar_fig = go.Figure()
            bar_fig.add_trace(
                go.Scatter(
                    name="Base", x=df_merged_perc["item"], y=df_merged_perc["perc_base"]
                )
            )
            bar_fig.add_trace(
                go.Scatter(
                    name="Lowest",
                    x=df_merged_perc["item"],
                    y=df_merged_perc["perc_lowest"],
                )
            )
            for col in df_merged_perc.iloc[:, -len(scenarios_files) :]:
                bar_fig.add_trace(
                    go.Bar(name=col, x=df_merged_perc["item"], y=df_merged_perc[col])
                )

            bar_fig2 = go.Figure()
            bar_fig2.add_trace(
                go.Bar(
                    name="Last year", x=["Last Year"], y=[df_merged["base_cost"].sum()]
                )
            )
            bar_fig2.add_trace(
                go.Bar(name="Lowest", x=["Lowest"], y=[df_merged["lowest_cost"].sum()])
            )
            for col in df_merged.iloc[:, -len(scenarios_files) :]:
                bar_fig2.add_trace(go.Bar(name=col, x=[col], y=[df_merged[col].sum()]))

            st.write(bar_fig)
            st.write(bar_fig2)
            df_merged.to_excel("df_merged.xlsx")

        except Exception as e:
            print("Try to reload the input files or check if their format is correct")
            print(e)

    # return st.write("not implemented yet")


## hide menu button
# hide_streamlit_style = """
# <style>
# #MainMenu {visibility: hidden;}
# footer {visibility: hidden;}
# </style>

# """
# st.markdown(hide_streamlit_style, unsafe_allow_html=True)

if __name__ == "__main__":
    main()