# 🐙 GitDec — Simple User Guide

Welcome to **GitDec**, a secure, peer-to-peer repository hosting system built directly into **ErnosDecent**. 

Unlike GitHub, which is owned by a single corporation, GitDec runs directly on your machine and communicates over a decentralized peer-to-peer network (Nostr). Your code remains yours, under your keys, and cannot be censored, deleted, or scraped by third parties.

---

## 🚀 How to Get Started

### 1. Opening GitDec
1. Start your ErnosDecent node daemon: `./node`
2. Open the dashboard in your browser: [http://localhost:8080](http://localhost:8080)
3. Click the **GitDec P2P** tab in the left-hand navigation menu.

### 2. Creating a New Repository
1. Click the **+ New** button.
2. Enter a unique **Repository ID** (e.g., `my-awesome-project`) and click **Create**.
3. GitDec will initialize the repository and assign ownership to your digital identity (DID).

### 3. Cloning an Existing Repository
If a friend shares their Repository ID with you, you can download it to your node:
1. Click the **Clone** button next to your repository list.
2. Enter the **Repository ID** your friend gave you and click **Clone**.
3. GitDec will query the decentralized network to locate the repository files and sync them to your machine automatically.

---

## 🤝 Collaborating & Permissions

Every GitDec repository relies on **Decentralized Identifiers (DIDs)** to authorize actions. 

### Adding Collaborators
Only the repository owner can add contributors:
1. Select your repository and go to the **Settings** tab.
2. Under **Add Collaborator**, enter the collaborator's DID (e.g., `did:key:z6M...`).
3. Select their role:
   - **owner**: Full administrative control (can add/remove collaborators and delete the repository).
   - **writer**: Can push commits, comment on issues, and submit/review PRs.
   - **reader**: Read-only access to view commits, issues, and PRs.
4. Click **Add Collaborator**.

### Removing Collaborators
1. Go to the **Settings** tab.
2. Locate the collaborator in the list and click **Remove**.

---

## 🛠️ Issues, Pull Requests, & Branch Heads

GitDec makes it simple to coordinate development asynchronously:

- **Commits Tab**: Displays the latest commit hashes for each branch (e.g., `main`).
- **Files Tab**: Browse the files and source code stored in the repository. Select any file in the file explorer to view its contents directly in the web dashboard.
- **Issues Tab**: Click **+ New Issue** to create bug reports or feature requests. Collaborators can reply or comment on any issue.
- **Pull Requests Tab**: Click **+ New PR** to submit code changes. Owners and writers can approve or comment on PRs directly.

---

## 📁 Behind the Scenes: Where are my files?

Every repository you create or clone is stored on your local disk under:
`config/gitdec/repos/<repository-id>/`

Inside this folder, you will find:
- [gitdec.json](file:///Users/mettamazza/Desktop/ErnosDecent./config/gitdec/repos/ErnosDecent/gitdec.json): The repository metadata manifest (name, owner, authorized collaborators, and branch heads).
- **objects/**: The database containing actual commit data.
- **issues.json**: The issues and comments tracker.
- **pull_requests.json**: The pull requests and reviews tracker.

To update files, simply edit them in this directory. GitDec automatically tracks updates and syncs modifications when you interact with the UI.
