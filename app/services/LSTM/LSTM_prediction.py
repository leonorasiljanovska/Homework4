from keras import Sequential
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler

from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.optimizers import Adam
import numpy as np
from sklearn.metrics import mean_squared_error

from app.models import CompanyData, Company
import pandas as pd


def preprocess_data_with_split(company_code):
    # Query the database for historical data of the given company
    company = Company.query.filter_by(company_code=company_code).first()
    if company:
        company_data = CompanyData.query.filter_by(company_id=company.id).order_by(CompanyData.date).all()
    # Convert data into a pandas DataFrame
    data = pd.DataFrame(
        [(entry.date, entry.last_transaction_price, entry.max_price, entry.min_price, entry.average_price,
          entry.price_change_percentage, entry.quantity, entry.turnover_best_bests, entry.total_turnover)
         for entry in company_data],
        columns=['date', 'last_transaction_price', 'max_price', 'min_price', 'average_price', 'price_change_percentage',
                 'quantity', 'turnover_best_bests', 'total_turnover'])

    # Convert 'date' column to datetime
    data['date'] = pd.to_datetime(data['date'])

    # Sort by date to ensure chronological order
    data = data.sort_values('date')

    # Handle missing values (fill with previous values or drop rows)
    data = data.fillna(method='ffill')

    # Define the target and features
    Y = data['last_transaction_price']
    X = data.drop(columns=['last_transaction_price', 'date'])  # Drop the target column and date column

    # Normalize the features
    scaler = MinMaxScaler(feature_range=(0, 1))
    X_scaled = scaler.fit_transform(X)

    # Split data into training and testing sets (70% for training, 30% for testing)
    X_train, X_test, Y_train, Y_test = train_test_split(X_scaled, Y, test_size=0.3,
                                                        shuffle=False)  # no shuffling for time-series data

    return X_train, X_test, Y_train, Y_test, scaler, data


def reshape_data_for_lstm(X_train, X_test):
    """Reshape data for LSTM input (samples, timesteps, features)"""
    # Using last 60 days for sequence
    sequence_length = 60

    # Reshape training data
    X_train_reshaped = []
    for i in range(sequence_length, len(X_train)):
        X_train_reshaped.append(X_train[i - sequence_length:i])
    X_train_reshaped = np.array(X_train_reshaped)

    # Reshape testing data
    X_test_reshaped = []
    for i in range(sequence_length, len(X_test)):
        X_test_reshaped.append(X_test[i - sequence_length:i])
    X_test_reshaped = np.array(X_test_reshaped)

    return X_train_reshaped, X_test_reshaped, sequence_length


def create_lstm_model(input_shape):
    """Create and compile the LSTM model"""
    model = Sequential([
        LSTM(units=50, return_sequences=True, input_shape=input_shape),
        Dropout(0.2),
        LSTM(units=50),
        Dropout(0.2),
        Dense(units=25),
        Dense(units=1)
    ])

    model.compile(optimizer=Adam(learning_rate=0.001), loss='mse')
    return model


def train_lstm_model(model, X_train_reshaped, Y_train, X_test_reshaped, Y_test):
    """Train the LSTM model"""
    # Adjust Y_train and Y_test to match reshaped X data
    sequence_length = X_train_reshaped.shape[1]
    Y_train_adj = Y_train[sequence_length:]
    Y_test_adj = Y_test[sequence_length:]

    history = model.fit(
        X_train_reshaped, Y_train_adj,
        epochs=50,
        batch_size=32,
        validation_data=(X_test_reshaped, Y_test_adj),
        verbose=1
    )
    return model, history


def make_predictions(model, X_test_reshaped, scaler, original_data):
    """Make predictions using the trained model"""
    predictions = model.predict(X_test_reshaped)

    # If you need to inverse transform the predictions
    # First create a dummy array with same shape as original data
    dummy = np.zeros((len(predictions), original_data.shape[1] - 2))  # -2 for date and target columns
    dummy_predictions = np.column_stack((predictions, dummy))

    # Inverse transform
    predictions_transformed = scaler.inverse_transform(dummy_predictions)[:, 0]

    return predictions_transformed


def generate_lstm_recommendation(predictions, actual_values, threshold=0.02):
    """Generate trading recommendation based on predicted price movement"""
    last_actual = actual_values.iloc[-1]
    next_predicted = predictions[-1]

    percent_change = (next_predicted - last_actual) / last_actual

    if percent_change > threshold:
        return "Buy"
    elif percent_change < -threshold:
        return "Sell"
    else:
        return "Hold"


def perform_lstm_prediction(company_code):
    """Main function to perform LSTM prediction and generate recommendation"""
    try:
        # Get preprocessed data
        X_train, X_test, Y_train, Y_test, scaler, original_data = preprocess_data_with_split(company_code)

        # Reshape data for LSTM
        X_train_reshaped, X_test_reshaped, sequence_length = reshape_data_for_lstm(X_train, X_test)

        # Create and train model
        model = create_lstm_model((sequence_length, X_train.shape[1]))
        model, history = train_lstm_model(model, X_train_reshaped, Y_train, X_test_reshaped, Y_test)

        # Make predictions
        predictions = make_predictions(model, X_test_reshaped, scaler, original_data)

        # Generate recommendation
        recommendation = generate_lstm_recommendation(predictions, Y_test)

        # Calculate error metrics
        mse = mean_squared_error(Y_test[sequence_length:], predictions)
        rmse = np.sqrt(mse)

        return recommendation, predictions, rmse

    except Exception as e:
        print(f"Error in LSTM prediction: {e}")
        return "Hold", None, None
