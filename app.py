from flask import Flask, jsonify, request
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt, get_jwt_identity
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import timedelta

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
ACCESS_EXPIRES = timedelta(hours=1)

app.config['JWT_SECRET_KEY'] = 'chakdephatte'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = ACCESS_EXPIRES
redis_client = Redis(host='3.109.181.143', port=6379, db=0, password='pastavase123')
jwt = JWTManager(app)

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    conn = databaseconn() 
    
    if conn:
        data = request.get_json()
        username = data.get('username') 
        if username is None:
            return jsonify({"message": "Empty Username"}), 400
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
    else:
        return jsonify({"message": "Database Down"}), 500

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
        if email is None or password is None:
            return jsonify({"message": "Empty email or password"}), 400
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
        conn = databaseconn()
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"message": "Database Down"}), 500
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
    

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port= 6969)  
