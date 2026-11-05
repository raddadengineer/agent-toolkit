---
id: avoid-unpinned-wildcard-dependencies
title: "Avoid Unpinned Wildcard Dependencies"
category: anti-patterns
scope: project
tags: [build, dependencies, security]
created_at: 2026-11-05T02:09:10.612060+00:00
updated_at: 2026-11-05T02:09:10.612060+00:00
---

# Avoid Unpinned Wildcard Dependencies

Do not use wildcard version specifiers (* or latest) in package manifests. Wildcard versions lead to non-deterministic builds and security vulnerabilities.
