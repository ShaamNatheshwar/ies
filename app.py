# from flask import Flask, render_template, request
# import pandas as pd
# from prophet import Prophet
# import boto3
# import matplotlib.pyplot as plt

# app = Flask(__name__)

# @app.route('/', methods=['GET', 'POST'])
# def index():
#     if request.method == 'POST':
#         aws_access_key = request.form['aws_access_key']
#         aws_secret_key = request.form['aws_secret_key']
#         aws_region = request.form['aws_region']
#         dimension_value = request.form['dimension_value']
#         metric_name = request.form['metric_name']
#         threshold_value = float(request.form['threshold_value'])

#         cloudwatch = boto3.client('cloudwatch',
#                                   aws_access_key_id=aws_access_key,
#                                   aws_secret_access_key=aws_secret_key,
#                                   region_name=aws_region)

#         response = cloudwatch.get_metric_data(
#             MetricDataQueries=[
#                 {
#                     'Id': 'm1',
#                     'MetricStat': {
#                         'Metric': {
#                             'Namespace': 'AWS/RDS',
#                             'MetricName': metric_name,
#                             'Dimensions': [
#                                 {
#                                     'Name': 'DBInstanceIdentifier',
#                                     'Value': dimension_value
#                                 },
#                             ],
#                         },
#                         'Period': 300,
#                         'Stat': 'Average',
#                     },
#                     'ReturnData': True,
#                 },
#             ],
#             StartTime=pd.to_datetime('now') - pd.Timedelta(minutes=300),
#             EndTime=pd.to_datetime('now')
#         )

#         timestamps = response['MetricDataResults'][0]['Timestamps']
#         cpu_values = response['MetricDataResults'][0]['Values']

#         threshold_series = pd.Series([threshold_value] * len(timestamps))
#         data = pd.DataFrame({'ds': timestamps, 'y': cpu_values, 'threshold': threshold_series})
#         # data['ds'] = data['ds'].dt.tz_localize(None)
#         data['ds'] = pd.to_datetime(data['ds'])
#         actual_and_predicted_values = pd.merge(data[['ds', 'y', 'threshold']], forecast[['ds', 'yhat']], on='ds', how='inner')

#         model = Prophet(
#             yearly_seasonality=True,
#             weekly_seasonality=True,
#             daily_seasonality=True,
#             holidays=None,
#             changepoint_prior_scale=0.25,
#             seasonality_prior_scale=10.0,
#         )

#         model.fit(data)

#         future = model.make_future_dataframe(periods=120, freq='10T')
#         forecast = model.predict(future)

#         forecast['yhat'] = forecast['yhat'].clip(lower=data['y'].min(), upper=data['y'].max())

#         actual_and_predicted_values = pd.merge(data[['ds', 'y', 'threshold']], forecast[['ds', 'yhat']], on='ds',
#                                                how='inner')
#         actual_and_predicted_values.columns = ['Timestamp', 'Actual', 'Threshold', 'Predicted']

#         breach_predictions = forecast[forecast['yhat'] > threshold_value]

#         plot_path = 'static/plot.png'
#         plt.figure(figsize=(10, 6))
#         plt.plot(data['ds'], data['y'], label='Actual', marker='o')
#         plt.plot(forecast['ds'], forecast['yhat'], label='Predicted', linestyle='--', marker='o')
#         plt.plot(data['ds'], data['threshold'], label='Threshold', linestyle='--', color='red')
#         plt.title('Actual vs Predicted CPU Utilization with Threshold')
#         plt.xlabel('Timestamp')
#         plt.ylabel('CPU Utilization')
#         plt.legend()
#         plt.savefig(plot_path)
#         plt.close()

#         if not breach_predictions.empty:
#             next_breach_time = breach_predictions['ds'].iloc[0]
#             breach_message = f"Possible breach might occur around: {next_breach_time}"
#         else:
#             breach_message = "No Threshold Breaches Predicted."

#         return render_template('result.html',
#                                actual_and_predicted_values=actual_and_predicted_values.to_html(),
#                                breach_message=breach_message,
#                                plot_path=plot_path)

#     return render_template('index.html')

# if __name__ == '__main__':  app.run(debug=True)








from flask import Flask, render_template, request
import pandas as pd
from prophet import Prophet
import boto3
import matplotlib.pyplot as plt

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    forecast = None  # Initialize forecast variable

    if request.method == 'POST':
        aws_access_key = request.form['aws_access_key']
        aws_secret_key = request.form['aws_secret_key']
        aws_region = request.form['aws_region']
        dimension_value = request.form['dimension_value']
        metric_name = request.form['metric_name']
        threshold_value = float(request.form['threshold_value'])

        cloudwatch = boto3.client('cloudwatch',
                                  aws_access_key_id=aws_access_key,
                                  aws_secret_access_key=aws_secret_key,
                                  region_name=aws_region)

        response = cloudwatch.get_metric_data(
            MetricDataQueries=[
                {
                    'Id': 'm1',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'AWS/RDS',
                            'MetricName': metric_name,
                            'Dimensions': [
                                {
                                    'Name': 'DBInstanceIdentifier',
                                    'Value': dimension_value
                                },
                            ],
                        },
                        'Period': 300,
                        'Stat': 'Average',
                    },
                    'ReturnData': True,
                },
            ],
            StartTime=pd.to_datetime('now') - pd.Timedelta(minutes=600),  # Adjust as needed
            EndTime=pd.to_datetime('now')
        )

        timestamps = response['MetricDataResults'][0]['Timestamps']
        cpu_values = response['MetricDataResults'][0]['Values']

        # Create a DataFrame
        data = pd.DataFrame({'ds': timestamps, 'y': cpu_values})
        
        # Drop rows with missing values
        data = data.dropna(subset=['ds', 'y'])

        # Sort by timestamps
        data = data.sort_values(by='ds').drop_duplicates('ds')

        data['ds'] = pd.to_datetime(data['ds']).dt.tz_localize(None)
        threshold_value = float(request.form['threshold_value'])

        threshold_series = pd.Series([threshold_value] * len(data))
        data['threshold'] = threshold_series

        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=True,
            holidays=None,
            changepoint_prior_scale=0.25,
            seasonality_prior_scale=10.0,
        )

        model.fit(data)

        future = model.make_future_dataframe(periods=120, freq='10T')
        forecast = model.predict(future)

        forecast['yhat'] = forecast['yhat'].clip(lower=data['y'].min(), upper=data['y'].max())

        actual_and_predicted_values = pd.merge(data[['ds', 'y', 'threshold']], forecast[['ds', 'yhat']], on='ds', how='inner')
        actual_and_predicted_values.columns = ['Timestamp', 'Actual', 'Threshold', 'Predicted']

        breach_predictions = forecast[forecast['yhat'] > threshold_value]

        plot_path = 'static/plot.png'
        plt.figure(figsize=(10, 6))
        plt.plot(data['ds'], data['y'], label='Actual', marker='o')
        plt.plot(forecast['ds'], forecast['yhat'], label='Predicted', linestyle='--', marker='o')
        plt.plot(data['ds'], data['threshold'], label='Threshold', linestyle='--', color='red')
        plt.title('Actual vs Predicted CPU Utilization with Threshold')
        plt.xlabel('Timestamp')
        plt.ylabel('CPU Utilization')
        plt.legend()
        plt.savefig(plot_path)
        plt.close()

        if not breach_predictions.empty:
            next_breach_time = breach_predictions['ds'].iloc[0]
            breach_message = f"Possible breach might occur around: {next_breach_time}"
        else:
            breach_message = "No Threshold Breaches Predicted."

        return render_template('result.html',
                               actual_and_predicted_values=actual_and_predicted_values.to_html(),
                               breach_message=breach_message,
                               plot_path=plot_path)

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)