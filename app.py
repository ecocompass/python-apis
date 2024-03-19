from flask import Flask, jsonify, request
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt, get_jwt_identity
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import timedelta
import datetime
import logging
logging.basicConfig(level=logging.DEBUG)
import sys
from celery import Celery
import time
import datetime
import psycopg2
import re
from redis import Redis

def databaseconn():
    try:
        conn = psycopg2.connect(
            host="140.238.228.234",
            port=8086,
            database="postgres",
            user="pastav",
            password="ase123pastav"
        )
        return conn
    except Exception as e:
        print(f"An error occurred: {e}")
        
app = Flask(__name__)
ACCESS_EXPIRES = timedelta(days=3)
app.config['CELERY_BROKER_URL'] = 'redis://:pastavase123@34.242.139.134:6379/1'
app.config['CELERY_RESULT_BACKEND'] = 'redis://:pastavase123@34.242.139.134:6379/1'
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

@celery.task
def background_task(param1, param2):
    # Perform some background task here
    # For example, save data to Redis
    time.sleep(5)
    x = param1 + param2
    print(param1, param2)
    return 'Task completed'

@app.route('/trigger_task')
@jwt_required()
def trigger_task():
    # Trigger the background task asynchronously
    result = background_task.delay(1, 3)
    return f"Task ID: {result.id}"

app.config['JWT_SECRET_KEY'] = 'chakdephatte'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = ACCESS_EXPIRES
redis_client = Redis(host='34.242.139.134', port=6379, db=0, password='pastavase123')
jwt = JWTManager(app)

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    try:
        conn = databaseconn()
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"message": "Database Down"}), 500
    if conn is not None:
        data = request.get_json()
        username = data.get('username') 
        try:
            first_name, last_name = username.split(' ', 1)  # Limit to 1 space
        except ValueError:
            match = re.search(r"^(?P<first_name>\S+)\s+(?P<last_name>\S+)$", username)
            if match:
                first_name = match.group('first_name')
                last_name = match.group('last_name')
            else:
                return jsonify({"message": "Invalid username format"}), 400
        password = data.get('password')
        email = data.get('email')
        print(username,first_name,last_name,password,email)
        try:
            cursor = conn.cursor()
            # Check if the user already exists
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            existing_user = cursor.fetchone()
            if existing_user:
                # User already exists
                cursor.close()
                conn.close()
                return jsonify({"message": "User already exists"}), 409
            # User does not exist, proceed with signup
            password_hash = generate_password_hash(password)
            insert_query = """
                INSERT INTO users (first_name, last_name, password, email, created_at)
                VALUES (%s, %s, %s, %s, NOW())
            """
            cursor.execute(insert_query, (first_name,last_name, password_hash, email))
            conn.commit()
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
            stored_userID = user[0]
            cursor.close()
            identities = {
                    "email": email,
                    "userID": stored_userID
                }
            print(f"User '{username}' signed up successfully")
            conn.close()
            access_token = create_access_token(identity=identities)
            return jsonify({"message": "User signed up", "access_token": access_token}), 201
        except Exception as e:
            conn.rollback()
            print(f"Error: {e}")
            conn.close()
            return jsonify({"message": "Unable to sign up"}), 400

@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        conn = databaseconn()
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"message": "Database Down"}), 500
    if conn is not None:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        try:
            cursor = conn.cursor()
            # Check if the user exists
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
            if user:
                # Verify password
                stored_password_hash = user[4]  # Assuming password hash is stored in the third column
                stored_userID = user[0]
                identities = {
                    "email": email,
                    "userID": stored_userID
                }
                if check_password_hash(stored_password_hash, password):
                    # Passwords match, generate JWT token
                    access_token = create_access_token(identity=identities)
                    conn.close()
                    return jsonify({"message": "Login successful", "access_token": access_token}), 200
                else:
                    # Passwords don't match
                    conn.close()
                    return jsonify({"message": "Invalid email or password"}), 401
            else:
                # User not found
                conn.close()
                return jsonify({"message": "Invalid email or password"}), 401
        except Exception as e:
            print(f"Error: {e}")
            conn.close()
            return jsonify({"message": "Unable to login"}), 500

@app.route('/api/auth/logout', methods=['DELETE'])
@jwt_required()
def logout():
    jti = get_jwt()["jti"]
    print(jti)
    redis_client.set(jti, "", ex=ACCESS_EXPIRES)
    return jsonify(msg="Access token revoked")

# Callback function to check if a JWT exists in the redis blocklist
@jwt.token_in_blocklist_loader
def check_if_token_is_revoked(jwt_header, jwt_payload: dict):
    jti = jwt_payload["jti"]
    token_in_redis = redis_client.get(jti)
    return token_in_redis is not None

@app.route("/protected", methods=["GET"])
@jwt_required()
def protected():
    return jsonify(hello="world")

@app.route("/api/user/profile", methods=["GET"])
@jwt_required()
def user_profile():
    identities = get_jwt_identity()

    # Extract email and userID from the identities dictionary
    email = identities.get("email")
    userID = identities.get("userID")
    try:
        conn = databaseconn()
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"message": "Database Down"}), 500
    try:
        cursor = conn.cursor()
        # Check if the user exists
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user_profile_details = cursor.fetchone()
        if user_profile_details:
            return jsonify({"first_name": user_profile_details[1], "last_name": user_profile_details[2], "email": user_profile_details[3], "created_at": user_profile_details[5],}), 200
        else:
            # User not found
            conn.close()
            return jsonify({"message": "Invalid email or password"}), 401
    except Exception as e:
        print(f"Error: {e}")
        conn.close()
        return jsonify({"message": "Unable to login"}), 500

@app.route("/api/user/preferences", methods=["GET"])
@jwt_required()
def user_preferences():
    identities = get_jwt_identity()
    # Extract email and userID from the identities dictionary
    email = identities.get("email")
    userID = identities.get("userID")
    try:
        conn = databaseconn()
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"message": "Database Down"}), 500
    try:
        cursor = conn.cursor()
        # Check if the user exists
        cursor.execute("SELECT * FROM preferences WHERE user_id = %s", (userID,))
        user_preferences_details = cursor.fetchone()
        if user_preferences_details:
            return jsonify({"public_transport_weight": user_preferences_details[1], "bike_weight": user_preferences_details[2], "walking_weight": user_preferences_details[3], "driving_weight": user_preferences_details[4],}), 200
        else:
            # User not found
            conn.close()
            return jsonify({"message": "Invalid email or password"}), 401
    except Exception as e:
        print(f"Error: {e}")
        conn.close()
        return jsonify({"message": "Unable to login"}), 500

@app.route("/api/user/preferences", methods=["POST"])
@jwt_required()
def user_preferences_add():
    try:
        conn = databaseconn()
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"message": "Database Down"}), 500
    data = request.get_json()
    public_transport = data.get('public_transport')
    bike_weight = data.get('bike_weight')
    walking_weight = data.get('walking_weight')
    driving_weight = data.get('driving_weight')
    identities = get_jwt_identity()
    # Extract email and userID from the identities dictionary
    userID = identities.get("userID")
    try:
        cursor = conn.cursor()
        insert_query = """
            INSERT INTO preferences (user_id, public_transport, bike_weight, walking_weight, driving_weight, updated_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            ON CONFLICT (user_id) DO UPDATE SET
                public_transport = EXCLUDED.public_transport,
                bike_weight = EXCLUDED.bike_weight,
                walking_weight = EXCLUDED.walking_weight,
                driving_weight = EXCLUDED.driving_weight,
                updated_at = NOW()
        """
        cursor.execute(insert_query, (userID, public_transport, bike_weight, walking_weight, driving_weight))
        conn.commit()
        cursor.close()
        return jsonify({"message": "User preferences updated or added"}), 200

    except Exception as e:
        print(f"Error: {e}")
        conn.close()
        return jsonify({"message": "Unable to add to DB"}), 500

@app.route("/api/user/savedlocations", methods=["POST"])
@jwt_required()
def user_savedlocations_add():
    try:
        conn = databaseconn()
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"message": "Database Down"}), 500
    data = request.get_json()
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    location_name = data.get('location_name')
    identities = get_jwt_identity()
    # Extract email and userID from the identities dictionary
    userID = identities.get("userID")
    try:
        cursor = conn.cursor()
        insert_query = """
            INSERT INTO saved_locations (user_id, lat, long, location_name)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id, location_name) DO UPDATE SET
                lat = EXCLUDED.lat,
                long = EXCLUDED.long,
                user_id = EXCLUDED.user_id
        """
        cursor.execute(insert_query, (userID, latitude, longitude, location_name))
        conn.commit()
        cursor.close()
        return jsonify({"message": "User saved locations updated or added"}), 200

    except Exception as e:
        print(f"Error: {e}")
        conn.close()
        return jsonify({"message": "Unable to add to DB"}), 500    
    
@app.route("/api/user/savedlocations", methods=["GET"])
@jwt_required()
def user_savedlocations_get():
    try:
        conn = databaseconn()
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"message": "Database Down"}), 500
    identities = get_jwt_identity()
    # Extract email and userID from the identities dictionary
    # email = identities.get("email")
    userID = identities.get("userID")
    try:
        cursor = conn.cursor()
        # Check if the user exists
        cursor.execute("SELECT * FROM saved_locations WHERE user_id = %s", (userID,))
        saved_locations = cursor.fetchall()
        # print(saved_locations)
        if saved_locations:
            locations_data = []
            for location in saved_locations:
                location_data = {
                    "location_name": location[3],
                    "latitude": location[1],
                    "longitude": location[2]
                }
                locations_data.append(location_data)
            conn.close()
            return jsonify({"saved_locations": locations_data}), 200
        else:
            # No saved locations found for the user
            conn.close()
            return jsonify({"message": "No saved locations found"}), 404
    except Exception as e:
        print(f"Error: {e}")
        conn.close()
        return jsonify({"message": "Unable to get saved locations"}), 500

@app.route("/api/user/savedlocations", methods=["DELETE"])
@jwt_required()
def user_savedlocations_del():
    try:
        conn = databaseconn()
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"message": "Database Down"}), 500
    data = request.get_json()
    location_name = data.get('location_name')
    identities = get_jwt_identity()
    # Extract email and userID from the identities dictionary
    userID = identities.get("userID")
    try:
        cursor = conn.cursor()
        delete_query = """
            DELETE FROM saved_locations
            WHERE user_id = %s AND location_name = %s
        """
        cursor.execute(delete_query, (userID, location_name))
        conn.commit()
        cursor.close()
        return jsonify({"message": "Location deleted successfully"}), 200

    except Exception as e:
        print(f"Error: {e}")
        conn.close()
        return jsonify({"message": "Unable to delete location"}), 500

@app.route("/api/user/trips", methods=["POST"])
@jwt_required()
def user_trips_add():
    try:
        conn = databaseconn()
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"message": "Database Down"}), 500
    data = request.get_json()
    start_time = datetime.datetime.fromtimestamp(int(data.get('start_time')))
    end_time = datetime.datetime.fromtimestamp(int(data.get('end_time')))
    start_time = start_time.strftime('%Y-%m-%d %H:%M:%S')
    end_time = end_time.strftime('%Y-%m-%d %H:%M:%S')
    start_location = data.get('start_location')
    end_location = data.get('end_location')
    distance_walk = data.get('distance_walk', 0)
    distance_bike = data.get('distance_bike', 0)
    distance_bus = data.get('distance_bus', 0)
    distance_dart = data.get('distance_dart', 0)
    distance_car = data.get('distance_car', 0)
    distance_motorcycle = data.get('distance_motorcycle', 0)
    distance_taxi = data.get('distance_taxi', 0)
    distance_luas = data.get('distance_luas', 0)
    identities = get_jwt_identity()
    # Extract email and userID from the identities dictionary
    userID = identities.get("userID")
    try:
        cursor = conn.cursor()
        insert_query = """
            INSERT INTO trips (user_id, start_time, end_time, start_location, end_location, 
                            distance_walk, distance_bike, distance_bus, distance_dart, 
                            distance_car, distance_motorcycle, distance_taxi, distance_luas)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        # Execute the insert query
        # Make sure to replace 'user_id_value' with the actual user ID
        cursor.execute(insert_query, (userID, start_time, end_time, start_location, end_location,
                                    distance_walk, distance_bike, distance_bus, distance_dart,
                                    distance_car, distance_motorcycle, distance_taxi, distance_luas))
        conn.commit()
        cursor.close()
        return jsonify({"message": "Trip added"}), 200

    except Exception as e:
        print(f"Error: {e}")
        conn.close()
        return jsonify({"message": "Unable to add to DB"}), 500    
    
@app.route("/api/user/trips", methods=["GET"])
@jwt_required()
def user_trips_get():
    try:
        conn = databaseconn()
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"message": "Database Down"}), 500
    identities = get_jwt_identity()
    # Extract email and userID from the identities dictionary
    # email = identities.get("email")
    userID = identities.get("userID")
    try:
        cursor = conn.cursor()
        # Check if the user exists
        cursor.execute("SELECT * FROM trips WHERE user_id = %s", (userID,))
        trips = cursor.fetchall()
        # print(trips)
        if trips:
            trips_data = []
            for trip in trips:
                # print(type(trip), file=sys.stderr)
                trip_data = {
                    "start_time": int(datetime.datetime.fromisoformat(str(trip[1])).timestamp()),
                    "end_time": int(datetime.datetime.fromisoformat(str(trip[2])).timestamp()),
                    "start_location": trip[3],
                    "end_location": trip[4],
                    "distance_walk": trip[5],
                    "distance_bike": trip[7],
                    "distance_bus": trip[8],
                    "distance_dart": trip[9],
                    "distance_car": trip[10],
                    "distance_motorcycle": trip[11],
                    "distance_taxi": trip[12],
                    "distance_luas": trip[13]
                }
                trips_data.append(trip_data)
            conn.close()
            return jsonify({"saved_locations": trips_data}), 200
        else:
            # No saved locations found for the user
            conn.close()
            return jsonify({"message": "No trips found"}), 404
    except Exception as e:
        print(f"Error: {e}")
        conn.close()
        return jsonify({"message": e}), 500
    
# def check_for_badge():

if __name__ == '__main__':
    
    app.run(ssl_context='adhoc', debug=True, host="0.0.0.0", port= 5000)  
