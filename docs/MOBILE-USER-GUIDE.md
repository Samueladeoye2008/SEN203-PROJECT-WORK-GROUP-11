# StudentBoard — Mobile & User Guide

## 1. What users do first

### Student / Member
1. Open the deployed StudentBoard link on a phone, tablet or computer.
2. Select **Create account / Register**.
3. Enter your name, matric number, email and password.
4. Submit the form. You should be taken into the application after successful registration.
5. From the dashboard, open a board using its card.
6. If you were given a board join code, use the **Join board** option and enter the code.
7. Open the board and work on tasks assigned to you.
8. Update your task status as you work (for example: To Do → In Progress → Done).
9. Open **Account** to review your profile and account information.
10. Use **Logout** when finished.

### Team Leader
1. Register or log in.
2. Create a new board/project, or open a board where you are already a Team Leader.
3. Share the board join code with project members.
4. Open the board's **Members** area.
5. Promote/demote members when necessary. The system prevents removing the final Team Leader from a board.
6. Create tasks, set status/priority/due date, and assign tasks to board members.
7. Review progress and activity.
8. Use the board dashboard to monitor work.

### Super Admin
1. Log in with the Super Admin account.
2. Open the **Admin / Super Admin** area.
3. Review system statistics, users, groups and usage limits.
4. Search users by name, matric number or email.
5. Suspend/reactivate users when necessary.
6. Promote or remove Super Admin privileges only when authorized.
7. Review email settings and use the test-email action to verify the configured relay.
8. Use system settings to control registration, limits and email behaviour.

## 2. Mobile navigation

On screens below the desktop breakpoint, the left sidebar is replaced by a compact mobile top bar. Boards use horizontal scrolling so the Kanban columns remain usable without squeezing task cards into unreadable widths.

Forms become one-column layouts, buttons become full-width where appropriate, tables can be horizontally scrolled, and touch targets are enlarged for phone use.

## 3. Recommended testing order after deployment

1. Open the production URL on desktop.
2. Register a normal Member account.
3. Log out and log back in using the registered matric number/email.
4. Create a board and confirm the creator is Team Leader.
5. Register a second account and join the board.
6. As Team Leader, create and assign a task.
7. As Member, update the task status.
8. Test Member restrictions by attempting a Team Leader-only action.
9. Log in as Super Admin and test user management.
10. Test the email action and confirm the message arrives.
11. Repeat the main flow on an Android/iPhone-sized screen.
12. Refresh pages while logged in to confirm the session remains active.

## 4. Important production note

The deployed version must use a persistent PostgreSQL database. Do not rely on local files or `/tmp` for application data in production. Vercel documents that function filesystems are not durable storage; production writes should use a database or other persistent storage.
