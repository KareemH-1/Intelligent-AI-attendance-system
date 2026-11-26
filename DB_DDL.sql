
IF DB_ID('IntelligentAttendanceDB') IS NULL
BEGIN
    CREATE DATABASE IntelligentAttendanceDB;
END;
GO

USE IntelligentAttendanceDB;
GO


CREATE TABLE People
(
    person_id INT IDENTITY(1,1) PRIMARY KEY,
    university_id VARCHAR(30) NOT NULL UNIQUE,
    full_name NVARCHAR(150) NOT NULL,
    email VARCHAR(150) NULL,
    created_at DATETIME2 NOT NULL DEFAULT SYSDATETIME()
);

CREATE UNIQUE INDEX UX_People_Email
ON People(email)
WHERE email IS NOT NULL;



CREATE TABLE Students
(
    student_id INT IDENTITY(1,1) PRIMARY KEY,
    person_id INT NOT NULL UNIQUE,
    department VARCHAR(100) NOT NULL,
    academic_year TINYINT NOT NULL,

    CONSTRAINT FK_Students_People
        FOREIGN KEY (person_id)
        REFERENCES People(person_id),

    CONSTRAINT CK_Students_AcademicYear
        CHECK (academic_year BETWEEN 1 AND 7)
);



CREATE TABLE Instructors
(
    instructor_id INT IDENTITY(1,1) PRIMARY KEY,
    person_id INT NOT NULL UNIQUE,
    department VARCHAR(100) NOT NULL,
    instructor_type VARCHAR(20) NOT NULL,

    CONSTRAINT FK_Instructors_People
        FOREIGN KEY (person_id)
        REFERENCES People(person_id),

    CONSTRAINT CK_Instructors_Type
        CHECK (instructor_type IN ('Lecturer', 'TA'))
);


-- =============================================
-- Stores vector embeddings for all people that require the ai recognition.
-- one person embedding is around 512 bytes, and one person has 5 embeddings for now
-- =============================================

CREATE TABLE FaceEmbeddings
(
    embedding_id INT IDENTITY(1,1) PRIMARY KEY,
    person_id INT NOT NULL,
    embedding VARBINARY(MAX) NOT NULL,
    embedding_dimension SMALLINT NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    is_active BIT NOT NULL DEFAULT 1,
    created_at DATETIME2 NOT NULL DEFAULT SYSDATETIME(),

    CONSTRAINT FK_FaceEmbeddings_People
        FOREIGN KEY (person_id)
        REFERENCES People(person_id),

    CONSTRAINT CK_FaceEmbeddings_Dimension
        CHECK (embedding_dimension > 0)
);

USE IntelligentAttendanceDB;
GO

ALTER TABLE FaceEmbeddings
ADD
    pose_label VARCHAR(10) NULL,
    registration_id UNIQUEIDENTIFIER NULL;
GO

ALTER TABLE FaceEmbeddings
ADD CONSTRAINT CK_FaceEmbeddings_Pose
CHECK (
    pose_label IS NULL
    OR pose_label IN (
        'FRONT',
        'LEFT',
        'RIGHT',
        'UP',
        'DOWN'
    )
);
GO

CREATE UNIQUE INDEX UX_FaceEmbeddings_ActivePersonPose
ON FaceEmbeddings(person_id, pose_label)
WHERE is_active = 1
  AND pose_label IS NOT NULL;
GO

CREATE UNIQUE INDEX UX_FaceEmbeddings_RegistrationPose
ON FaceEmbeddings(registration_id, pose_label)
WHERE registration_id IS NOT NULL
  AND pose_label IS NOT NULL;
GO

CREATE INDEX IX_FaceEmbeddings_Person
ON FaceEmbeddings(person_id, is_active);



CREATE TABLE Semesters
(
    semester_id INT IDENTITY(1,1) PRIMARY KEY,
    semester_name VARCHAR(50) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    is_active BIT NOT NULL DEFAULT 0,

    CONSTRAINT CK_Semesters_Dates
        CHECK (end_date >= start_date)
);

CREATE UNIQUE INDEX UX_Semesters_OneActive
ON Semesters(is_active)
WHERE is_active = 1;


CREATE TABLE Courses
(
    course_id INT IDENTITY(1,1) PRIMARY KEY,
    course_code VARCHAR(20) NOT NULL UNIQUE,
    course_name NVARCHAR(150) NOT NULL,
    credit_hours TINYINT NOT NULL,

    CONSTRAINT CK_Courses_CreditHours
        CHECK (credit_hours > 0)
);


-- a course offered in a specific semester.
CREATE TABLE CourseOfferings
(
    offering_id INT IDENTITY(1,1) PRIMARY KEY,
    course_id INT NOT NULL,
    semester_id INT NOT NULL,
    section_code VARCHAR(20) NOT NULL,

    CONSTRAINT FK_CourseOfferings_Courses
        FOREIGN KEY (course_id)
        REFERENCES Courses(course_id),

    CONSTRAINT FK_CourseOfferings_Semesters
        FOREIGN KEY (semester_id)
        REFERENCES Semesters(semester_id),

    CONSTRAINT UQ_CourseOfferings
        UNIQUE (course_id, semester_id, section_code)
);


CREATE TABLE Enrollments
(
    enrollment_id INT IDENTITY(1,1) PRIMARY KEY,
    student_id INT NOT NULL,
    offering_id INT NOT NULL,
    enrollment_date DATE NOT NULL DEFAULT CAST(GETDATE() AS DATE),

    CONSTRAINT FK_Enrollments_Students
        FOREIGN KEY (student_id)
        REFERENCES Students(student_id),

    CONSTRAINT FK_Enrollments_CourseOfferings
        FOREIGN KEY (offering_id)
        REFERENCES CourseOfferings(offering_id),

    CONSTRAINT UQ_Enrollments
        UNIQUE (student_id, offering_id)
);

CREATE INDEX IX_Enrollments_Offering
ON Enrollments(offering_id);


CREATE TABLE LectureHalls
(
    hall_id INT IDENTITY(1,1) PRIMARY KEY,
    hall_name VARCHAR(50) NOT NULL,
    building VARCHAR(100) NOT NULL,
    capacity INT NOT NULL,

    CONSTRAINT UQ_LectureHalls
        UNIQUE (hall_name, building),

    CONSTRAINT CK_LectureHalls_Capacity
        CHECK (capacity > 0)
);


CREATE TABLE HallTerminals
(
    terminal_id INT IDENTITY(1,1) PRIMARY KEY,
    hall_id INT NOT NULL,
    terminal_code VARCHAR(50) NOT NULL UNIQUE,
    device_name NVARCHAR(100) NOT NULL,
    device_key_hash VARCHAR(255) NOT NULL,
    is_active BIT NOT NULL DEFAULT 1,
    last_seen DATETIME2 NULL,
    created_at DATETIME2 NOT NULL DEFAULT SYSDATETIME(),

    CONSTRAINT FK_HallTerminals_LectureHalls
        FOREIGN KEY (hall_id)
        REFERENCES LectureHalls(hall_id)
);

CREATE INDEX IX_HallTerminals_Hall
ON HallTerminals(hall_id);



-- roles for authentication/authorization
CREATE TABLE Roles
(
    role_id INT IDENTITY(1,1) PRIMARY KEY,
    role_name VARCHAR(30) NOT NULL UNIQUE,
    description NVARCHAR(200) NULL
);


-- Initial application roles
INSERT INTO Roles (role_name, description)
VALUES
('Admin', 'System administrator'),
('Lecturer', 'University lecturer'),
('TA', 'Teaching assistant'),
('Student', 'University student');


CREATE TABLE UserAccounts
(
    account_id INT IDENTITY(1,1) PRIMARY KEY,
    person_id INT NOT NULL UNIQUE,
    role_id INT NOT NULL,
    username VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    is_active BIT NOT NULL DEFAULT 1,
    must_change_password BIT NOT NULL
        CONSTRAINT DF_UserAccounts_must_change_password DEFAULT 0,
    created_at DATETIME2 NOT NULL DEFAULT SYSDATETIME(),

    CONSTRAINT FK_UserAccounts_People
        FOREIGN KEY (person_id)
        REFERENCES People(person_id),

    CONSTRAINT FK_UserAccounts_Roles
        FOREIGN KEY (role_id)
        REFERENCES Roles(role_id)
);



CREATE TABLE TimetableSlots
(
    slot_id INT IDENTITY(1,1) PRIMARY KEY,
    offering_id INT NOT NULL,
    hall_id INT NOT NULL,

    primary_instructor_id INT NOT NULL,
    ta_instructor_id INT NULL,

    day_of_week TINYINT NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,

    is_active BIT NOT NULL DEFAULT 1,

    CONSTRAINT FK_TimetableSlots_CourseOfferings
        FOREIGN KEY (offering_id)
        REFERENCES CourseOfferings(offering_id),

    CONSTRAINT FK_TimetableSlots_LectureHalls
        FOREIGN KEY (hall_id)
        REFERENCES LectureHalls(hall_id),

    CONSTRAINT FK_TimetableSlots_PrimaryInstructor
        FOREIGN KEY (primary_instructor_id)
        REFERENCES Instructors(instructor_id),

    CONSTRAINT FK_TimetableSlots_TA
        FOREIGN KEY (ta_instructor_id)
        REFERENCES Instructors(instructor_id),

    CONSTRAINT CK_TimetableSlots_Day
        CHECK (day_of_week BETWEEN 1 AND 7),

    CONSTRAINT CK_TimetableSlots_Times
        CHECK (end_time > start_time),

    CONSTRAINT CK_TimetableSlots_Instructors
        CHECK (
            ta_instructor_id IS NULL
            OR ta_instructor_id <> primary_instructor_id
        )
);

CREATE INDEX IX_TimetableSlots_HallDay
ON TimetableSlots(hall_id, day_of_week, is_active);

CREATE INDEX IX_TimetableSlots_Instructor
ON TimetableSlots(primary_instructor_id, day_of_week);



CREATE TABLE LectureSessions
(
    session_id INT IDENTITY(1,1) PRIMARY KEY,

    slot_id INT NOT NULL,

    primary_instructor_id INT NOT NULL,
    ta_instructor_id INT NULL,

    session_date DATE NOT NULL,

    scheduled_start TIME NOT NULL,
    scheduled_end TIME NOT NULL,

    actual_start DATETIME2 NULL,
    actual_end DATETIME2 NULL,

    session_status VARCHAR(20) NOT NULL DEFAULT 'Scheduled',

    created_at DATETIME2 NOT NULL DEFAULT SYSDATETIME(),

    CONSTRAINT FK_LectureSessions_TimetableSlots
        FOREIGN KEY (slot_id)
        REFERENCES TimetableSlots(slot_id),

    CONSTRAINT FK_LectureSessions_PrimaryInstructor
        FOREIGN KEY (primary_instructor_id)
        REFERENCES Instructors(instructor_id),

    CONSTRAINT FK_LectureSessions_TA
        FOREIGN KEY (ta_instructor_id)
        REFERENCES Instructors(instructor_id),

    CONSTRAINT UQ_LectureSessions_SlotDate
        UNIQUE (slot_id, session_date),

    CONSTRAINT CK_LectureSessions_Status
        CHECK (
            session_status IN (
                'Scheduled',
                'Active',
                'Completed',
                'Cancelled'
            )
        ),

    CONSTRAINT CK_LectureSessions_Times
        CHECK (scheduled_end > scheduled_start),

    CONSTRAINT CK_LectureSessions_ActualTimes
        CHECK (
            actual_end IS NULL
            OR (
                actual_start IS NOT NULL
                AND actual_end >= actual_start
            )
        )
);

CREATE INDEX IX_LectureSessions_Date
ON LectureSessions(session_date, session_status);

CREATE INDEX IX_LectureSessions_Instructor
ON LectureSessions(primary_instructor_id, session_date);

CREATE INDEX IX_LectureSessions_Slot
ON LectureSessions(slot_id, session_date);



CREATE TABLE StudentAttendance
(
    attendance_id INT IDENTITY(1,1) PRIMARY KEY,

    session_id INT NOT NULL,
    student_id INT NOT NULL,

    check_in_time DATETIME2 NOT NULL DEFAULT SYSDATETIME(),

    attendance_status VARCHAR(20) NOT NULL DEFAULT 'Present',

    verification_method VARCHAR(30) NOT NULL DEFAULT 'FaceRecognition',

    CONSTRAINT FK_StudentAttendance_LectureSessions
        FOREIGN KEY (session_id)
        REFERENCES LectureSessions(session_id),

    CONSTRAINT FK_StudentAttendance_Students
        FOREIGN KEY (student_id)
        REFERENCES Students(student_id),

    CONSTRAINT UQ_StudentAttendance
        UNIQUE (session_id, student_id),

    CONSTRAINT CK_StudentAttendance_Status
        CHECK (attendance_status IN ('Present', 'Late')),

    CONSTRAINT CK_StudentAttendance_Method
        CHECK (
            verification_method IN (
                'FaceRecognition',
                'Manual'
            )
        )
);

CREATE INDEX IX_StudentAttendance_Student
ON StudentAttendance(student_id, check_in_time);

CREATE INDEX IX_StudentAttendance_Session
ON StudentAttendance(session_id);


CREATE TABLE InstructorOfferings
(
    instructor_offering_id INT IDENTITY(1,1) PRIMARY KEY,
    instructor_id INT NOT NULL,
    offering_id INT NOT NULL,

    instructor_role VARCHAR(20) NOT NULL,

    CONSTRAINT FK_InstructorOfferings_Instructors
        FOREIGN KEY (instructor_id)
        REFERENCES Instructors(instructor_id),

    CONSTRAINT FK_InstructorOfferings_Offerings
        FOREIGN KEY (offering_id)
        REFERENCES CourseOfferings(offering_id),

    CONSTRAINT CK_InstructorOfferings_Role
        CHECK (instructor_role IN ('Lecturer', 'TA')),

    CONSTRAINT UQ_InstructorOfferings
        UNIQUE (instructor_id, offering_id)
);