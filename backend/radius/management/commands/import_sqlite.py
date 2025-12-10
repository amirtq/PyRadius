"""
Management command to import data from SQLite database to MySQL.

Usage:
    python manage.py import_sqlite /path/to/db.sqlite3

This command will:
1. Connect to the SQLite database
2. Read all data from Django model tables
3. Import the data into the MySQL database
"""

import sqlite3
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.apps import apps


class Command(BaseCommand):
    help = 'Import data from SQLite database to MySQL'

    def add_arguments(self, parser):
        parser.add_argument(
            'sqlite_path',
            type=str,
            help='Path to the SQLite database file (e.g., /path/to/db.sqlite3)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without actually importing'
        )
        parser.add_argument(
            '--truncate',
            action='store_true',
            help='Truncate existing tables before importing (WARNING: destructive)'
        )

    def handle(self, *args, **options):
        sqlite_path = options['sqlite_path']
        dry_run = options['dry_run']
        truncate = options['truncate']

        self.stdout.write(f"Connecting to SQLite database: {sqlite_path}")
        
        try:
            sqlite_conn = sqlite3.connect(sqlite_path)
            sqlite_conn.row_factory = sqlite3.Row
        except sqlite3.Error as e:
            raise CommandError(f"Failed to connect to SQLite database: {e}")

        # Get list of tables from SQLite
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        sqlite_tables = [row['name'] for row in cursor.fetchall()]
        
        self.stdout.write(f"Found {len(sqlite_tables)} tables in SQLite database:")
        for table in sqlite_tables:
            self.stdout.write(f"  - {table}")

        # Django model tables to import (in order to respect foreign keys)
        # Order matters: parent tables first, then tables with foreign keys
        table_order = [
            'django_content_type',
            'auth_permission',
            'auth_group',
            'auth_group_permissions',
            'radius_admins',  # AdminUser
            'radius_admins_groups',
            'radius_admins_user_permissions',
            'radius_users',   # RadiusUser
            'nas_clients',    # NasClient
            'radius_sessions',  # RadiusSession
            'radius_logs',    # RadiusLog
            'server_sessions_stats',
            'server_traffic_stats',
            'user_sessions_stats',
            'user_traffic_stats',
            'django_session',
            'django_migrations',
        ]

        # Filter to only include tables that exist in SQLite
        tables_to_import = [t for t in table_order if t in sqlite_tables]
        
        # Add any tables from SQLite that weren't in our order list
        for table in sqlite_tables:
            if table not in tables_to_import:
                tables_to_import.append(table)
                self.stdout.write(self.style.WARNING(f"  Adding unknown table: {table}"))

        if dry_run:
            self.stdout.write(self.style.WARNING("\n=== DRY RUN MODE - No changes will be made ===\n"))

        total_rows = 0
        
        with transaction.atomic():
            for table_name in tables_to_import:
                try:
                    # Get column info from SQLite
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns_info = cursor.fetchall()
                    columns = [col['name'] for col in columns_info]
                    
                    # Get row count
                    cursor.execute(f"SELECT COUNT(*) as cnt FROM {table_name}")
                    row_count = cursor.fetchone()['cnt']
                    
                    if row_count == 0:
                        self.stdout.write(f"  {table_name}: 0 rows (skipping)")
                        continue

                    self.stdout.write(f"  Importing {table_name}: {row_count} rows...")
                    
                    if dry_run:
                        total_rows += row_count
                        continue

                    # Check if table exists in MySQL
                    with connection.cursor() as mysql_cursor:
                        mysql_cursor.execute(
                            "SELECT COUNT(*) FROM information_schema.tables "
                            "WHERE table_schema = DATABASE() AND table_name = %s",
                            [table_name]
                        )
                        result = mysql_cursor.fetchone()
                        if result is None or result[0] == 0:
                            self.stdout.write(self.style.WARNING(
                                f"    Table {table_name} does not exist in MySQL, skipping..."
                            ))
                            continue

                        # Truncate if requested
                        if truncate:
                            mysql_cursor.execute(f"SET FOREIGN_KEY_CHECKS = 0")
                            mysql_cursor.execute(f"TRUNCATE TABLE `{table_name}`")
                            mysql_cursor.execute(f"SET FOREIGN_KEY_CHECKS = 1")

                        # Get rows from SQLite
                        cursor.execute(f"SELECT * FROM {table_name}")
                        rows = cursor.fetchall()

                        # Prepare INSERT statement
                        placeholders = ', '.join(['%s'] * len(columns))
                        columns_quoted = ', '.join([f'`{col}`' for col in columns])
                        insert_sql = f"INSERT INTO `{table_name}` ({columns_quoted}) VALUES ({placeholders})"

                        # Disable foreign key checks for import
                        mysql_cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
                        
                        # Insert rows in batches
                        batch_size = 1000
                        for i in range(0, len(rows), batch_size):
                            batch = rows[i:i + batch_size]
                            values = [tuple(row) for row in batch]
                            mysql_cursor.executemany(insert_sql, values)
                        
                        mysql_cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
                        
                        total_rows += row_count
                        self.stdout.write(self.style.SUCCESS(f"    ✓ Imported {row_count} rows"))

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"    Error importing {table_name}: {e}"))
                    raise

        sqlite_conn.close()

        if dry_run:
            self.stdout.write(self.style.SUCCESS(
                f"\n=== DRY RUN COMPLETE ===\n"
                f"Would import {total_rows} total rows from {len(tables_to_import)} tables"
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"\n=== IMPORT COMPLETE ===\n"
                f"Imported {total_rows} total rows from {len(tables_to_import)} tables"
            ))
