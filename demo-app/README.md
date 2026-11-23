# Smart Scroll demo
Run `npm run dev` here and visit http://localhost:3000; the decision viewer is at /decision-log. The page has no runtime network dependencies.

For a clean feature-merge demo, create a separate demo repository at `.demo-repo`: main contains the article without the progress bar and navigation, and `feat/smart-scroll` adds those two related elements. Merge that feature into main, then install the trigger using `py scripts/install_post_merge.py` from the project root. A merge invokes `run_autonomous_launch.py`. This build does not create commits or branches because its worker contract forbids git commits. Until that repository exists, use `--repo PATH` with a repository containing a commit. The hook installer refuses to overwrite an existing hook.

The viewer reads output runs locally. It displays `latest` and any run directories with decision logs. Live social publishing is deliberately not implemented.
