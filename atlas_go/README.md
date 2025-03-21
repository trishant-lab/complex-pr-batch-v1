### Naming convention
- Tables - Only lowercase alphabets with underscores.
- Relation/Bridge Tables - `{table1}{table2}bridge`
- Columns - Only Camelcase alphabets.
- Referenced/Foreign Key column name - `{table}Id`/`{table}Reference`
- UniqueConstraint - `{table}_{column/s}_uq`
- ForeignKeyConstraint - `{table}_{column}_fk`
- Index name - `{table}_{column/s}_idx`

### Creating new migration file
```atlas migrate new {descriptive_name}```

### Set Atlas Token
export ATLAS_TOKEN={...}

### Usage
- To print queries
    ```
    atlas migrate apply --env prod --tx-mode all --dry-run
    ```
- Dry run, execute queires & abort transaction
    ```
    atlas migrate apply --env prod --tx-mode all --dry-run --var dry_run=true
    ```
- To run migrations
    ```
    atlas migrate apply --env prod --tx-mode all
    ```