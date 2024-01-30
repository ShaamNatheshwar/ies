import sys
import boto3
import pandas as pd
from prophet import Prophet

def fetch_cloudwatch_data(aws_region, dimension_value, metric_name):
    # Placeholder AWS access key and secret for testing
    aws_access_key = 'AKIA5XLCDJWDBSTFUWUY'
    aws_secret_key = 'mztynV/GEmytgoixWqK+ZeUUx+W3LPI2G2jI0b67'

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
        StartTime=pd.to_datetime('now') - pd.Timedelta(hours=6),  # Adjust the time range
        EndTime=pd.to_datetime('now')
    )

    timestamps = response['MetricDataResults'][0]['Timestamps']
    cpu_values = response['MetricDataResults'][0]['Values']

    data = pd.DataFrame({'ds': timestamps, 'y': cpu_values})

    data = data.sort_values(by='ds').drop_duplicates('ds')

    data['ds'] = pd.to_datetime(data['ds']).dt.tz_localize(None)

    # Handle NaN values by dropping them
    data = data.dropna()

    return data

def main():
    # Check if enough command-line arguments are provided
    if len(sys.argv) != 4:
        print("Usage: python script.py <aws_region> <dimension_value> <metric_name>")
        sys.exit(1)

    # Take command-line arguments
    aws_region = sys.argv[1]
    dimension_value = sys.argv[2]
    metric_name = sys.argv[3]

    # Fetch CloudWatch data
    data = fetch_cloudwatch_data(aws_region, dimension_value, metric_name)

    # Check the length of the DataFrame
    if len(data) < 2:
        print("Insufficient non-NaN data for modeling. Check your time range or data availability.")
        sys.exit(1)

    # Define a threshold value
    threshold_value = 3.25

    # Add the threshold value to the data frame
    data['threshold'] = threshold_value

    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=True,
        holidays=None,
        changepoint_prior_scale=0.25,
        seasonality_prior_scale=10.0,
    )

    # Fit the model
    model.fit(data)

    future = model.make_future_dataframe(periods=120, freq='10T')  # Predict the next 2 hours (120 minutes)

    # Make predictions
    forecast = model.predict(future)

    # Identify threshold breaches in the predicted values
    breach_predictions = forecast[forecast['yhat'] > threshold_value]
    if not breach_predictions.empty:
        # Identify and print the time when the breach might occur
        next_breach_time = breach_predictions['ds'].iloc[0]
        print(f"\nPossible breach might occur around: {next_breach_time}")
    else:
        print("\nNo Threshold Breaches Predicted.")

if __name__ == '__main__':
    main()