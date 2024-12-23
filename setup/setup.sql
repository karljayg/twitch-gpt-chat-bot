DROP DATABASE IF EXISTS mathison;
CREATE DATABASE mathison;

USE Mathison;

CREATE TABLE MAJOR_TRAITS (
    id INT AUTO_INCREMENT PRIMARY KEY,
    Name VARCHAR(255),
    Description TEXT
);

CREATE TABLE MOOD_TYPE (
    id INT AUTO_INCREMENT PRIMARY KEY,
    Name VARCHAR(255),
    Description TEXT
);

CREATE TABLE MOODS (
    MOOD_TYPE_id INT,
    Probability INT CHECK (Probability BETWEEN 0 AND 100),
    FOREIGN KEY (MOOD_TYPE_id) REFERENCES MOOD_TYPE(id)
);

CREATE TABLE MOTIVATIONS (
    id INT AUTO_INCREMENT PRIMARY KEY,
    Name VARCHAR(255),
    Description TEXT
);

CREATE TABLE CORE_VALUES (
    Values_id INT AUTO_INCREMENT PRIMARY KEY,
    Name VARCHAR(255),
    Description TEXT
);

CREATE TABLE GOALS (
    id INT AUTO_INCREMENT PRIMARY KEY,
    Name VARCHAR(255),
    Description TEXT,
    Term VARCHAR(255) CHECK (Term IN ('Short', 'Long'))
);

CREATE TABLE PERSONALITY (
    id INT AUTO_INCREMENT PRIMARY KEY,
    MAJOR_TRAITS_id INT,
    MOTIVATIONS_id INT,
    VALUES_id INT,
    GOALS_id INT,
    FOREIGN KEY (MAJOR_TRAITS_id) REFERENCES MAJOR_TRAITS(id),
    FOREIGN KEY (MOTIVATIONS_id) REFERENCES MOTIVATIONS(id),
    FOREIGN KEY (VALUES_id) REFERENCES CORE_VALUES(Values_id),
    FOREIGN KEY (GOALS_id) REFERENCES GOALS(id)
);

CREATE TABLE USER (
    id INT AUTO_INCREMENT PRIMARY KEY,
    LastName VARCHAR(255),
    DisplayName VARCHAR(255),
    TwitchName VARCHAR(255),
    Gender VARCHAR(255),
    Sex VARCHAR(255),
    Dob DATE,
    Race VARCHAR(255),
    Nationality VARCHAR(255),
    Occupation VARCHAR(255),
    State VARCHAR(255),
    Country VARCHAR(255),
    Personality_ID INT,
    FOREIGN KEY (Personality_ID) REFERENCES PERSONALITY(id)
);

CREATE TABLE MEMORY (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ConciseSummary VARCHAR(255),
    Summary TEXT,
    DateTime TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    User_ID INT,
    FOREIGN KEY (User_ID) REFERENCES USER(id)
);

CREATE TABLE Players (
    Id INT NOT NULL AUTO_INCREMENT,
    SC2_UserId VARCHAR(255) NOT NULL UNIQUE,  -- This column is marked as UNIQUE
    PRIMARY KEY(Id)
);

CREATE TABLE Replays (
    UnixTimestamp BIGINT UNIQUE NOT NULL,
    ReplayId INT NOT NULL AUTO_INCREMENT,
    Player1_Id INT,
    Player2_Id INT,
    Player1_PickRace VARCHAR(50),
    Player2_PickRace VARCHAR(50),
    Player1_Race VARCHAR(50),
    Player2_Race VARCHAR(50),
    Player1_Result VARCHAR(50),
    Player2_Result VARCHAR(50),
    Date_Uploaded TIMESTAMP,
    Date_Played TIMESTAMP,  -- This will hold the converted US Eastern time from UnixTimestamp
    Replay_Summary TEXT,
    Player_Comments TEXT,    
    Map VARCHAR(255),
    Region VARCHAR(50),
    GameType VARCHAR(50),
    GameDuration VARCHAR(10),
    PRIMARY KEY (ReplayId),
    FOREIGN KEY (Player1_Id) REFERENCES Players(Id),
    FOREIGN KEY (Player2_Id) REFERENCES Players(Id)
);

