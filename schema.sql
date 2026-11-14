CREATE TABLE IF NOT EXISTS students (
    id         SERIAL PRIMARY KEY,
    student_no VARCHAR(20)  UNIQUE NOT NULL,
    first_name VARCHAR(50)  NOT NULL,
    last_name  VARCHAR(50)  NOT NULL,
    course     VARCHAR(100) NOT NULL,
    year_level INTEGER      NOT NULL CHECK (year_level BETWEEN 1 AND 6),
    email      VARCHAR(100),
    created_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
