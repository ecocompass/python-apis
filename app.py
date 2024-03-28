import os

from flask import Flask, jsonify, request
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import timedelta

import datetime
import psycopg2
import re
from redis import Redis
import requests

try:
    POSTGRES_HOST_NAME = os.environ.get('POSTGRES_HOST_NAME')
    POSTGRES_PORT = os.environ.get('POSTGRES_PORT')
    POSTGRES_DATABASE = os.environ.get('POSTGRES_DATABASE')
    POSTGRES_USER = os.environ.get('POSTGRES_USER')
    POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD')
except Exception as e:
    print(f"cannot fetch POSTGRES DB details from environment {e}")


try:
    REDIS_HOST_NAME = os.environ.get('REDIS_HOST_NAME')
    REDIS_PORT = os.environ.get('REDIS_PORT')
    REDIS_DATABASE = os.environ.get('REDIS_DATABASE')
    REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD')
except Exception as e:
    print(f"cannot fetch REDIS details from environment {e}")

try:
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    JWT_ACCESS_TOKEN_EXPIRE_HOURS = int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRE_HOURS'))
except Exception as e:
    print(f"cannot fetch JWT details from environment {e}")


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
        print(f"An error occurred: {e}")
        
app = Flask(__name__)
ACCESS_EXPIRES = timedelta(hours=JWT_ACCESS_TOKEN_EXPIRE_HOURS)
FORWARD_URL = "http://routing-engine-service.default.svc.cluster.local"

app.config['JWT_SECRET_KEY'] = JWT_SECRET_KEY
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = ACCESS_EXPIRES

redis_client = Redis(host=REDIS_HOST_NAME, port=REDIS_PORT, db=REDIS_DATABASE, password=REDIS_PASSWORD)
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
            cursor.close()
            print(f"User '{username}' signed up successfully")
            conn.close()
            access_token = create_access_token(identity=email)
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
                if check_password_hash(stored_password_hash, password):
                    # Passwords match, generate JWT token
                    access_token = create_access_token(identity=email)
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

# forward request
@app.route('/api/routes', methods=['GET'])
def get_route():
    start_coordinates = request.args.get('startCoordinates')
    end_coordinates = request.args.get('endCoordinates')

    forward_params = {
        'startCoordinates': start_coordinates,
        'endCoordinates': end_coordinates
    }
    
    response = requests.get(FORWARD_URL + "/api/routes", params=forward_params)

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
    response = requests.get(FORWARD_URL + "/api/routes2", params=forward_params)

    return jsonify(response.json()), response.status_code

# for load-balancer healthcheck
@app.route('/', methods=['GET'])
def health():
    return jsonify({"message": "All okay!"})


if __name__ == '__main__':
    
    app.run(debug=True, host="0.0.0.0", port= 6969)  
