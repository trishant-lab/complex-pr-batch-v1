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
    vars = {
        schema = local.config.schema
    }
}

env "prod" {
    url = "${local.config.url}?sslmode=disable&options=-c%20search_path=${local.config.schema},public"
    migration {
        dir = data.template_dir.migrations.url
        revisions_schema = local.config.schema
    }
}
