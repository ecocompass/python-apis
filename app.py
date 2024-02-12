from flask import Flask, jsonify, request
from flask_jwt_extended import JWTManager, create_access_token, jwt_required
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import timedelta
import datetime
import psycopg2
import re
import redis

# Connect to Redis
# r = redis.Redis(host='140.238.228.234', port=9090, db=0)
# # Example usage
# r.set('key', 'value')

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

app.config['JWT_SECRET_KEY'] = 'chakdephatte'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)  
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


@app.route('/api/auth/logout', methods=['POST'])
def logout():
    
    return jsonify({"message": "User logged out"}), 200

@app.route('/api/user/profile', methods=['GET'])
def get_user_profile():
    # TODO: Fetch user profile information
    return jsonify({"profile": "user_profile_data"}), 200

@app.route('/api/user/badges', methods=['GET'])
def get_user_badges():
    # TODO: Fetch user badges
    return jsonify({"badges": ["badge1", "badge2"]}), 200

# Continue defining other routes similarly...

if __name__ == '__main__':
    
    app.run(debug=True, host="0.0.0.0", port= 6969)  
