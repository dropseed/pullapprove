<a href="https://www.pullapprove.com/"><img src="https://www.pullapprove.com/assets/img/logos/pull-approve-logo-gray-dk.png" alt="PullApprove" height="40px" /></a>
---

PullApprove is a framework for code review assignment and policies.
It integrates directly with GitHub, GitLab (beta), and Bitbucket (beta).

It is configured with a `.pullapprove.yml` file at the root of your repo.
Reviews are split into "review groups" which can be enabled/disabled depending on the specifics of a PR.
When a group is activated on a PR, review requests are sent out automatically to the selected reviewers.

Here's a basic example:

```yaml
version: 3

overrides:
- if: "base.ref != 'master'"
  status: success
  explanation: "Review not required unless merging to master"
- if: "'hotfix' in labels"
  status: success
  explanation: "Review skipped for hotfix"

groups:
  code:
    reviewers:
      users:
      - reviewerA
      - reviewerB
    reviews:
      required: 2
      request: 1
      request_order: random
    labels:
      approved: "Code review approved"

  database:
    conditions:
    - "'*migrations*' in files"
    reviewers:
      teams:
      - database
```

A "pullapprove" status is reported on the PR with a link to more details.
You can make this a [required status check](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/defining-the-mergeability-of-pull-requests/managing-a-branch-protection-rule#creating-a-branch-protection-rule) to enforce your review workflows on all pull requests.

![pullapprove review status check](https://user-images.githubusercontent.com/649496/141190794-c62da3f0-92fb-4125-ae7e-410b1ec8dc89.png)

---

This repo contains some of the core models and configuration settings which are used by the [hosted service](https://www.pullapprove.com/).

To host your own version of PullApprove, please contact us at https://www.pullapprove.com/enterprise/.
