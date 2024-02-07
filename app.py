from flask import Flask, jsonify, request
import jwt
import datetime
import psycopg2
def databaseconn():
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5433,
            database="Dynamic_way_finding",
            user="postgres",
            password="1881"
        )
        return conn
    except Exception as e:
        print(f"An error occurred: {e}")
        

app = Flask(__name__)
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
        password = data.get('password')
        try:
            # Create a cursor object to interact with the database
            cursor = conn.cursor()

            # Define the SQL INSERT statement
            insert_query = """
                INSERT INTO users (username, pass, created_at)
                VALUES (%s, %s, NOW())
            """

            # Execute the INSERT statement
            cursor.execute(insert_query, (username, password))

            # Commit the transaction
            conn.commit()

            # Close the cursor
            cursor.close()

            print(f"User '{username}' signed up successfully")
            conn.close()
            return jsonify({"message": "User signed up"}), 201
        except Exception as e:
            conn.rollback()  # Rollback the transaction in case of an error
            print(f"Error: {e}")
            conn.close()
            return jsonify({"message": "Unable to sign up"}), 400



@app.route('/api/auth/login', methods=['POST'])
def login():
   # TODO: Implement logout logic (token revocation)
    return jsonify({"token": "generated_token"}), 200

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    # TODO: Implement logout logic (token revocation)
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
