"""Recalcula secuencias PostgreSQL del esquema activo (post-migración de datos)."""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Sincroniza secuencias id con MAX(id) de cada tabla del esquema actual'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    quote_ident(n.nspname) || '.' || quote_ident(c.relname) AS fq_table,
                    quote_ident(a.attname) AS column_name,
                    pg_get_serial_sequence(
                        quote_ident(n.nspname) || '.' || quote_ident(c.relname),
                        a.attname
                    ) AS seq_name
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped
                WHERE n.nspname = current_schema()
                  AND c.relkind = 'r'
                  AND pg_get_serial_sequence(
                        quote_ident(n.nspname) || '.' || quote_ident(c.relname),
                        a.attname
                    ) IS NOT NULL
                """
            )
            rows = cursor.fetchall()
            fixed = 0
            for fq_table, column_name, seq_name in rows:
                cursor.execute(
                    f"""
                    SELECT setval(
                        %s::regclass,
                        COALESCE((SELECT MAX({column_name}) FROM {fq_table}), 1),
                        true
                    )
                    """,
                    [seq_name],
                )
                fixed += 1
                self.stdout.write(f'  {seq_name} -> OK')

        self.stdout.write(self.style.SUCCESS(f'Secuencias actualizadas: {fixed}'))
