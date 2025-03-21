data "external" "config" {
    program = [
    "python3",
    "atlas_go/setup.py"
    ]
}

locals {
    config = jsondecode(data.external.config)
}

variable "dry_run" {
    type = bool
    default = false
}

data "template_dir" "migrations" {
    path = "atlas_go/migrations"
}

env "prod" {
    url = "${local.config.url}?sslmode=disable"
    migration {
        dir = data.template_dir.migrations.url
        revisions_schema = local.config.schema
    }
}

hook "sql" "set_schema" {
    transaction {
        after_begin = [
			"CREATE SCHEMA IF NOT EXISTS \"${local.config.schema}\";",
            "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\" schema public;",
			"CREATE EXTENSION IF NOT EXISTS \"pg_uuidv7\" schema public;",
            "SET SEARCH_PATH TO \"${local.config.schema}\", public;"
        ]
        # abort if dry_run is true, atlas dry-run just prints the sql statements
        before_commit = [
            "${var.dry_run ? "ABORT;" : "SELECT 1;"}",
        ]
    }
}