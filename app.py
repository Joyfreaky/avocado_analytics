import pandas as pd
from dash import Dash, dcc, html, Input, Output, dash_table
import plotly.express as px
from prophet import Prophet
import datetime

# Read the data and preprocess it
data = (
    pd.read_csv("avocado.csv")
    .assign(Date=lambda data: pd.to_datetime(data["Date"], format="%Y-%m-%d"))
    .sort_values(by="Date")
)
regions = data["region"].sort_values().unique()
avocado_types = data["type"].sort_values().unique()

# Modify the data to include the week number and month and replace the unnamed column with the week number
data["Week"] = data["Date"].dt.week
data["Month"] = data["Date"].dt.month
data["Year"] = data["Date"].dt.year
# Drop the unnamed column
data = data.drop(columns=["Unnamed: 0"])
# Create Index column
data["Index"] = range(1, len(data) + 1)

# Reorder the columns
data = data[["Index", "Date", "Year", "Month", "Week", "AveragePrice", "Total Volume", "4046", "4225", "4770", "Total Bags", "Small Bags", "Large Bags", "XLarge Bags", "type", "year", "region"]]


# Perform time series forecasting
prophet_data = data[["Date", "AveragePrice"]].rename(columns={"Date": "ds", "AveragePrice": "y"})
confidence_interval = 0.95
model = Prophet(interval_width=confidence_interval)
model.fit(prophet_data)
weeks_to_forecast = 12 # Forecasting for 4 weeks
last_date = data["Date"].max()
forecast_start_date = last_date + datetime.timedelta(days=7)
future_dates = pd.date_range(start=forecast_start_date, periods=weeks_to_forecast, freq="W")
future = model.make_future_dataframe(periods=weeks_to_forecast, freq="W", include_history=False)
forecast = model.predict(future)

# Set the External Stylesheets
external_stylesheets = [
    {
        "href": (
            "https://fonts.googleapis.com/css2?"
            "family=Lato:wght@400;700&display=swap"
        ),
        "rel": "stylesheet",
    },
]

# Create the Dash application instance
app = Dash(__name__, external_stylesheets=external_stylesheets)

# Set the application title
app.title = "Avocado Analytics: Understand Your Avocados!"


# Create the application layout

app.layout = html.Div(
    children=[
        html.Div(
            children=[
                html.P(children="🥑", className="header-emoji"),
                html.H1(children="Avocado Analytics", className="header-title"),
                html.P(
                    children=(
                        "Analyse the behaviour of avocado prices and the number"
                        " of avocados sold in the US between 2015 and 2018"
                    ),
                    className="header-description",
                ),
            ],
            className="header",
        ),
        html.Div(
            children=[
                html.Div(
                    children=[
                        html.Div(children="Region", className="menu-title"),
                        dcc.Dropdown(
                            id="region-filter",
                            options=[
                                {"label": region, "value": region}
                                for region in regions
                            ],
                            value="Albany",
                            clearable=False,
                            className="dropdown",
                        ),
                    ]
                ),
                html.Div(
                    children=[
                        html.Div(children="Type", className="menu-title"),
                        dcc.Dropdown(
                            id="type-filter",
                            options=[
                                {
                                    "label": avocado_type.title(),
                                    "value": avocado_type,
                                }
                                for avocado_type in avocado_types
                            ],
                            value="organic",
                            clearable=False,
                            searchable=False,
                            className="dropdown",
                        ),
                    ],
                ),
                html.Div(
                    children=[
                        html.Div(
                            children="Date Range",
                            className="menu-title"
                        ),
                        dcc.DatePickerRange(
                            id="date-range",
                            min_date_allowed=data["Date"].min().date(),
                            max_date_allowed=data["Date"].max().date(),
                            start_date=data["Date"].min().date(),
                            end_date=data["Date"].max().date(),
                        ),
                    ]
                ),
            ],
            className="menu",
        ),
        html.Div(
            children=[
                html.Div(
                    children=[
                        dcc.Graph(
                            id="price-chart",
                            figure=px.line(
                                data,
                                x="Date",
                                y="AveragePrice",
                                title="Average Price of Avocados"
                            ),
                        ),
                    ],
                    className="graph-container",
                ),
                html.Div(
                    children=[
                        dcc.Graph(
                            id="volume-chart",
                            figure=px.line(
                                data,
                                x="Date",
                                y="Total Volume",
                                title="Avocados Sold"
                            ),
                        ),
                    ],
                    className="graph-container",
                ),
                html.Div(
                    children=[
                        dcc.Graph(
                            id="forecast-chart",
                            figure=px.line(
                                forecast,
                                x="ds",
                                y=["yhat", "yhat_lower", "yhat_upper"],
                                title="Forecasted Average Price of Avocados"
                            ),
                        ),
                    ],
                    className="graph-container",
                ),
            ],
            className="wrapper",
        ),
        html.Div(
            id="forecast-table",
            children=[
                html.H2("Projected or Future Price Data"),
                html.Table(
                    className="forecast-table",
                    children=[
                        html.Thead(
                            html.Tr(
                                children=[
                                    html.Th("Date"),
                                    html.Th("Projected Price"),
                                    html.Th("Lower Bound"),
                                    html.Th("Upper Bound"),
                                ]
                            )
                        ),
                        html.Tbody(
                            [
                                html.Tr(
                                    children=[
                                        html.Td(str(date)),
                                        html.Td(f"${price:.2f}"),
                                        html.Td(f"${lower_bound:.2f}"),
                                        html.Td(f"${upper_bound:.2f}"),
                                    ]
                                )
                                for date, price, lower_bound, upper_bound in zip(
                                    forecast["ds"].tail(weeks_to_forecast),
                                    forecast["yhat"].tail(weeks_to_forecast),
                                    forecast["yhat_lower"].tail(weeks_to_forecast),
                                    forecast["yhat_upper"].tail(weeks_to_forecast),
                                )
                            ]
                        ),
                    ],
                ),
            ],
            className="wrapper"
        ),
    ]
)



# Define the callback function to update the graphs and selected data based on the selected date range

@app.callback(
    [Output("price-chart", "figure"),
        Output("volume-chart", "figure"),
        Output("forecast-chart", "figure"),
        Output("forecast-table", "children")],
    [
        Input("region-filter", "value"),
        Input("type-filter", "value"),
        Input("date-range", "start_date"),
        Input("date-range", "end_date"),
    ],    
)
def update_data(region, avocado_type, start_date, end_date):
    filtered_data = data.query(
        "region == @region & type == @avocado_type"
        " and Date >= @start_date and Date <= @end_date"
    )

    
    
    price_chart_figure = {
        "data": [
            {
                "x": filtered_data["Date"],
                "y": filtered_data["AveragePrice"],
                "type": "lines",
                "hovertemplate": "$%{y:.2f}<extra></extra>",
            },
        ],
        "layout": {
            "title": {
                "text": "Average Price of Avocados",
                "x": 0.05,
                "xanchor": "left",
            },
            "xaxis": {"fixedrange": True},
            "yaxis": {"tickprefix": "$", "fixedrange": True},
            "colorway": ["#17B897"],
        },
    }
    price_chart_figure["data"][0]["line"] = {"color": "#E12D39"}
    price_chart_figure["data"][0]["hovertemplate"] = "$%{y:.2f}<extra></extra>"
    price_chart_figure["layout"]["yaxis"]["title"] = {"text": "Price"}
    price_chart_figure["layout"]["xaxis"]["title"] = {"text": "Date"}



    volume_chart_figure = {
        "data": [
            {
                "x": filtered_data["Date"],
                "y": filtered_data["Total Volume"],
                "type": "lines",
            },
        ],
        "layout": {
            "title": {"text": "Avocados Sold", "x": 0.05, "xanchor": "left"},
            "xaxis": {"fixedrange": True},
            "yaxis": {"fixedrange": True},
            "colorway": ["#E12D39"],
        },
    }
    volume_chart_figure["data"][0]["line"] = {"color": "#17B897"}
    volume_chart_figure["data"][0]["hovertemplate"] = "%{y:.2f}<extra></extra>"
    volume_chart_figure["layout"]["yaxis"]["title"] = {"text": "Avocados Sold"}
    volume_chart_figure["layout"]["xaxis"]["title"] = {"text": "Date"}



    forecast_chart_figure = {
        "data": [
            {
                "x": forecast["ds"],
                "y": forecast["yhat"],
                "type": "lines",
                "hovertemplate": "$%{y:.2f}<extra></extra>",
            },
            {
                "x": forecast["ds"],
                "y": forecast["yhat_upper"],
                "type": "lines",
                "hovertemplate": "$%{y:.2f}<extra></extra>",
                "line": {"color": "#E12D39", "dash": "dash"},
                "showlegend": False,
            },
            {
                "x": forecast["ds"],
                "y": forecast["yhat_lower"],
                "type": "lines",
                "hovertemplate": "$%{y:.2f}<extra></extra>",
                "line": {"color": "#E12D39", "dash": "dash"},
                "showlegend": False,
            },
        ],
        "layout": {
            "title": {
                "text": "Forecasted Average Price of Avocados",
                "x": 0.05,
                "xanchor": "left",
            },
            "xaxis": {"fixedrange": True},
            "yaxis": {"tickprefix": "$", "fixedrange": True},
            "colorway": ["#17B897"],
        },
    }
    forecast_chart_figure["layout"]["yaxis"]["title"] = {"text": "Price"}
    forecast_chart_figure["layout"]["xaxis"]["title"] = {"text": "Date"}
    forecast_chart_figure["layout"]["hovermode"] = "x unified"
    


    forecast_table_data = forecast.loc[
        :, ["ds", "yhat", "yhat_lower", "yhat_upper"]
    ].tail(weeks_to_forecast)

    forecast_table_data.rename(
        columns={"ds": "Date", "yhat": "Projected Price"}, inplace=True
    )

    forecast_table = dash_table.DataTable(
        data=forecast_table_data.to_dict("records"),
        columns=[{"id": c, "name": c} for c in forecast_table_data.columns],
        style_cell={"textAlign": "left"},
        style_header={
            "backgroundColor": "white",
            "fontWeight": "bold",
            "border": "1px solid black",
        },
        style_data={"border": "1px solid black"},
    )
    
    
    return price_chart_figure, volume_chart_figure, forecast_chart_figure, forecast_table



if __name__ == "__main__":
    app.run_server(debug=True)