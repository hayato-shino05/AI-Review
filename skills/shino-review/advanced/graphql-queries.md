# GitHub GraphQL Review Thread Management (`graphql-queries.md`)

This guide provides tested GraphQL queries and batch mutations for managing GitHub Pull Request review threads, incorporating official patterns from `greptileai/skills`.

---

## 1. Why GitHub GraphQL for AI Review?

Traditional REST endpoints (`/repos/{owner}/{repo}/pulls/{pull_number}/comments`) suffer from three key deficiencies:
1. **N+1 Round-Trip Latency**: Resolving 10 review threads requires 10 distinct HTTP calls.
2. **Missing Thread State**: REST API does not cleanly expose `isResolved` status or thread groupings without fetching multi-page comment timelines.
3. **Atomic Batch Mutations**: GraphQL Aliases allow resolving all addressed or refuted threads in a **single round-trip HTTP request**, avoiding GitHub secondary rate limits.

---

## 2. Query: Fetch All PR Review Threads

Retrieves all review threads, their resolved status, line coordinates, file paths, and discussion comments.

```graphql
query GetPRReviewThreads($owner: String!, $repo: String!, $pullNumber: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $pullNumber) {
      id
      title
      reviewThreads(first: 100) {
        totalCount
        nodes {
          id
          isResolved
          isOutdated
          path
          line
          originalLine
          comments(first: 20) {
            totalCount
            nodes {
              id
              body
              author {
                login
              }
              createdAt
            }
          }
        }
      }
    }
  }
}
```

### CLI Execution via `gh api graphql`:

```bash
gh api graphql -f query='
query($owner: String!, $repo: String!, $pullNumber: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $pullNumber) {
      reviewThreads(first: 100) {
        nodes {
          id
          isResolved
          path
          line
          comments(first: 5) {
            nodes {
              id
              author { login }
              body
            }
          }
        }
      }
    }
  }
}' -F owner="<OWNER>" -F repo="<REPO>" -F pullNumber=<PR_NUMBER>
```

Filter for unresolved threads using `jq`:
```bash
gh api graphql ... | jq '.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false)'
```

---

## 3. Mutation: Resolve a Single Review Thread

Marks a specific thread as resolved:

```graphql
mutation ResolveThread($threadId: ID!) {
  resolveReviewThread(input: { threadId: $threadId }) {
    thread {
      id
      isResolved
    }
  }
}
```

### CLI Execution:
```bash
gh api graphql -f query='
mutation($threadId: ID!) {
  resolveReviewThread(input: { threadId: $threadId }) {
    thread {
      id
      isResolved
    }
  }
}' -F threadId="PRRT_kwDOxxx..."
```

---

## 4. Mutation: Reply to a Review Thread

Adds a technical reply before resolving (essential for Actionable fix references and False Positive refutations):

```graphql
mutation ReplyToReviewThread($threadId: ID!, $body: String!) {
  addPullRequestReviewThreadReply(input: {
    pullRequestReviewThreadId: $threadId,
    body: $body
  }) {
    comment {
      id
      body
      createdAt
    }
  }
}
```

### CLI Execution:
```bash
gh api graphql -f query='
mutation($threadId: ID!, $body: String!) {
  addPullRequestReviewThreadReply(input: {
    pullRequestReviewThreadId: $threadId,
    body: $body
  }) {
    comment { id }
  }
}' -F threadId="PRRT_kwDOxxx..." -F body="Verified: Fixed at shared choke point in commit 8a3f2b1."
```

---

## 5. Batch Mutation: Batch Resolve Threads via GraphQL Aliases

To resolve multiple threads in a single HTTP request without multiple round-trips:

```graphql
mutation BatchResolveThreads(
  $t1: ID!,
  $t2: ID!,
  $t3: ID!
) {
  res1: resolveReviewThread(input: { threadId: $t1 }) {
    thread { id isResolved }
  }
  res2: resolveReviewThread(input: { threadId: $t2 }) {
    thread { id isResolved }
  }
  res3: resolveReviewThread(input: { threadId: $t3 }) {
    thread { id isResolved }
  }
}
```

### Dynamic Batch Resolution Script (Node.js / Bash)

Use this script to dynamically batch resolve any list of thread IDs:

```javascript
// resolve-threads.js
const { execSync } = require('child_process');

function batchResolveThreads(threadIds) {
  if (!threadIds || threadIds.length === 0) {
    console.log('No threads to resolve.');
    return;
  }

  // Construct dynamic aliased mutations
  const varDefs = threadIds.map((_, i) => `$id${i}: ID!`).join(', ');
  const mutations = threadIds.map((_, i) => `
    res${i}: resolveReviewThread(input: { threadId: $id${i} }) {
      thread { id isResolved }
    }
  `).join('\n');

  const query = `mutation BatchResolve(${varDefs}) {\n${mutations}\n}`;

  const varArgs = threadIds.map((id, i) => `-F id${i}="${id}"`).join(' ');
  const cmd = `gh api graphql -f query='${query}' ${varArgs}`;

  try {
    const res = execSync(cmd, { encoding: 'utf8' });
    console.log('Batch resolve successful:', res);
  } catch (err) {
    console.error('Batch resolve failed:', err.message);
  }
}

// Example usage:
// batchResolveThreads(['PRRT_kwDO...', 'PRRT_kwDO...']);
```

---

## 6. Atomic Reply and Resolve Pattern

For False Positives and Actionable fixes, provide evidence and resolve atomically:

```graphql
mutation ReplyAndResolve($threadId: ID!, $replyBody: String!) {
  reply: addPullRequestReviewThreadReply(input: {
    pullRequestReviewThreadId: $threadId,
    body: $replyBody
  }) {
    comment { id }
  }
  resolve: resolveReviewThread(input: {
    threadId: $threadId
  }) {
    thread { id isResolved }
  }
}
```
