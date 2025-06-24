# 🎮 Persona Nexus - Persona Series Community Forum

**Persona Nexus** is a full-stack web forum application built from scratch, inspired by the pop-retro aesthetic of the *Persona 4* game. The platform serves as a space for fans to discuss, share content, and interact within a dynamic and modern community.

---

## ✨ Core Features (Current)

### 🌐 Complete Authentication System
- Secure user registration, login, and logout using `django-allauth`.
- Account settings page for users to update their **avatar** and **bio**.

### ✍️ Post Management (CRUD)
- Full CRUD operations for posts (Create, Read, Update, Delete).
- SEO-friendly post URLs using **slugs** instead of numeric IDs.

### ⚡ Interactive Feed
- Main feed with **"Recommended"** and **"Following"** tabs.
- Sort and filter options: **New**, **Hot**, **Top**.
- Dynamic content loading with **HTMX**, no page reloads.

### 👥 Social & Interaction Features
- **Voting System**: Upvote/downvote posts.
- **Nested Comments**: Structured discussions with threaded replies.
- **Follow System**: Users can follow others (via `django-friendship`).
- **Save Posts**: Bookmark favorite posts, accessible on profile.

### 👤 Dynamic Profile Pages
- Single smart profile template:
  - **Edit** button for owners.
  - **Follow/Unfollow** for visitors.
- Tabs for:
  - Posts created by the user.
  - Saved/bookmarked posts.

---

## 🛠️ Tech Stack

| Category         | Technology                             |
|------------------|-----------------------------------------|
| Backend          | Python, Django, 	
Python, Django, SQLite (development), PostgreSQL (production)|
| Frontend         | HTML, Tailwind CSS, Alpine.js, HTMX    |
| Authentication   | django-allauth                         |
| Social Features  | django-friendship                      |
| Environment      | Poetry                                 |

---
## 📝 Future Plans
- Refine the UI/UX across pages for a smoother user experience.
- Implement pagination on post feeds for improved performance.