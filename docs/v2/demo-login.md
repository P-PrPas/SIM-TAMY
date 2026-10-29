# Demo login and account navigation — 2026-10-29

The owner replaced profile pickers with the fixed demo-login option allowed by the prototype
boundary. `/login` lists existing fictional learner, educator and organization-admin accounts.
The username is the account ID; the public demonstration password is `SimTamy2026!`.
Choosing an account only fills the form. The learner must submit it to start a browser login.
Passwords are never persisted. This is a demonstration flow, not server authentication.

The browser stores the account's ID, display name, organization and role, and sends the existing
`X-Demo-Account` header. Existing organization checks remain unchanged. Reviewers are not offered
because the institution workspace's existing APIs support educators and organization admins.
Old profile-picker IDs alone do not establish a login.

Account navigation and the learner dashboard are added by subsequent stack layers.
