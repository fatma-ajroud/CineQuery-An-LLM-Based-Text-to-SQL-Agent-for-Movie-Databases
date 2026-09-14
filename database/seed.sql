-- ======================================================================
-- Movie Text-to-SQL — STARTER seed data (PostgreSQL)
-- Loaded automatically by docker-compose on first boot (02_seed.sql).
--
-- NOTE: This is a small illustrative sample so the pipeline is testable
-- end-to-end. Member 1 (Database & Data Engineering) replaces / extends
-- this with the curated ~50-movie dataset:
--   ~50 movies, 20-30 directors, 80-120 actors, 10-15 genres,
--   50 rating records, plus junction rows.
-- Data is fictional-but-realistic; adjust as needed.
-- ======================================================================

-- Reset (safe to re-run). RESTART IDENTITY resets the SERIAL counters.
TRUNCATE movie_genres, movie_actors, movie_directors, ratings,
         genres, actors, directors, movies RESTART IDENTITY CASCADE;

-- ---------------------------------------------------------------- genres
INSERT INTO genres (name) VALUES
    ('Sci-Fi'), ('Drama'), ('Thriller'), ('Action'),
    ('Animation'), ('Adventure'), ('Crime'), ('Fantasy');

-- ------------------------------------------------------------- directors
INSERT INTO directors (name) VALUES
    ('Christopher Nolan'),   -- 1
    ('Hayao Miyazaki'),      -- 2
    ('Denis Villeneuve'),    -- 3
    ('Bong Joon-ho'),        -- 4
    ('Greta Gerwig');        -- 5

-- ---------------------------------------------------------------- actors
INSERT INTO actors (name) VALUES
    ('Leonardo DiCaprio'),   -- 1
    ('Joseph Gordon-Levitt'),-- 2
    ('Timothée Chalamet'),   -- 3
    ('Zendaya'),             -- 4
    ('Song Kang-ho'),        -- 5
    ('Saoirse Ronan'),       -- 6
    ('Cillian Murphy');      -- 7

-- ---------------------------------------------------------------- movies
INSERT INTO movies (title, release_year, runtime, language) VALUES
    ('Inception',        2010, 148, 'English'),  -- 1
    ('Interstellar',     2014, 169, 'English'),  -- 2
    ('Spirited Away',    2001, 125, 'Japanese'), -- 3
    ('Dune',             2021, 155, 'English'),  -- 4
    ('Parasite',         2019, 132, 'Korean'),   -- 5
    ('Lady Bird',        2017,  94, 'English'),  -- 6
    ('Oppenheimer',      2023, 180, 'English');  -- 7

-- --------------------------------------------------------------- ratings
INSERT INTO ratings (movie_id, rating) VALUES
    (1, 8.8), (2, 8.6), (3, 8.6), (4, 8.0), (5, 8.5), (6, 7.4), (7, 8.4);

-- ------------------------------------------------------- movie_directors
INSERT INTO movie_directors (movie_id, director_id) VALUES
    (1, 1), (2, 1), (7, 1),   -- Nolan: Inception, Interstellar, Oppenheimer
    (3, 2),                    -- Miyazaki: Spirited Away
    (4, 3),                    -- Villeneuve: Dune
    (5, 4),                    -- Bong Joon-ho: Parasite
    (6, 5);                    -- Gerwig: Lady Bird

-- ---------------------------------------------------------- movie_actors
INSERT INTO movie_actors (movie_id, actor_id, role) VALUES
    (1, 1, 'Dom Cobb'),
    (1, 2, 'Arthur'),
    (4, 3, 'Paul Atreides'),
    (4, 4, 'Chani'),
    (5, 5, 'Kim Ki-taek'),
    (6, 6, 'Christine "Lady Bird" McPherson'),
    (7, 7, 'J. Robert Oppenheimer');

-- ---------------------------------------------------------- movie_genres
INSERT INTO movie_genres (movie_id, genre_id) VALUES
    (1, 1), (1, 3),   -- Inception: Sci-Fi, Thriller
    (2, 1), (2, 2),   -- Interstellar: Sci-Fi, Drama
    (3, 5), (3, 6),   -- Spirited Away: Animation, Adventure
    (4, 1), (4, 6),   -- Dune: Sci-Fi, Adventure
    (5, 2), (5, 3),   -- Parasite: Drama, Thriller
    (6, 2),           -- Lady Bird: Drama
    (7, 2);           -- Oppenheimer: Drama
