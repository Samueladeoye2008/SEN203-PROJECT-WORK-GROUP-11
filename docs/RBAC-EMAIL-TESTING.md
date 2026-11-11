# SEN203 RBAC and Email Testing Guide

## Roles

### Super Admin
System-wide role. Can manage users, groups, system limits and email settings. It does not automatically become a board member, so board access remains read-only unless the admin also joins that board.

### Team Leader
Board-level management role. Can create/edit/delete tasks, assign tasks to members, manage board members and promote/demote members. Every board must keep at least one Team Leader.

### Member
Normal project member. Can join boards, view work, create tasks, work on tasks assigned to them or created by them, move their own work through the board and view activity. Members cannot assign work to other people or manage membership.

## Test accounts

Create three normal accounts through **Create account**:

1. Student One — matric `TEST001` — `student1@example.com`
2. Student Two — matric `TEST002` — `student2@example.com`
3. Student Three — matric `TEST003` — `student3@example.com`

Passwords should be at least 8 characters.

Then:

1. Student One creates a new board. The creator automatically becomes its Team Leader.
2. Copy the board join code.
3. Student Two and Student Three log in and join with the code. They become Members.
4. On the board's **Board members** section, Student One can promote Student Two to Team Leader, demote them back, or remove a member.
5. Confirm a Member cannot see or use Team Leader membership controls.
6. Confirm a Member cannot delete a task.
7. Confirm a Team Leader can assign a task to another board member.
8. Confirm a Member can create a task and assign it only to themselves.
9. Confirm a board always retains at least one Team Leader.

## Login

Users can sign in with either their **matric number or email address** plus their password.

## Email setup on Vercel

Set these environment variables in Vercel Project Settings → Environment Variables:

- `APPS_SCRIPT_URL` = the deployed Google Apps Script Web App URL ending in `/exec`
- `APPS_SCRIPT_SECRET` = exactly the same value as the Apps Script project's `SHARED_SECRET`
- `SECRET_KEY` = a strong random secret
- `DATABASE_URL` = the production PostgreSQL connection string

After changing environment variables, redeploy the Vercel project.

## Email test

Sign in as Super Admin → **Super Admin → Settings**.

The Email relay panel shows whether the two Apps Script variables are configured. Click **Send test email**. The test is sent to the Super Admin's email address.

The application uses the relay for:

- welcome emails after registration
- password reset links
- task assignment notifications
- review notifications
- deadline reminder emails

Email failure must not break account creation or task creation. The database transaction completes first, then email is attempted as a best-effort notification.

## If email fails

Check:

1. Apps Script deployment is a **Web app**.
2. It is configured to **Execute as Me**.
3. Access is **Anyone**.
4. The URL ends in `/exec`.
5. `SHARED_SECRET` exactly matches `APPS_SCRIPT_SECRET`.
6. Apps Script has permission to send mail.
7. Vercel has the variables in the correct Production environment.
8. Redeploy after changing Vercel variables.
9. Check the Super Admin Settings test-email message and Vercel Runtime Logs if necessary.


## Hosted Super Admin setup (Vercel)

1. In Vercel open **Project → Settings → Environment Variables**.
2. Add `SECRET_KEY` for **Production** with a long random value.
3. Add `SUPERADMIN_SETUP_KEY` for **Production** with a different long random value. Keep it private.
4. If email is required, add `APPS_SCRIPT_URL` and `APPS_SCRIPT_SECRET` for Production.
5. Redeploy. Vercel requires a redeploy for environment-variable changes to take effect.
6. Open `https://YOUR-DOMAIN/admin/setup`.
7. Enter the `SUPERADMIN_SETUP_KEY`, then the administrator name, Admin ID, email and a password of at least 10 characters.
8. After creation, `/admin/setup` automatically redirects to login because the first Super Admin already exists.
9. Sign in at `/login` using the Admin ID or email and password.
10. Open `/admin`.

The setup key is never stored in the database and the setup route cannot create a second Super Admin once one exists.

### Production test order

Super Admin setup → Super Admin login/session → create Team Leader board → register Member accounts → join board → test leader/member permissions → task CRUD and Kanban moves → email test from `/admin/settings` → password reset → logout/login → refresh and revisit pages → verify PostgreSQL persistence → mobile/responsive test.
