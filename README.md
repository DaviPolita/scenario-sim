# Procurement Optimization Platform

This project demonstrates the Cost and Share Optimization tool, developed using Pulp, a linear programing modeler written in Python.
The Web App user interface was developed using Streamlit and custom Javascript, it allows the user to easily run simulations for different scenarios, the results then can be visualized and exported.

<- **Please select _Scenario Creation_ in the sidebar to start.**

#### Instructions

-   Download the template in the folder link
-   Fill the template with the data without changing the structure of the template
-   Load the file into the app
-   Select a name for the simulation, the default value is the local datetime
-   Run the simulation without constraints by pressing the Calculate button
-   Or create a constraint by selecting a checkbox on the sidebar

##### To configure a constraint:

-   Select the desired supplier(s)
-   Select the type of constraint (<= or >=)
-   Select the allocated share for that supplier(s) (%)
-   Run the simulation by pressing the Calculate button

### Results:

The results can be visualized with the interactive charts available in the app, to view the charts in full screen click the button on the top right corner of the chart, use the toolbar on the top of the char to download it as an image or to explore the data

At the bottom of the charts are displayed the result tables, with the supplier share per item, supplier cost per item and overall cost and share per supplier.

All the calculated data and model constraints can be exported to Excel by clicking the "Export results" link at the bottom of the app.
