INSERT INTO system (id, name, display, database, is_legacy, mnemonic, search_identifiers)
VALUES (
    {{ system_id }}::uuid,
    {{ name }},
    {{ display }},
    {{ database }},
    true,
    {{ mnemonic }},
    {{ search_identifiers }}::jsonb
)
ON CONFLICT (name) DO UPDATE SET
    display = EXCLUDED.display,
    database = EXCLUDED.database,
    mnemonic = EXCLUDED.mnemonic,
    search_identifiers = EXCLUDED.search_identifiers
RETURNING id, name;
