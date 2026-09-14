-- ======================================================================
-- Movie Text-to-SQL — relational schema (PostgreSQL)
-- Small but relationally rich: ~50 movies spread across normalized tables.
-- Loaded automatically by docker-compose on first boot (01_schema.sql).
-- ======================================================================

-- Idempotent: drop in dependency order so the file can be re-run.
DROP TABLE IF EXISTS movie_genres    CASCADE;
DROP TABLE IF EXISTS movie_actors    CASCADE;
DROP TABLE IF EXISTS movie_directors CASCADE;
DROP TABLE IF EXISTS ratings         CASCADE;
DROP TABLE IF EXISTS genres          CASCADE;
DROP TABLE IF EXISTS actors          CASCADE;
DROP TABLE IF EXISTS directors       CASCADE;
DROP TABLE IF EXISTS movies          CASCADE;

-- ---------------------------------------------------------------- entities
CREATE TABLE movies (
    movie_id     SERIAL PRIMARY KEY,
    title        VARCHAR(255) NOT NULL,
    release_year INT,
    runtime      INT,                 -- minutes
    language     VARCHAR(50)
);

CREATE TABLE directors (
    director_id SERIAL PRIMARY KEY,
    name        VARCHAR(255) NOT NULL
);

CREATE TABLE actors (
    actor_id SERIAL PRIMARY KEY,
    name     VARCHAR(255) NOT NULL
);

CREATE TABLE genres (
    genre_id SERIAL PRIMARY KEY,
    name     VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE ratings (
    rating_id SERIAL PRIMARY KEY,
    movie_id  INT NOT NULL REFERENCES movies(movie_id) ON DELETE CASCADE,
    rating    DECIMAL(3, 1) CHECK (rating >= 0 AND rating <= 10)
);

-- ------------------------------------------------------------ junction tables
CREATE TABLE movie_directors (
    movie_id    INT NOT NULL REFERENCES movies(movie_id)    ON DELETE CASCADE,
    director_id INT NOT NULL REFERENCES directors(director_id) ON DELETE CASCADE,
    PRIMARY KEY (movie_id, director_id)
);

CREATE TABLE movie_actors (
    movie_id INT NOT NULL REFERENCES movies(movie_id) ON DELETE CASCADE,
    actor_id INT NOT NULL REFERENCES actors(actor_id) ON DELETE CASCADE,
    role     VARCHAR(255),
    PRIMARY KEY (movie_id, actor_id)
);

CREATE TABLE movie_genres (
    movie_id INT NOT NULL REFERENCES movies(movie_id) ON DELETE CASCADE,
    genre_id INT NOT NULL REFERENCES genres(genre_id) ON DELETE CASCADE,
    PRIMARY KEY (movie_id, genre_id)
);

-- ------------------------------------------------------------------- indexes
-- Helpful for the JOIN / GROUP BY heavy questions in the evaluation set.
CREATE INDEX idx_ratings_movie          ON ratings(movie_id);
CREATE INDEX idx_movie_directors_dir    ON movie_directors(director_id);
CREATE INDEX idx_movie_actors_actor     ON movie_actors(actor_id);
CREATE INDEX idx_movie_genres_genre     ON movie_genres(genre_id);
CREATE INDEX idx_movies_release_year    ON movies(release_year);
