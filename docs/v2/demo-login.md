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

- Learners land on Home and open `/profile` from the top-right account menu. `/passport` redirects
  to `/profile`; it is no longer a primary navigation item.
- The profile dashboard uses completed lesson records and finished attempts of that account.
  The four core stages count a completed lesson and a finished scenario each; repeated attempts
  never advance other stages. Completion is separate from Critical Safety, shown per attempt.
- Institution accounts land on `/institution`, with only institution navigation and workspace routes.
  Learners cannot open institution pages. Anonymous visits to protected pages go through login.
- Logout and account switches clear this tab's learning credentials. The same account can reload
  and resume its rooms. Account changes remount page content to discard the prior account's UI state.

Browser role guards and public demonstration credentials are a prototype UX boundary, not production
authorization. No real credentials, password database, authentication service, SSO or billing is added.
Class/assignment removal is separately defined in `contracts.md`: archive settings, retain evidence.
