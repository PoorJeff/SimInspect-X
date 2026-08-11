# Reproducibility

Every trial stores:
- git commit;
- dependency manifest;
- method ID;
- scenario ID;
- seed;
- world ID;
- mission ID;
- controller;
- planner parameters;
- result;
- failure reason;
- metrics.

Example:

```text
experiments/raw/
  E4_viewpoint_policy/
    commit_abcdef/
      manifest.json
      B0/F09/seed_0001.json
      P1/F09/seed_0001.json
      P2/F09/seed_0001.json
```

Every paper/report figure must be regenerated from these files.
