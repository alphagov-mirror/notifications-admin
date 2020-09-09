import json
import os
import sqlite3
from pathlib import Path


class BroadcastAreasRepository(object):
    def __init__(self):
        self.database = Path(__file__).resolve().parent / 'broadcast-areas.sqlite3'

    def conn(self):
        return sqlite3.connect(str(self.database))

    def delete_db(self):
        os.remove(str(self.database))

    def create_tables(self):
        with self.conn() as conn:
            conn.execute("""
            CREATE TABLE broadcast_area_libraries (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                name_singular TEXT NOT NULL,
                is_group BOOLEAN NOT NULL
            )""")

            conn.execute("""
            CREATE TABLE broadcast_area_library_groups (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                broadcast_area_library_id TEXT NOT NULL
            )""")

            conn.execute("""
            CREATE TABLE broadcast_areas (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                broadcast_area_library_id TEXT NOT NULL,
                broadcast_area_library_group_id TEXT,

                FOREIGN KEY (broadcast_area_library_id)
                    REFERENCES broadcast_area_libraries(id),

                FOREIGN KEY (broadcast_area_library_group_id)
                    REFERENCES broadcast_area_library_groups(id)
            )""")

            conn.execute("""
            CREATE TABLE broadcast_area_polygons (
                id TEXT PRIMARY KEY,
                polygons TEXT NOT NULL,
                simple_polygons TEXT NOT NULL
            )""")

            conn.execute("""
            CREATE INDEX broadcast_areas_broadcast_area_library_id
            ON broadcast_areas (broadcast_area_library_id);
            """)

            conn.execute("""
            CREATE INDEX broadcast_areas_broadcast_area_library_group_id
            ON broadcast_areas (broadcast_area_library_group_id);
            """)

    def delete_library_data(self):
        # delete everything except broadcast_area_polygons
        with self.conn() as conn:
            conn.execute('DELETE FROM broadcast_area_libraries;')
            conn.execute('DELETE FROM broadcast_area_library_groups;')
            conn.execute('DELETE FROM broadcast_areas;')

    def insert_broadcast_area_library(self, id, *, name, name_singular, is_group):

        q = """
        INSERT INTO broadcast_area_libraries (id, name, name_singular, is_group)
        VALUES (?, ?, ?, ?)
        """

        with self.conn() as conn:
            conn.execute(q, (id, name, name_singular, is_group))

    def insert_broadcast_areas(self, areas, keep_old_features):

        areas_q = """
        INSERT INTO broadcast_areas (
            id, name,
            broadcast_area_library_id, broadcast_area_library_group_id
        )
        VALUES (?, ?, ?, ?)
        """

        features_q = """
        INSERT INTO broadcast_area_polygons (
            id,
            polygons, simple_polygons
        )
        VALUES (?, ?, ?)
        """

        with self.conn() as conn:
            for id, name, area_id, group, polygons, simple_polygons in areas:
                conn.execute(areas_q, (
                    id, name, area_id, group,
                ))
                if not keep_old_features:
                    conn.execute(features_q, (
                        id, json.dumps(polygons), json.dumps(simple_polygons),
                    ))

    def query(self, sql, *args):
        with self.conn() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (*args,))
            return cursor.fetchall()

    def get_libraries(self):
        q = "SELECT id, name, name_singular, is_group FROM broadcast_area_libraries"
        results = self.query(q)
        libraries = [(row[0], row[1], row[2], row[3]) for row in results]
        return sorted(libraries)

    def get_library_description(self, library_id):
        q = """
        WITH
        areas AS (
            SELECT * FROM broadcast_areas
            WHERE broadcast_area_library_id = ?
            AND broadcast_area_library_group_id IS NULL
        ),
        area_count AS (SELECT COUNT(*) AS c FROM areas),
        subset_area_count AS (SELECT c - 4 FROM area_count),
        description_area_names  AS (SELECT name FROM areas ORDER BY name ASC LIMIT 3),
        description_areas_joined AS (
            SELECT GROUP_CONCAT(name, ", ") FROM description_area_names
        )
        SELECT
        CASE (SELECT * FROM subset_area_count)
        WHEN 0 THEN
            (SELECT * FROM description_areas_joined)
            || ", and "
            || (SELECT name from areas ORDER BY name DESC limit 1)
        ELSE
            (SELECT * FROM description_areas_joined)
            || ", and "
            || (SELECT * FROM subset_area_count)
            || " more…"
        END
        """
        description = self.query(q, library_id)[0][0]
        return description

    def get_areas(self, area_ids):
        q = """
        SELECT id, name
        FROM broadcast_areas
        WHERE id IN ({})
        """.format(("?," * len(area_ids))[:-1])

        results = self.query(q, *area_ids)

        areas = [
            (row[0], row[1])
            for row in results
        ]

        return areas

    def get_all_areas_for_library(self, library_id):
        # only interested in areas with children - local authorities, counties, unitary authorities. not wards.
        q = """
        SELECT id, name
        FROM broadcast_areas
        JOIN (
            SELECT DISTINCT broadcast_area_library_group_id
            FROM broadcast_areas
            WHERE broadcast_area_library_group_id IS NOT NULL
        ) AS parent_broadcast_areas ON parent_broadcast_areas.broadcast_area_library_group_id = broadcast_areas.id
        WHERE broadcast_area_library_id = ?
        """

        results = self.query(q, library_id)

        return [
            (row[0], row[1])
            for row in results
        ]

    def get_all_areas_for_group(self, group_id):
        q = """
        SELECT id, name
        FROM broadcast_areas
        WHERE broadcast_area_library_group_id = ?
        """

        results = self.query(q, group_id)

        areas = [
            (row[0], row[1])
            for row in results
        ]

        return areas

    def get_all_groups_for_library(self, library_id):
        q = """
        SELECT id, name
        FROM broadcast_areas
        WHERE broadcast_area_library_group_id = NULL
        AND broadcast_area_library_id = ?
        """

        results = self.query(q, library_id)

        areas = [
            (row[0], row[1])
            for row in results
        ]

        return areas

    def get_polygons_for_area(self, area_id):
        q = """
        SELECT polygons
        FROM broadcast_area_polygons
        WHERE id = ?
        """

        results = self.query(q, area_id)

        return json.loads(results[0][0])

    def get_simple_polygons_for_area(self, area_id):
        q = """
        SELECT simple_polygons
        FROM broadcast_area_polygons
        WHERE id = ?
        """

        results = self.query(q, area_id)

        return json.loads(results[0][0])
