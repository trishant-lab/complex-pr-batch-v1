SELECT schema_name as tenant
FROM information_schema.schemata
WHERE schema_name NOT IN (
      'information_schema',
      'pg_catalog',
      'public',
      'pg_toast',
      '_timescaledb_debug',
      '_timescaledb_cache',
      '_timescaledb_catalog',
      '_timescaledb_functions',
      '_timescaledb_internal',
      '_timescaledb_config',
      'timescaledb_information',
      'timescaledb_experimental',
      'pganalyze'
)