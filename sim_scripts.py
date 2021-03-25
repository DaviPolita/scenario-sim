import pandas as pd
from pulp import *
import streamlit as st
import base64
from io import BytesIO

# df01 = pd.read_excel("./Data/teste.xlsx")


@st.cache
def convert_df_to_dict(df):
    items_dict = {}

    for row in df.iterrows():
        item = {}

        item_num = row[1]["Item"]
        item["item_num"] = item_num
        item["description"] = row[1]["Description"]
        item["consumption"] = round(row[1]["Consumption"])

        item_supplier = {}
        for i, j in zip(row[1][3:].keys(), row[1][3:].values):
            if j > 0:
                j = round(float(j), 2)
                item_supplier[i] = j

        item["suppliers_price"] = item_supplier

        items_dict[item_num] = item

    return items_dict


# items_dict = convert_df_to_dict(df)

# print(convert_df_to_dict(df))


@st.cache
def calculate_item_results(dict_of_items, constraints):
    results = {}

    for x in dict_of_items:
        prob = LpProblem(f"{x}_case", LpMinimize)

        suppliers = list([i for i in dict_of_items[x]["suppliers_price"].keys()])

        costs = dict(
            zip(suppliers, [i for i in dict_of_items[x]["suppliers_price"].values()])
        )

        supp_item_results = LpVariable.dicts(
            "Share", suppliers, lowBound=0, cat="Integer"
        )

        prob += lpSum([costs[i] * supp_item_results[i] for i in suppliers])

        prob += (
            lpSum([supp_item_results[i] for i in suppliers])
            <= dict_of_items[x]["consumption"]
        )
        prob += (
            lpSum([supp_item_results[i] for i in suppliers])
            >= dict_of_items[x]["consumption"]
        )

        for con in constraints:
            if constraints[con][1] == "<=":
                supplier_con = constraints[con][0]
                supplier_share = (dict_of_items[x]["consumption"] / 100) * constraints[
                    con
                ][2]
                prob += (
                    lpSum(
                        [
                            supp_item_results[i]
                            for i in supplier_con
                            if i in supp_item_results
                        ]
                    )
                    <= supplier_share
                )
            if constraints[con][1] == ">=":
                supplier_con = constraints[con][0]
                supplier_share = (dict_of_items[x]["consumption"] / 100) * constraints[
                    con
                ][2]
                prob += (
                    lpSum(
                        [
                            supp_item_results[i]
                            for i in supplier_con
                            if i in supp_item_results
                        ]
                    )
                    >= supplier_share
                )

        prob.solve()

        item_results = {}
        item_results["item_num"] = dict_of_items[x]["item_num"]
        item_results["description"] = dict_of_items[x]["description"]
        item_results["item_consumption"] = dict_of_items[x]["consumption"]
        item_results["supplier_prices"] = dict_of_items[x]["suppliers_price"]

        share = {}
        for v in prob.variables():
            if v.varValue is not None and v.varValue > 0:

                # perc = v.varValue / dict_of_items[x]["consumption"] * 100

                sup_name = v.name[6:]  # .replace("_", " ")

                #                 share[v.name] = [str(v.varValue) + " Units"+ " -> ", str(round(perc)) + " %"]
                share[sup_name] = v.varValue
        item_results["share"] = share

        obj = value(prob.objective)
        item_results["total_value"] = obj

        # data = prob.to_dict()
        # item_results["full_prob"] = data

        results["item " + f"{x}"] = item_results

    #     # prob.to_json("prob.json")

    return results


@st.cache
def calculate_group_results(df_items, constraints):
    # print(constraints)

    df_items[["Item"]] = df_items[["Item"]].astype(str)
    items = list(df_items["Item"])
    # items_dict = dict(zip(items, df_items["Item"]))

    consumption = dict(zip(items, round(df_items["Consumption"])))
    total_consumption = sum(df_items["Consumption"])

    supplier_list = list(df_items.columns[3:])

    costs = df_items.iloc[:, 3:].values
    costs = makeDict([items, supplier_list], costs, 0)

    for con in constraints:
        max_items = round(
            ((total_consumption / 100) * constraints[con][2])
            / (len(constraints[con][0]))
        )
        constraints[con].append(max_items)

    supplier_constraints = {}
    if len(constraints) == 0:
        for sup in supplier_list:
            supplier_constraints[sup] = 0

    if len(constraints) > 0:
        for con in constraints:
            for sup in supplier_list:

                if sup in constraints[con][0]:
                    supplier_constraints[sup] = constraints[con][3]
                else:
                    if sup not in supplier_constraints:
                        supplier_constraints[sup] = 0

    prob = LpProblem("supplier_cost", LpMinimize)

    prices = [(i, s) for i in items for s in supplier_list]

    share_vars = LpVariable.dicts("share", (items, supplier_list), 0, None, LpInteger)

    prob += (
        lpSum([share_vars[w][b] * costs[w][b] for (w, b) in prices]),
        "Optimal_share_division",
    )

    for i in items:
        prob += (
            lpSum([share_vars[i][s] for s in supplier_list]) == consumption[i],
            "Sum_of_consumption_for_item_%s" % i,
        )

    for s in supplier_list:
        for con in constraints:
            if s in constraints[con][0] and constraints[con][1] == "<=":
                prob += (
                    lpSum([share_vars[i][s] for i in items]) <= supplier_constraints[s],
                    "Sum_of_itens_for_supplier_lower_%s" % s,
                )

        prob += (
            lpSum([share_vars[i][s] for i in items]) >= supplier_constraints[s],
            "Sum_of_itens_for_supplier_%s" % s,
        )

    prob.solve()

    results = {}
    for v in prob.variables():
        results[v.name] = v.varValue

    df_r = pd.DataFrame.from_dict(results, orient="index")
    # df_r['name'] = df_r.index
    df_r = df_r.reset_index()

    df_r[["sh", "item", "sup"]] = df_r["index"].str.split("_", 2, expand=True)
    df_result = df_r[["item", "sup", 0]].rename(columns={0: "share"})
    df_piv = df_result.pivot(index="item", columns="sup", values="share")
    # df_piv

    costs_d = df_items.iloc[:, 3:]
    costs_d["Item"] = df_items["Item"]
    costs_d = costs_d.set_index("Item")
    costs_dict = costs_d.transpose().to_dict()

    share_dict = df_piv.transpose().to_dict()

    item_results = {}
    for item in items:
        result = {}
        result["item_num"] = item
        result["description"] = "desc"
        result["item_consumption"] = consumption[item]
        result["supplier_prices"] = costs_dict[item]
        result["share"] = share_dict[item]
        item_results[item] = result

    return item_results


# result = calculate_item_results(items_dict)

# pp = pprint.PrettyPrinter()
# pp.pprint(result)


@st.cache
def split_results(result):
    share_result = {}
    share_percent_result = {}
    cost_result = {}

    for item in result:
        share_dict = {}
        share_dict["item"] = result[item]["item_num"]
        # share_dict["item_description"] = result[item]["description"]
        share_dict["item_consumption"] = result[item]["item_consumption"]
        for sup in result[item]["share"]:
            share_dict[sup] = result[item]["share"][sup]

        cost_dict = {}
        cost_dict["item"] = result[item]["item_num"]
        # cost_dict["item_description"] = result[item]["description"]
        cost_dict["item_consumption"] = result[item]["item_consumption"]

        for sup_price in result[item]["share"]:
            cost_dict[sup_price] = (
                result[item]["supplier_prices"][sup_price]
                * result[item]["share"][sup_price]
            )

        share_percent_dict = {}
        # share_percent_dict["item_description"] = result[item]["description"]
        for sup_q in result[item]["share"]:
            share_percent_dict[sup_q] = round(
                (result[item]["share"][sup_q] / result[item]["item_consumption"]) * 100
            )

        share_result[item] = share_dict
        share_percent_result[item] = share_percent_dict
        cost_result[item] = cost_dict

    # clean_result
    share_df = pd.DataFrame(share_result).fillna(0)
    share_percent_df = pd.DataFrame(share_percent_result).fillna(0)
    cost_df = pd.DataFrame(cost_result).fillna(0)
    return share_df, share_percent_df, cost_df


def to_excel(df_export_list, df_name_export_list):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine="xlsxwriter")
    for i, j in zip(df_export_list, df_name_export_list):
        i.to_excel(writer, sheet_name=j, index=False)
    writer.save()
    processed_data = output.getvalue()
    return processed_data


def get_table_download_link(df_export_list, df_name_export_list, file_name):
    """Generates a link allowing the data in a given panda dataframe to be downloaded
    in:  dataframe
    out: href string
    """
    val = to_excel(df_export_list, df_name_export_list)
    b64 = base64.b64encode(val)  # val looks like b'...'
    return f'<a href="data:application/octet-stream;base64,{b64.decode()}" download="{file_name}.xlsx">Download results file</a>'  # decode b'abc' => abc
