CREATE TABLE IF NOT EXISTS role_hierarchy (
    role_name TEXT PRIMARY KEY,
    point_threshold INTEGER NOT NULL,
    "order" INTEGER NOT NULL
);