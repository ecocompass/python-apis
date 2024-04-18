import os
from scipy.spatial import KDTree
from flask import Flask, jsonify, request, Response
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt, get_jwt_identity
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import timedelta
import datetime
import logging
logging.basicConfig(level=logging.DEBUG)
import sys
import time
import datetime
import psycopg2
import re
from redis import Redis
import requests
import json
_default_expiry_hours = 24  
JWT_ACCESS_TOKEN_EXPIRE_HOURS = int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRE_HOURS', '24'))
try:
    POSTGRES_HOST_NAME = os.environ.get('POSTGRES_HOST_NAME')
    POSTGRES_PORT = os.environ.get('POSTGRES_PORT')
    POSTGRES_DATABASE = os.environ.get('POSTGRES_DATABASE')
    POSTGRES_USER = os.environ.get('POSTGRES_USER')
    POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD')
except Exception as e:
    logging.error(f"cannot fetch POSTGRES DB details from environment {e}")


try:
    REDIS_HOST_NAME = os.environ.get('REDIS_HOST_NAME')
    REDIS_PORT = os.environ.get('REDIS_PORT')
    REDIS_DATABASE = os.environ.get('REDIS_DATABASE')
    REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD')
except Exception as e:
    logging.error(f"cannot fetch REDIS details from environment {e}")

JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
JWT_ACCESS_TOKEN_EXPIRE_HOURS = int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRE_HOURS'))

def databaseconn():
    try:
        conn = psycopg2.connect(
            host=POSTGRES_HOST_NAME,
            port=POSTGRES_PORT,
            database=POSTGRES_DATABASE,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD
        )
        return conn
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        
app = Flask(__name__)
ACCESS_EXPIRES = timedelta(hours=JWT_ACCESS_TOKEN_EXPIRE_HOURS)
FORWARD_URL = "http://routing-engine-service.default.svc.cluster.local:8080"

app.config['JWT_SECRET_KEY'] = JWT_SECRET_KEY
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = ACCESS_EXPIRES

redis_client = Redis(host=REDIS_HOST_NAME, port=REDIS_PORT, db=REDIS_DATABASE, password=REDIS_PASSWORD)
jwt = JWTManager(app)
transitmap = None
@app.route('/api/auth/signup', methods=['POST'])
def signup():
    try:
        conn = databaseconn()
    except Exception as e:
        logging.error(f"An error occurred: {e}")
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
        # logging.info(username,first_name,last_name,password,email)
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
            # logging.info(f"User '{username}' signed up successfully")
            conn.close()
            access_token = create_access_token(identity=identities)
            return jsonify({"message": "User signed up", "access_token": access_token}), 201
        except Exception as e:
            conn.rollback()
            logging.error(f": {e}")
            conn.close()
            return jsonify({"message": "Unable to sign up"}), 400

@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        conn = databaseconn()
    except Exception as e:
        # logging.error(f"An error occurred: {e}")
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
            # logging.error(f": {e}")
            conn.close()
            return jsonify({"message": "Unable to login"}), 500

@app.route('/api/auth/logout', methods=['DELETE'])
@jwt_required()
def logout():
    jti = get_jwt()["jti"]
    # logging.info(jti)
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
        # logging.error(f"An error occurred: {e}")
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
        # logging.error(f": {e}")
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
        # logging.error(f"An error occurred: {e}")
        return jsonify({"message": "Database Down"}), 500
    try:
        cursor = conn.cursor()
        # Check if the user exists
        cursor.execute("SELECT * FROM preferences WHERE user_id = %s", (userID,))
        user_preferences_details = cursor.fetchone()
        if user_preferences_details:
            return jsonify({"payload": {"public_transport_weight": user_preferences_details[1], "bike_weight": user_preferences_details[2], "walking_weight": user_preferences_details[3], "driving_weight": user_preferences_details[4],}}), 200
        else:
            # User not found
            conn.close()
            return jsonify({"payload": False}), 200
    except Exception as e:
        # logging.error(f": {e}")
        conn.close()
        return jsonify({"message": "Unable to login"}), 500

@app.route("/api/user/preferences", methods=["POST"])
@jwt_required()
def user_preferences_add():
    try:
        conn = databaseconn()
    except Exception as e:
        # logging.error(f"An error occurred: {e}")
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
        # logging.error(f": {e}")
        conn.close()
        return jsonify({"message": "Unable to add to DB"}), 500

@app.route("/api/user/savedlocations", methods=["POST"])
@jwt_required()
def user_savedlocations_add():
    try:
        conn = databaseconn()
    except Exception as e:
        # logging.error(f"An error occurred: {e}")
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
        logging.error(f": {e}")
        conn.close()
        return jsonify({"message": "Unable to add to DB"}), 500    

# forward request
@app.route('/api/routes', methods=['GET'])
def get_route():
    start_coordinates = request.args.get('startCoordinates')
    end_coordinates = request.args.get('endCoordinates')

    forward_params = {
        'startCoordinates': start_coordinates,
        'endCoordinates': end_coordinates
    }
    logging.info("relaying routing request to routing engine") 
    logging.info(f"params: {forward_params}")
    response = requests.get(FORWARD_URL + "/api/routes", params=forward_params)
    logging.info(f"engine response: {response.status_code}")

    return jsonify(response.json()), response.status_code

# forward request
@app.route('/api/routes2', methods=['GET'])
def get_route2():
    start_coordinates = request.args.get('startCoordinates')
    end_coordinates = request.args.get('endCoordinates')

    forward_params = {
        'startCoordinates': start_coordinates,
        'endCoordinates': end_coordinates
    }
    logging.info("relaying routing2 request to routing engine")
    logging.info(f"params: {forward_params}")
    response = requests.get(FORWARD_URL + "/api/routes2", params=forward_params)
    logging.info(f"engine response: {response.status_code}")

    return jsonify(response.json()), response.status_code

@app.route('/api/transit/incidents', methods=['GET'])
def get_traffic_incidents():
    recommendation_id = request.args.get('recommendationId')
    response = requests.get(FORWARD_URL + "/api/transit/incidents", params={'recommendationId': recommendation_id})
    logging.info(f"relaying transit incidents request: recommendationId={recommendation_id}")
    logging.info(f"backend response: {response.status_code}")
    return jsonify(response.json()), response.status_code

@app.route('/createIncident', methods=['POST'])
def create_incident():
    incident_data = request.get_json()
    response = requests.post(FORWARD_URL + "/createIncident", json=incident_data)
    logging.info(f"relaying incident creation request: {incident_data}")
    logging.info(f"backend response: {response.status_code}")
    return Response(response.text, status=response.status_code, mimetype='application/json')

@app.route('/deleteIncident/<incidentId>', methods=['DELETE'])
def delete_incident(incidentId):
    response = requests.delete(FORWARD_URL + f"/deleteIncident/{incidentId}")
    logging.info(f"relaying delete incident request: incidentId={incidentId}")
    logging.info(f"backend response: {response.status_code}")
    return Response(response.text, status=response.status_code, mimetype='application/json')

@app.route('/api/incidents', methods=['GET'])
def get_all_incidents():
    response = requests.get(FORWARD_URL + "/api/incidents")
    logging.info("relaying get all incidents request")
    logging.info(f"backend response: {response.status_code}")
    return jsonify(response.json()), response.status_code

# for load-balancer healthcheck
@app.route('/', methods=['GET'])
def health():
    return jsonify({"message": "All okay!"})

@app.route("/api/user/savedlocations", methods=["GET"])
@jwt_required()
def user_savedlocations_get():
    try:
        conn = databaseconn()
    except Exception as e:
        # logging.error(f"An error occurred: {e}")
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
        # logging.info(saved_locations)
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
        logging.error(f": {e}")
        conn.close()
        return jsonify({"message": "Unable to get saved locations"}), 500

@app.route("/api/user/savedlocations", methods=["DELETE"])
@jwt_required()
def user_savedlocations_del():
    try:
        conn = databaseconn()
    except Exception as e:
        logging.error(f"An error occurred: {e}")
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
        logging.error(f": {e}")
        conn.close()
        return jsonify({"message": "Unable to delete location"}), 500


def awards_from_goals(userID, start_time):
    try:
        conn = databaseconn()
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return jsonify({"message": "Database Down"}), 500
    try:
        trip_start_date = datetime.datetime.fromtimestamp(int(start_time))
        week_start_date = get_week_start_date(trip_start_date)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM goals WHERE user_id = %s", (userID,))
        goals = cursor.fetchall()
        # logging.info(goals, file=sys.stderr)
        cursor.execute("SELECT * FROM weekly_user_stats WHERE user_id = %s AND week_start_date = %s",
                       (userID, week_start_date))
        stats = cursor.fetchone()
        # logging.info(stats)
        # _, _, _, public_transport, cycling, walking = stats
        public_transport = stats[3]
        cycling = stats[4]
        walking = stats[5]
        car = stats[6]
        goal_walking = stats[7]
        goal_cycling = stats[8]
        goal_public_transport = stats[9]
        # logging.info("public_transport for awards: ",public_transport)
        # logging.info("cycling for awards: ",cycling)
        # logging.info("walking for awards: ",walking)
        public_transport_awards = []
        cycling_awards = []
        walking_awards = []
        change = False

        if goal_walking and goal_cycling and goal_public_transport == True:
            return False
        
        for goal in goals:
            goal_type = goal[1]
            goal_target = goal[2]
            # logging.info(goal_type)
            # logging.info(goal_target)
            # , goal_target, _, _, _ = goal
            if goal_type == 'walking' and goal_walking == False:
                if walking >= goal_target:
                    walking_awards.append(f"Achievement Unlocked: Reached walking goal of {goal_target} km.")
                    goal_walking = True
                    change = True
            elif goal_type == 'cycling' and goal_cycling == False:
                if cycling >= goal_target:
                    # logging.info(f"Achievement Unlocked: Reached biking goal of {goal_target} km.")
                    cycling_awards.append(f"Achievement Unlocked: Reached biking goal of {goal_target} km.")
                    goal_cycling = True
                    change = True
            elif goal_type == 'public_transport' and goal_public_transport == False:
                if public_transport >= goal_target:
                    public_transport_awards.append(f"Achievement Unlocked: Reached public transport goal of {goal_target} km.")
                    goal_public_transport = True
                    change = True

        if change:
            try:
                cursor = conn.cursor()
                insert_query = """
                    INSERT INTO weekly_user_stats (user_id, week_start_date, goal_walking, goal_cycling, goal_public_transport)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, week_start_date) DO UPDATE SET
                        goal_walking = EXCLUDED.goal_walking,
                        goal_cycling = EXCLUDED.goal_cycling,
                        goal_public_transport = EXCLUDED.goal_public_transport
                """
                cursor.execute(insert_query, (userID, week_start_date, goal_walking, goal_cycling, goal_public_transport))
                conn.commit()
                cursor.close()
            except Exception as e:
                logging.error(f"An error occurred: {e}")
                conn.rollback()
            finally:
                conn.close()

        payload = {}
        if cycling_awards:
            payload["awards for biking"] = cycling_awards
        if walking_awards:
            payload["awards for walking"] = walking_awards
        if public_transport_awards:
            payload["awards for public transport"] = public_transport_awards
    
        if payload:
            # print(payload)
            # logging.info(payload)
            return payload
        else:
            # logging.info("No awards")
            return False
    except Exception as e:
        logging.error(f" in the awards: {e}")
        conn.close()
        return False    

def get_week_start_date(date):
    """
    Function to calculate the start date of the week for a given date.
    """
    return (date - datetime.timedelta(days=date.weekday())).date()

def save_weekly_data(userID, start_time, walking, cycling, distance_bus, distance_dart, distance_car, distance_luas):
    try:
        conn = databaseconn()
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return False
    trip_start_date = datetime.datetime.fromtimestamp(int(start_time))
    week_start_date = get_week_start_date(trip_start_date)
    # logging.info(week_start_date)
    public_transport = float(distance_bus) + float(distance_dart) + float(distance_luas)
    try:
        cursor = conn.cursor()
        insert_query = """
            INSERT INTO weekly_user_stats (user_id, week_start_date, public_transport, cycling, walking, car)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id, week_start_date) DO UPDATE SET
                car = weekly_user_stats.car + EXCLUDED.car,
                public_transport = weekly_user_stats.public_transport + EXCLUDED.public_transport,
                cycling = weekly_user_stats.cycling + EXCLUDED.cycling,
                walking = weekly_user_stats.walking + EXCLUDED.walking,
                week_start_date = EXCLUDED.week_start_date,
                user_id = weekly_user_stats.user_id
        """
        cursor.execute(insert_query, (userID, week_start_date, str(public_transport), cycling, walking, distance_car))
        conn.commit()
        conn.close()
        return True

    except Exception as e:
        logging.error(f"An error occurred in weekly data saving: {e}")
        return False

@app.route("/api/user/trips", methods=["POST"])
@jwt_required()
def user_trips_add():
    try:
        conn = databaseconn()
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return jsonify({"message": "Database Down"}), 500
    data = request.get_json()
    start_time_weekly = int(data.get('start_time'))
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
    route = data.get('route', 0)
    if float(distance_walk) >= 1:
        walking_streak = 1
    else:
        walking_streak = 0
    
    if float(distance_bike) >=1:
        cycle_streak = 1
    else:
        cycle_streak = 0
    identities = get_jwt_identity()
    completed_trips = 1
    # Extract email and userID from the identities dictionary
    userID = identities.get("userID")
    try:
        cursor = conn.cursor()
        try:
            with conn:
                insert_query = """
                    INSERT INTO trips (user_id, start_time, end_time, start_location, end_location, 
                                    distance_walk, distance_bike, distance_bus, distance_dart, 
                                    distance_car, distance_motorcycle, distance_taxi, distance_luas, route)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(insert_query, (userID, start_time, end_time, start_location, end_location,
                                            distance_walk, distance_bike, distance_bus, distance_dart,
                                            distance_car, distance_motorcycle, distance_taxi, distance_luas, route))
                
                insert_query_stats = """
                    INSERT INTO user_statistics (user_id, Total_Distance_walk, Total_Distance_bike, Cycle_Streak, Walking_streak, 
                                        Completed_trips, Total_Distance_bus, Total_Distance_dart, Total_Distance_car, 
                                        Total_Distance_luas)
                    VALUES (%s, %s, %s, %s, %s, (SELECT COUNT(*) FROM trips WHERE user_id = %s), %s, %s, %s, %s)
                    ON CONFLICT (user_id)
                    DO UPDATE SET
                        Total_Distance_walk = user_statistics.Total_Distance_walk + EXCLUDED.Total_Distance_walk,
                        Total_Distance_bike = user_statistics.Total_Distance_bike + EXCLUDED.Total_Distance_bike,
                        Cycle_Streak = CASE WHEN EXCLUDED.Cycle_Streak = 0 THEN 0 ELSE user_statistics.Cycle_Streak + EXCLUDED.Cycle_Streak END,
                        Walking_streak = CASE WHEN EXCLUDED.Walking_streak = 0 THEN 0 ELSE user_statistics.Walking_streak + EXCLUDED.Walking_streak END,
                        Completed_trips = EXCLUDED.Completed_trips,
                        Total_Distance_bus = user_statistics.Total_Distance_bus + EXCLUDED.Total_Distance_bus,
                        Total_Distance_dart = user_statistics.Total_Distance_dart + EXCLUDED.Total_Distance_dart,
                        Total_Distance_car = user_statistics.Total_Distance_car + EXCLUDED.Total_Distance_car,
                        Total_Distance_luas = user_statistics.Total_Distance_luas + EXCLUDED.Total_Distance_luas;
                """
                cursor.execute(insert_query_stats, (userID, distance_walk, distance_bike, cycle_streak, walking_streak,
                                            userID, distance_bus, distance_dart,
                                            distance_car, distance_luas))
        except Exception as e:
            logging.error(f"An error occurred: {e}")
            return jsonify({"payload": "Database Error"}), 500
        else:
            conn.commit()
            conn.close()
        # logging.info(userID, start_time_weekly, distance_walk, distance_bike, distance_bus, distance_dart, distance_car, distance_luas)
        weekly_data = save_weekly_data(userID, start_time_weekly, distance_walk, distance_bike, distance_bus, distance_dart, distance_car, distance_luas)
        if weekly_data == True:
            logging.info("weekly data saved in db")
            awards_result = awards_from_goals(userID, start_time_weekly)

            # logging.info(awards_result)
            if awards_result:
                # return jsonify({"message": "Saved Trips", "payload": awards_result}), 200
                return jsonify({"payload": {"message": "Saved Trips", "awards": awards_result}}), 200
            else:
                return jsonify({"payload": "Saved Trips"}), 200
        else:
            logging.info("unable to save weekly data in db")
            return jsonify({"payload": "Saved Trips"}), 200
    except Exception as e:
        logging.error(f" in the trips: {e}")
        conn.close()
        return jsonify({"payload": "Unable to add to DB"}), 500    
    
@app.route("/api/user/trips", methods=["GET"])
@jwt_required()
def user_trips_get():
    try:
        conn = databaseconn()
    except Exception as e:
        logging.error(f"An error occurred: {e}")
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
        # logging.info(trips)
        if trips:
            trips_data = []
            for trip in trips:
                # logging.info(type(trip), file=sys.stderr)
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
                    "distance_luas": trip[13], 
                    "route": trip[14]
                }
                trips_data.append(trip_data)
            conn.close()
            return jsonify({"saved_locations": trips_data}), 200
        else:
            # No saved locations found for the user
            conn.close()
            return jsonify({"message": "No trips found"}), 404
    except Exception as e:
        logging.error(f": {e}")
        conn.close()
        return jsonify({"message": e}), 500
    
@app.route("/api/user/trips", methods=["DELETE"])
@jwt_required()
def user_trips_del():
    try:
        conn = databaseconn()
    except Exception as e:
        logging.error(f"An error occurred: {e}")
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
        delete_query = """
            DELETE FROM trips
            WHERE user_id = %s
            AND start_time = %s
            AND end_time = %s
            AND start_location = %s
            AND end_location = %s
            AND distance_walk = %s
            AND distance_bike = %s
            AND distance_bus = %s
            AND distance_dart = %s
            AND distance_car = %s
            AND distance_motorcycle = %s
            AND distance_taxi = %s
            AND distance_luas = %s;
        """
        cursor.execute(delete_query, (userID, start_time, end_time, start_location, end_location, 
                                    distance_walk, distance_bike, distance_bus, distance_dart, 
                                    distance_car, distance_motorcycle, distance_taxi, distance_luas))
        conn.commit()
        cursor.close()
        return jsonify({"message": "Location deleted successfully"}), 200

    except Exception as e:
        logging.error(f": {e}")
        conn.close()
        return jsonify({"message": "Unable to delete location"}), 500


@app.route("/api/user/routes", methods=["POST"])
@jwt_required()
def user_routes_add():
    try:
        conn = databaseconn()
    except Exception as e:
        # logging.error(f"An error occurred: {e}")
        return jsonify({"message": "Database Down"}), 500
    data = request.get_json()
    route = data.get('route')
    route_name = data.get('route_name')
    identities = get_jwt_identity()
    # Extract email and userID from the identities dictionary
    userID = identities.get("userID")
    try:
        cursor = conn.cursor()
        insert_query = """
            INSERT INTO routes (user_id, route_val, route_name)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, route_name) DO UPDATE SET
                route_val = EXCLUDED.route_val,
                user_id = EXCLUDED.user_id
        """
        cursor.execute(insert_query, (userID, route, route_name))
        conn.commit()
        cursor.close()
        return jsonify({"message": "User saved routes updated or added"}), 200

    except Exception as e:
        logging.error(f": {e}")
        conn.close()
        return jsonify({"message": "Unable to add to DB"}), 500    


@app.route("/api/user/routes", methods=["GET"])
@jwt_required()
def user_routes_get():
    try:
        conn = databaseconn()
    except Exception as e:
        # logging.error(f"An error occurred: {e}")
        return jsonify({"message": "Database Down"}), 500
    identities = get_jwt_identity()
    # Extract email and userID from the identities dictionary
    # email = identities.get("email")
    userID = identities.get("userID")
    try:
        cursor = conn.cursor()
        # Check if the user exists
        cursor.execute("SELECT * FROM routes WHERE user_id = %s", (userID,))
        saved_routes = cursor.fetchall()
        # logging.info(saved_locations)
        if saved_routes:
            routes_data = []
            for route in saved_routes:
                route_data = {
                    "route_name": route[3],
                    "route": route[2]
                }
                routes_data.append(route_data)
            conn.close()
            return jsonify({"payload": routes_data}), 200
        else:
            # No saved locations found for the user
            conn.close()
            return jsonify({"payload": False}), 200
    except Exception as e:
        logging.error(f": {e}")
        conn.close()
        return jsonify({"message": "Unable to get saved routes"}), 500


@app.route("/api/user/routes", methods=["DELETE"])
@jwt_required()
def user_routes_del():
    try:
        conn = databaseconn()
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return jsonify({"message": "Database Down"}), 500
    data = request.get_json()
    route_name = data.get('route_name')
    identities = get_jwt_identity()
    # Extract email and userID from the identities dictionary
    userID = identities.get("userID")
    try:
        cursor = conn.cursor()
        delete_query = """
            DELETE FROM routes
            WHERE user_id = %s AND route_name = %s
        """
        cursor.execute(delete_query, (userID, route_name))
        conn.commit()
        cursor.close()
        return jsonify({"message": "Route deleted successfully"}), 200

    except Exception as e:
        logging.error(f": {e}")
        conn.close()
        return jsonify({"message": "Unable to delete route"}), 500
    
@app.route("/api/user/goals", methods=["POST"])
@jwt_required()
def user_goals_add():
    try:
        conn = databaseconn()
    except Exception as e:
        return jsonify({"message": "Database Down"}), 500

    data = request.get_json()

    try:
        cursor = conn.cursor()

        for goal_data in data:
            targettype = goal_data.get('type')
            target = goal_data.get('target')
            createdat = datetime.datetime.fromtimestamp(int(goal_data.get('created_at')))
            expiry = datetime.datetime.fromtimestamp(int(goal_data.get('expiry')))
            identities = get_jwt_identity()
            userID = identities.get("userID")

            insert_query = """
                INSERT INTO goals (user_id, type, target, created_at, expiry)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (user_id, type) DO UPDATE SET
                    type = EXCLUDED.type,
                    user_id = EXCLUDED.user_id,
                    target = EXCLUDED.target,
                    created_at = EXCLUDED.created_at,
                    expiry = EXCLUDED.expiry
            """
            cursor.execute(insert_query, (userID, targettype, target, createdat, expiry))
            conn.commit()

        cursor.close()
        return jsonify({"message": "User goals updated or added"}), 200

    except Exception as e:
        logging.error(f": {e}", file=sys.stderr)
        conn.rollback()  # Rollback changes if an error occurs
        return jsonify({"message": "Unable to add to DB"}), 500
    finally:
        conn.close()
 

@app.route("/api/user/goals", methods=["GET"])
@jwt_required()
def user_goals_get():
    try:
        conn = databaseconn()
    except Exception as e:
        # logging.error(f"An error occurred: {e}")
        return jsonify({"message": "Database Down"}), 500
    identities = get_jwt_identity()
    # Extract email and userID from the identities dictionary
    # email = identities.get("email")
    trip_start_date = datetime.datetime.fromtimestamp(int(request.args.get('start_time')))
    week_start_date = get_week_start_date(trip_start_date)
    logging.info(week_start_date)
    userID = identities.get("userID")
    try:
        cursor = conn.cursor()
        # Check if the user exists
        cursor.execute("SELECT * FROM goals WHERE user_id = %s", (userID,))
        saved_goals = cursor.fetchall()
        # logging.info(saved_goals)
        try:
            cursor.execute("SELECT * FROM weekly_user_stats WHERE user_id = %s AND week_start_date = %s",
                        (userID, week_start_date))
            stats = cursor.fetchone()
            logging.info(stats)
            public_transport = stats[3]
            cycling = stats[4]
            walking = stats[5]
            if saved_goals:
                goals_data = []
                for goal in saved_goals:
                    if goal[1] == "walking":
                        goal_data = {
                            "type": goal[1],
                            "target": goal[2],
                            "current": walking,
                            "created_at": int(datetime.datetime.fromisoformat(str(goal[3])).timestamp()),
                            "expiry": int(datetime.datetime.fromisoformat(str(goal[4])).timestamp())
                        }
                    elif goal[1] == "cycling":
                        goal_data = {
                            "type": goal[1],
                            "target": goal[2],
                            "current": cycling,
                            "created_at": int(datetime.datetime.fromisoformat(str(goal[3])).timestamp()),
                            "expiry": int(datetime.datetime.fromisoformat(str(goal[4])).timestamp())
                        }
                    elif goal[1] == "public_transport":
                        goal_data = {
                            "type": goal[1],
                            "target": goal[2],
                            "current": public_transport,
                            "created_at": int(datetime.datetime.fromisoformat(str(goal[3])).timestamp()),
                            "expiry": int(datetime.datetime.fromisoformat(str(goal[4])).timestamp())
                        }
                    goals_data.append(goal_data)
                conn.close()
                return jsonify({"payload": goals_data}), 200
            else:
                conn.close()
                return jsonify({"payload": False}), 200
        except Exception as e:
            logging.error(f": {e}")
        if saved_goals:
            goals_data = []
            for goal in saved_goals:
                goal_data = {
                    "type": goal[1],
                    "target": goal[2],
                    "created_at": int(datetime.datetime.fromisoformat(str(goal[3])).timestamp()),
                    "expiry": int(datetime.datetime.fromisoformat(str(goal[4])).timestamp())
                }
                goals_data.append(goal_data)
            conn.close()
            return jsonify({"payload": goals_data}), 200
        else:
            conn.close()
            return jsonify({"payload": False}), 200
    except Exception as e:
        logging.error(f": {e}")
        conn.close()
        return jsonify({"message": "Unable to get saved goals"}), 500

@app.route("/api/user/goals", methods=["DELETE"])
@jwt_required()
def user_goals_del():
    try:
        conn = databaseconn()
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return jsonify({"message": "Database Down"}), 500
    data = request.get_json()
    goaltype = data.get('type')
    identities = get_jwt_identity()
    # Extract email and userID from the identities dictionary
    userID = identities.get("userID")
    try:
        cursor = conn.cursor()
        delete_query = """
            DELETE FROM goals
            WHERE user_id = %s AND type = %s
        """
        cursor.execute(delete_query, (userID, goaltype))
        conn.commit()
        cursor.close()
        return jsonify({"message": "Goal deleted successfully"}), 200

    except Exception as e:
        logging.error(f": {e}")
        conn.close()
        return jsonify({"message": "Unable to delete goal"}), 500
    

kd_trees_global = {}
nodes_global = {}

def get_nearest_nodes(root, mode, k=25):
    global kd_trees_global
    global nodes_global
    global transitmap
    
    results = []

    if mode == 'bus':
        tree = kd_trees_global.get('bus')
        nodes = nodes_global.get('bus')
        if tree and nodes:
            distances, indices = tree.query((root[0], root[1]), k=k)
            for i in indices:
                stop_id = nodes[i]
                data = transitmap["bus_stops"].get(stop_id)
                if data:
                    result = {
                        "stop_id": stop_id,
                        "name": data.get('name'),
                        "lat": data.get('lat'),
                        "lon": data.get('lon')
                    }
                    results.append(result)
        return results
    elif mode == 'luas':
        tree = kd_trees_global.get('luas')
        nodes = nodes_global.get('luas')
        if tree and nodes:
            distances, indices = tree.query((root[0], root[1]), k=k)
            for i in indices:
                stop_id = nodes[i]
                data = transitmap["luas_stops"].get(stop_id)
                if data:
                    result = {
                        "stop_id": stop_id,
                        "name": data.get('name'),
                        "lat": data.get('lat'),
                        "lon": data.get('lon')
                    }
                    results.append(result)
        return results
    else:
        return False


@app.route("/api/get_nearest_nodes", methods=["GET"])
def get_nearest_nodes_api():
    try:
        # Get parameters from the request
        k = int(request.args.get('k', 25))
        lat = float(request.args.get('lat'))
        lon = float(request.args.get('lon'))
        mode = request.args.get('mode')

        # Fetch the appropriate KD tree and nodes based on your application logic
        if mode == 'bus':
            nearest_nodes = get_nearest_nodes((lat, lon),mode, k=k)
        elif mode == 'luas':
            nearest_nodes = get_nearest_nodes((lat, lon),mode, k=k)
        else:
            return jsonify({"error": "Invalid mode"}), 400

        if nearest_nodes:
            return jsonify({"nearest_nodes": nearest_nodes}), 200
        else:
            return jsonify({"error": "KD tree or nodes not found for the given type"}), 404

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return jsonify({"error": str(e)}), 500
    
def build_kd_tree_bus(node_map):
    logging.info("building kd tree for bus")
    global kd_trees_global
    global nodes_global
    try:
        # Extract node keys and their corresponding lat and lon to build the kd-tree
        nodes_global['bus'] = list(node_map.keys())
        coordinates = [(info['lat'], info['lon']) for info in node_map.values()]
        # Construct KDTree with the coordinates
        kd_trees_global['bus'] = KDTree(coordinates)
        return True
    except Exception as e:
        logging.error(e)
        return False

def build_kd_tree_luas(node_map):
    logging.info("building kd tree for bus")
    global kd_trees_global
    global nodes_global
    try:
        # Extract node keys and their corresponding lat and lon to build the kd-tree
        nodes_global['luas'] = list(node_map.keys())
        coordinates = [(info['lat'], info['lon']) for info in node_map.values()]
        # Construct KDTree with the coordinates
        kd_trees_global['luas'] = KDTree(coordinates)
        return True
    except Exception as e:
        logging.error(e)
        return False
    

if __name__ == '__main__':
    with open("consolidated_gtfs.json", "r", encoding="utf-8") as file:
            transitmap = json.loads(file.read())
    kd_bus = build_kd_tree_bus(transitmap["bus_stops"])
    if kd_bus:
        logging.info("kd tree for bus built successfully")
    else:
        logging.info("kd tree for bus not built")
    kd_luas = build_kd_tree_luas(transitmap["luas_stops"])
    if kd_luas:
        logging.info("kd tree for bus built successfully")
    else:
        logging.info("kd tree for bus not built")


    app.run(debug=False, host="0.0.0.0", port= 5050)
