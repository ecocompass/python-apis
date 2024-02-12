CREATE TABLE "user_statistics" (
  "user_id" integer,
  "Total_Distance_walked" integer,
  "Totl_Distance_cycled" integer,
  "Cycle_Streak" integer,
  "Walking_streak" integer,
  "Completed_trips" integer
);
CREATE TABLE "users" (
  "user_id" SERIAL PRIMARY KEY,
  "first_name" varchar,
  "last_name" varchar,
  "email" varchar UNIQUE NOT NULL,
  "password" varchar NOT NULL,
  "created_at" timestamp NOT NULL
);


CREATE TABLE "goals" (
  "goal_ID" integer PRIMARY KEY,
  "user_ID" integer,
  "type" varchar,
  "target" int,
  "initial_Value" integer,
  "created_at" timestamp NOT NULL,
  "expiry" timestamp
);

CREATE TABLE "trips" (
  "trip_id" integer PRIMARY KEY,
  "user_id" integer,
  "start_time" timestamp,
  "end_time" timestamp,
  "start_location" varchar,
  "end_location" varchar,
  "route" varchar
);

CREATE TABLE "saved_locations" (
  "location_id" integer PRIMARY KEY,
  "user_id" integer,
  "lat" float,
  "long" float,
  "location_name" varchar
);

CREATE TABLE "prefrences" (
  "prefernece_ID" integer PRIMARY KEY,
  "user_id" integer,
  "public_transport" integer,
  "bike_weight" integer,
  "walking_weight" integer,
  "driving_weight" integer
);

CREATE TABLE "badge" (
  "badge_id" integer PRIMARY KEY,
  "user_id" integer,
  "type" varchar,
  "badge_image" varchar,
  "created_at" timestamp
);

ALTER TABLE "prefrences" ADD FOREIGN KEY ("user_id") REFERENCES "users" ("user_id");

ALTER TABLE "user_statistics" ADD FOREIGN KEY ("user_id") REFERENCES "users" ("user_id");

ALTER TABLE "goals" ADD FOREIGN KEY ("user_ID") REFERENCES "users" ("user_id");

ALTER TABLE "trips" ADD FOREIGN KEY ("user_id") REFERENCES "users" ("user_id");

ALTER TABLE "saved_locations" ADD FOREIGN KEY ("user_id") REFERENCES "users" ("user_id");

ALTER TABLE "badge" ADD FOREIGN KEY ("user_id") REFERENCES "users" ("user_id");
