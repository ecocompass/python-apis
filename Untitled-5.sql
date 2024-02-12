CREATE TABLE "User_statistics" (
  "User_ID" integer,
  "Total_Distance_walked" integer,
  "Totl_Distance_cycled" integer,
  "Cycle_Streak" integer,
  "Walking_streak" integer,
  "Completed_trips" integer
);

CREATE TABLE "users" (
  "User_ID" integer PRIMARY KEY,
  "Name" varchar,
  "Email" varchar UNIQUE NOT NULL,
  "Password" varchar NOT NULL,
  "created_at" timestamp NOT NULL
);

CREATE TABLE "Goals" (
  "Goal_ID" integer PRIMARY KEY,
  "User_ID" integer,
  "Type" varchar,
  "Target" int,
  "Initial_Value" integer,
  "created_at" timestamp NOT NULL,
  "Expiry" timestamp
);

CREATE TABLE "Trips" (
  "Trip_ID" integer PRIMARY KEY,
  "User_ID" integer,
  "Start_time" timestamp,
  "End_time" timestamp,
  "Start_Location" varchar,
  "End_Location" varchar,
  "Route" varchar
);

CREATE TABLE "Saved_Locations" (
  "Location_ID" integer PRIMARY KEY,
  "User_ID" integer,
  "Lat" float,
  "Long" float,
  "Location_name" varchar
);

CREATE TABLE "Prefrences" (
  "Prefernece_ID" integer PRIMARY KEY,
  "User_ID" integer,
  "Public_transport" integer,
  "Bike_weight" integer,
  "Walking_weight" integer,
  "Driving_weight" integer
);

CREATE TABLE "Badge" (
  "Badge_id" integer PRIMARY KEY,
  "User_ID" integer,
  "Type" varchar,
  "Badge_image" varchar,
  "created_at" timestamp
);

ALTER TABLE "Trips" ADD FOREIGN KEY ("User_ID") REFERENCES "users" ("User_ID");

ALTER TABLE "Goals" ADD FOREIGN KEY ("User_ID") REFERENCES "users" ("User_ID");

ALTER TABLE "Prefrences" ADD FOREIGN KEY ("User_ID") REFERENCES "users" ("User_ID");

ALTER TABLE "Saved_Locations" ADD FOREIGN KEY ("User_ID") REFERENCES "users" ("User_ID");

ALTER TABLE "Badge" ADD FOREIGN KEY ("User_ID") REFERENCES "users" ("User_ID");

ALTER TABLE "User_statistics" ADD FOREIGN KEY ("User_ID") REFERENCES "users" ("User_ID");
