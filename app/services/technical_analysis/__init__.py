# from flask import Flask
#
# from app.services.technical_analysis.calculations import calculate_for_date_range
#
#
# def create_app():
#     app = Flask(__name__)
#
#     @app.route('/calculate_signal', methods=['POST'])
#     def calculate_signal():
#         from flask import request, jsonify
#
#         # Get the data from the request
#         data = request.get_json()
#         start_date = data.get('start_date')
#         end_date = data.get('end_date')
#
#         # Call your calculate_for_date_range function
#         signal = calculate_for_date_range((start_date, end_date))
#
#         if signal is None:
#             return jsonify({'message': 'No data found or calculation error'}), 400
#
#         return jsonify({'signal': signal}), 200
#
#     return app1
