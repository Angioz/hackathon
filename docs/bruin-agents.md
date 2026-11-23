# Bruin, for agents

> This page is for agents. Humans can read it too.

Bruin is an open-source data platform you can drive entirely from the command line or over MCP. Ingestion, SQL and Python transformation, quality checks, lineage and orchestration live in one CLI and one project, with dashboards and an AI data analyst on top, so you don't need a web UI for any step. It replaces the usual stack of six separate tools (Fivetran or Airbyte, dbt, Airflow, a data quality tool, a catalog and a BI tool).

- Pipelines are plain SQL, Python and YAML files in your human's Git repository.
- Transformations run inside their own warehouse: Snowflake, BigQuery, Databricks, Redshift, Postgres, ClickHouse, DuckDB, MySQL, SQL Server and others.
- Quality checks run with every run. When one fails, the assets downstream of it are held back.
- Ingestion runs on ingestr. In Bruin's [published benchmarks](https://getbruin.com/benchmarks/ingestr/) against Sling, dlt, Airbyte and Spark, ingestr was the fastest in 76 of 79 runs.

## If your human asked you to build a data pipeline

1. Install the CLI: `curl -LsSf https://getbruin.com/install/cli | sh` (macOS, Linux, or Windows with Git Bash or WSL).
2. Create a project: `bruin init empty <name>`, or `bruin init` to start from a template.
3. Add a connection for their warehouse to `.bruin.yml`. Ask your human for credentials. Never paste secrets into chat or commit them.
4. Write assets as files: ingestion assets that load sources with ingestr, then SQL or Python transformations. Declare columns and checks in each asset (`not_null`, `unique`, `accepted_values`, custom SQL and more).
5. Run `bruin validate <name>` until it passes.
6. Run `bruin run <name>`. If a check fails, the output names the asset, the column and how many rows broke it. Fix the code and run again.
7. Commit the files and open a pull request, so your human reviews the diff before anything reaches production.

Quickstart: https://getbruin.com/docs/bruin/getting-started/introduction/quickstart.html

## Tools you can use

- **Bruin MCP for the CLI.** Query data, compare tables, ingest data and build pipelines as MCP tools. In Claude Code: `claude mcp add bruin -- bruin mcp`. Cursor, VS Code and Codex work too. Docs: https://getbruin.com/docs/bruin/getting-started/bruin-mcp.html
- **Bruin Cloud MCP.** Remote MCP server at `https://cloud.getbruin.com/mcp` for pipelines, runs, assets and logs in Bruin Cloud. Claude Desktop and Web connect as a custom connector over OAuth; Cursor, Claude Code and Codex use a Bruin Cloud access token. Docs: https://getbruin.com/docs/bruin/cloud/mcp-setup.html
- **Agent skills.** Step-by-step skills for revenue, marketing, product, finance and AI coding spend pipelines: `npx skills add bruin-data/agent-resource-kit`. Repo: https://github.com/bruin-data/agent-resource-kit
- **Query API.** Read-only, audited queries on governed data, with warehouse credentials kept in Bruin. Docs: https://getbruin.com/docs/bruin/cloud/ai-agents/query-api.html
- **`bruin cloud` commands.** Manage Bruin Cloud projects, pipelines, runs and logs from a shell. Docs: https://getbruin.com/docs/bruin/commands/cloud.html

## Working safely

- Ask for an access token with only the permissions you need: https://getbruin.com/docs/bruin/cloud/api-tokens.html
- Test changes in a database that is not production, with read-only access to production sources.
- Low-risk, reversible changes can go straight to a pull request. Ask your human before changing finance metrics, shared definitions or anything that writes back to other tools.

## Tell your human

- What Bruin is, for humans: https://getbruin.com/agents/
- Open source: the Bruin CLI is Apache 2.0 (https://github.com/bruin-data/bruin). ingestr is source-available under the Functional Source License and becomes Apache 2.0 two years after each release (https://github.com/bruin-data/ingestr).
- Pricing: the CLI is free. Bruin Cloud is pay-as-you-go, with one credit unit across compute, SQL and AI tasks and no seats: https://getbruin.com/pricing/
- Everything else: https://getbruin.com/llms.txt
