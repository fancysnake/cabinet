# Probing questions

Deeper questions for each lens in Step 3. Ask the ones that fit the feature and skip the rest.

## 1. Boundaries

- What happens at zero items, at one, and at exactly the limit?
- What happens at the limit + 1? Is it rejected, truncated, or silently accepted?
- Is the limit per user, per account, per day, or global? Who can change it?
- What happens at the largest size a real user will send: file, text, list, amount?
- What happens across a page boundary when items are added or removed between pages?
- How are time zones, DST, month ends, leap days, and midnight handled?
- How are money and quantities rounded, and how many decimals are allowed? Are negative values possible?

## 2. Bad input

- What happens when a required field is empty, whitespace only, or missing?
- What happens when the same value is submitted twice? Is it a duplicate or a legitimate repeat?
- How are case, leading or trailing spaces, and unicode lookalikes compared?
- What happens with emoji, right-to-left text, very long words, or HTML and script in text fields?
- What happens when a file has the wrong type behind the right extension?
- How does a reference to a deleted or nonexistent record behave?
- How does input from an import, an API, or a pasted spreadsheet differ from the form?

## 3. Unhappy paths

- What does the user see when a dependency is down or slow?
- If the action runs halfway, what is left behind? Can it be resumed or rolled back?
- Is a retry safe, or does it charge, send, or create twice?
- Who finds out when a background job fails, and how?
- What happens to a notification, email, or webhook that never arrives?
- Can the user recover alone, or does support have to step in?

## 4. State and timing

- What happens when two users edit the same thing at once? Who wins?
- What happens on a double click, a back button, or a refreshed form?
- What happens when the user acts on a page that was loaded an hour ago?
- What happens when an action lands while the object is changing state (being published, cancelled, paid)?
- When does an offer, link, token, session, or hold expire, and what happens right after?
- Does order matter? What happens if step 2 arrives before step 1?
- What does a scheduled job do with records created or changed while it runs?

## 5. Permissions and ownership

- Who can see, create, edit, and delete this? Is that checked on the server?
- Can a user reach another user's record by changing an ID?
- What happens to access when a role is removed, an account is downgraded, or someone leaves the team?
- Who owns data that several users created together?
- Can an admin act as a user? Is that logged and visible?
- What does a shared link, invite, or delegated access grant, and for how long?

## 6. Abuse and misuse

- Can the rule be gamed: new accounts for repeat discounts, splitting one order to stay under a limit?
- Can responses reveal whether an email, username, or record exists?
- What does it cost when someone calls this a million times? Is there a rate limit?
- Can one user spam, harass, or impersonate another through this feature?
- Can the feature be used to reach something the user shouldn't, like a cheaper tier, someone else's data, or an admin action?
- Can a refund, cancellation, or undo be used to keep the benefit and lose the cost?
- What would a competitor, a scraper, or a disgruntled insider do with it?

## 7. Conflicting rules

- Does this story contradict another story in this feature?
- Does it clash with an existing policy: pricing, privacy, retention, terms of service?
- Does it clash with a legal duty: GDPR erasure, tax records, accessibility?
- When two rules both apply, which one wins, and who decided?
- Does the rule contradict itself at its own edges (for example, "always" against "only when")?

## 8. Ambiguous terms

- Which words in the story could two people read differently? List them.
- For each one: is it measured, from what moment, and by whose clock?
- Is "user" one person, one account, one device, or one organization?
- Does "delete" mean hide, archive, or erase?
- Does "notify" mean email, push, in-app, or all three?
- Is the threshold a product decision, a config value, or a guess?

## 9. Lifecycle

- Can the action be undone? For how long, and by whom?
- What happens to history, audit logs, and reports after an edit?
- What happens to dependent data, like comments, orders, files, and links, when the parent is deleted?
- How long is data kept, and what removes it?
- What happens to this data when the account is closed, merged, or transferred?
- What happens to records created under old rules when the rules change?
