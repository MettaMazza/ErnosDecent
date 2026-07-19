# 🐙 GitDec — Simple User Guide

Welcome to **GitDec**, the repository, issue, and pull-request subsystem built into **ErnosDecent**.

GitDec stores repositories on the node operator's machine and signs network events with
the node identity. Public repositories and events can be copied by peers; local control
does not make public material impossible to delete, censor elsewhere, or scrape.

---

## 🚀 How to Get Started

### 1. Opening GitDec
1. Build and start the node with `bash build.sh` and `./run_node.sh`.
2. Open the dashboard: [http://localhost:8088](http://localhost:8088)
3. Click the **GitDec P2P** tab in the left-hand navigation menu.

### 2. Creating a New Repository
1. Click the **+ New** button.
2. Enter a unique **Repository ID** (e.g., `my-awesome-project`) and click **Create**.
3. GitDec will initialize the repository and assign ownership to your digital identity (DID).

### 3. Cloning an Existing Repository
If a friend shares their Repository ID with you, you can download it to your node:
1. Click the **Clone** button next to your repository list.
2. Enter the **Repository ID** your friend gave you and click **Clone**.
3. GitDec requests repository history from connected peers. With no connected mesh peer, network synchronization is deferred and the repository remains local.

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

Inside this folder, a repository can contain:
- **gitdec.json**: Repository metadata (name, owner, visibility, collaborators, and branch heads).
- **objects/**: The database containing actual commit data.
- **issues.json**: The issues and comments tracker.
- **pull_requests.json**: The pull requests and reviews tracker.

GitDec changes are created through its dashboard/API operations. Editing files directly
does not by itself broadcast, authenticate, or synchronize a GitDec event.
