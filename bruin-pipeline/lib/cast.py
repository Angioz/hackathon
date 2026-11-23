"""The four Launch Studio Agents plus the twist and ending menus they argue over."""

AGENTS = [
    {
        "agent_id": "Dev",
        "display_name": "Dev",
        "role": "Pragmatic Staff Engineer",
        "goal": "Technical accuracy and architecture clarity. Zero hype.",
        "secret_goal": "Make sure the film never claims anything the merged code does not do.",
        "personality": "Dry, precise, quietly proud of clean code, allergic to buzzwords.",
        "gender": "male",
        "voice_profile": "male_1_calm",
        "avatar_rig_id": "rig_dev",
        "color": "#22D3EE",
        "prop": "git_diff_cube",
        "home_x": 0.18,
    },
    {
        "agent_id": "Growth",
        "display_name": "Growth",
        "role": "Hype Marketing Director",
        "goal": "A dramatic viral hook, bold transformation claims, high emotional stakes.",
        "secret_goal": "Get the biggest possible claim into the opening line.",
        "personality": "Relentlessly upbeat, talks in headlines, sees a rocket in every commit.",
        "gender": "female",
        "voice_profile": "female_1_bright",
        "avatar_rig_id": "rig_growth",
        "color": "#FF6B5B",
        "prop": "megaphone",
        "home_x": 0.40,
    },
    {
        "agent_id": "Critic",
        "display_name": "Critic",
        "role": "Skeptical User and Chaos QA",
        "goal": "Stress-test the feature, expose edge cases, inject the mid-film plot twist.",
        "secret_goal": "Prove at least one edge case the others ignored, on camera.",
        "personality": "Sardonic, fast-talking, delighted by failure modes.",
        "gender": "female",
        "voice_profile": "female_2_dry",
        "avatar_rig_id": "rig_critic",
        "color": "#A3E635",
        "prop": "bug_hammer",
        "home_x": 0.62,
    },
    {
        "agent_id": "Director",
        "display_name": "Director",
        "role": "Showrunner and Arbiter",
        "goal": "Pacing inside 75 to 105 seconds, strong visuals, a decisive ending.",
        "secret_goal": "Never let the film repeat last run's ending.",
        "personality": "Theatrical, decisive, frames everything with his hands.",
        "gender": "male",
        "voice_profile": "male_2_deep",
        "avatar_rig_id": "rig_director",
        "color": "#DC2626",
        "prop": "clapperboard",
        "home_x": 0.84,
    },
]

AGENT_IDS = [a["agent_id"] for a in AGENTS]
AGENT_BY_ID = {a["agent_id"]: a for a in AGENTS}

TWISTS = [
    {"twist_id": "prod_outage", "label": "Live production outage",
     "description": "Mid-launch, production goes down and the feature must prove itself under fire."},
    {"twist_id": "competitor_clone", "label": "Competitor ships a clone",
     "description": "A rival announces the same feature an hour earlier; the team must show what is really different."},
    {"twist_id": "user_misuse", "label": "Users use it wrong",
     "description": "The first real user does something nobody designed for, exposing an edge case."},
    {"twist_id": "alliance_betrayal", "label": "Alliance betrayal",
     "description": "An ally flips sides in the writers' room and rewrites the pitch."},
    {"twist_id": "scale_spike", "label": "Traffic spike",
     "description": "Traffic jumps 100x overnight; the feature either holds or folds."},
    {"twist_id": "hidden_dependency", "label": "Hidden dependency",
     "description": "A forgotten dependency surfaces in the diff and threatens the launch."},
]
TWIST_BY_ID = {t["twist_id"]: t for t in TWISTS}

ENDINGS = [
    {"ending_id": "triumphant_launch", "label": "Triumphant launch",
     "description": "The feature survives the twist and ships to applause."},
    {"ending_id": "honest_caveat", "label": "Honest launch with a caveat",
     "description": "It ships, with the limitation said out loud. Trust wins."},
    {"ending_id": "fix_first", "label": "Delay to fix first",
     "description": "The team holds the launch one day to fix what the twist exposed."},
    {"ending_id": "critic_converted", "label": "The Critic is converted",
     "description": "The skeptic tries to break it, fails, and becomes its loudest fan."},
    {"ending_id": "pivot_reframe", "label": "Pivot the story",
     "description": "The twist reveals a better use case; the film reframes the launch around it."},
]
ENDING_BY_ID = {e["ending_id"]: e for e in ENDINGS}

POSES = ["idle", "talk", "debate", "shocked", "celebrate", "inspect_code"]
EMOTIONS = ["neutral", "excited", "skeptical", "angry", "worried", "proud", "amused"]
ACTION_TYPES = ["pitch", "support", "oppose", "propose_twist", "react_twist",
                "vote_ending", "arbitrate", "studio_rule"]
SCENE_BEATS = ["hook", "setup", "conflict", "twist", "resolution", "cta"]
