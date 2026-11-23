# Hack: the launch film that writes itself

**Every merge to `main` becomes a 75-105 second animated launch film, written by four AI agents who argue about it.**

Multiplayer AI Hackathon, Track 1 (Agent Animated Film). No human in the loop at runtime.

```
git merge -> Bruin pipeline (4 agents, 4 rounds, memory, decision log, quality checks)
          -> story_bible.json + decision_log.json + rewritten_script.json
          -> 4 voices + animated Remotion film with an on-screen Decision Log
          -> auto-publisher receipt
```

## The cast

| Agent | Role | Wants | Secret goal |
|---|---|---|---|
| **Dev** | Pragmatic Staff Engineer | Technical accuracy, zero hype | Never claim what the code doesn't do |
| **Growth** | Hype Marketing Director | A viral hook, big stakes | Biggest possible claim in the first line |
| **Critic** | Skeptical user and chaos QA | Break it, inject the plot twist | Prove an edge case on camera |
| **Director** | Showrunner and arbiter | Pacing, visuals, a decisive ending | Never repeat last run's ending |

## How a film gets decided

1. **Pitch:** each agent proposes how to frame the merged feature and backs or attacks a rival.
2. **Twist:** the Critic picks the mid-film plot twist (twists used in recent runs are banned by memory); the others support or oppose it.
3. **Vote:** all four vote on the ending (last run's ending is banned).
4. **Arbitration:** the Director decides, weighting each vote by how much he trusts that agent (trust is stored in memory and changes every run).

Every decision is written to the `decision_log` table with **what** was decided and **why**. After the run each agent writes a reflection and updated alliance weights to `agent_memory`, which it reads at the start of the next run.

## Hackathon rules: where to check each one

| Requirement | How we meet it | Evidence |
|---|---|---|
| Bruin (mandatory sponsor) | 5-asset Bruin pipeline (4 Python + 1 SQL) on DuckDB; `bruin validate` and `bruin run` pass (5/5 assets, 13/13 quality checks). Synced to Bruin Cloud, no validation errors. | [`bruin-pipeline/`](bruin-pipeline/) |
| At least 3 agents with distinct roles, goals, personalities | 4 agents with opposing goals and secret goals | [`bruin-pipeline/lib/cast.py`](bruin-pipeline/lib/cast.py), DuckDB `agents` |
| Agents decide story, twist and ending | 4-round writers' room; twist and ending are agent choices | [`bruin-pipeline/lib/room.py`](bruin-pipeline/lib/room.py) |
| Decision log: what and why | `decision_log` table + `decision_log.json`, with Bruin checks for non-empty `reasoning_why`, a plot twist, and at least 3 agents | [`assets/story_quality_checks.sql`](bruin-pipeline/assets/story_quality_checks.sql), [sample](bruin-pipeline/contracts/sample/decision_log.json) |
| Different runs, different outcomes | Memory bans recent twists and the last ending; trust weights shift the vote | Run comparison below |
| Agent memory and adaptive behaviour (bonus) | `agent_memory` rows per run: reflection, alliance weights, twist and ending history | DuckDB `agent_memory` |
| Visual characters with movement and interaction | Every scripted line carries a stage move, a look-at target, a prop interaction and a pose | [sample story bible](bruin-pipeline/contracts/sample/story_bible.json); renderer: *pending (Lane A)* |
| 1-3 minute film | Script is checked for 60-180 s (current runs about 77 s at 2.6 words/sec) | *final MP4 pending* |
| Voice (bonus) | 4 distinct voices, 2 male and 2 female | *pending (Lane A)* |
| Zero human in the loop | One command or a signed GitHub webhook runs everything | [`launch/`](launch/) |
| Demo video with AdaL | | *pending* |

## Run it

Requirements: Python 3.11+, [Bruin CLI](https://getbruin.com/docs/bruin/getting-started/introduction/installation.html), `pip install duckdb==1.5.2 anthropic`.

```bash
# Optional: real Claude agents. Without a key, a template stand-in brain is used (marked "offline" in the log).
echo "ANTHROPIC_API_KEY=..." >> .env.local      # git-ignored

bruin validate bruin-pipeline

# One command, zero prompts: commit -> Bruin -> (render) -> publish receipt
py launch/run_autonomous_launch.py --commit HEAD --fresh --label run_1
py launch/run_autonomous_launch.py --commit HEAD --label run_2

# Or listen for merges (GitHub webhook, HMAC-verified)
GITHUB_WEBHOOK_SECRET=... py launch/webhook_server.py --port 8787
```

Outputs land in `output/runs/<run_id>/` (also mirrored to `output/latest/`): `feature_payload.json`, `story_bible.json`, `decision_log.json`, `rewritten_script.json`, `publish_receipt.json`, `run_manifest.json`.

The publisher defaults to **dry run** and only posts to an allow-listed channel when explicitly switched to live.

## Run comparison

*Pending: two runs with the real Claude agents on the same commit.*
