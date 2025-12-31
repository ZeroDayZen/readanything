# Manual Update Guide for ReadAnything

This guide provides step-by-step instructions for manually updating ReadAnything to the latest version from GitHub.

## Prerequisites

- ReadAnything installed via `git clone` (not a ZIP download)
- Git installed on your system
- Terminal/Command Line access
- Internet connection

## Step-by-Step Update Instructions

### Step 1: Navigate to the ReadAnything Directory

Open a terminal and navigate to the ReadAnything installation directory:

```bash
cd /path/to/readanything
```

**Note:** Replace `/path/to/readanything` with the actual path where you cloned the repository.

**Example:**
- If you cloned to your home directory: `cd ~/readanything`
- If you cloned to Desktop: `cd ~/Desktop/readanything`
- If you cloned to a custom location: `cd /your/custom/path/readanything`

---

### Step 2: Check Current Status

Check what branch you're on and if there are any uncommitted changes:

```bash
git status
```

**What to look for:**
- Current branch (should be `main` or `master`)
- Any modified files (shown in red)
- Any untracked files

**If you have uncommitted changes:**
- **Option A (Recommended):** Commit your changes first:
  ```bash
  git add .
  git commit -m "Your commit message"
  ```

- **Option B:** Stash your changes temporarily:
  ```bash
  git stash
  ```
  (You can restore them later with `git stash pop`)

- **Option C:** Discard changes (be careful - this is permanent):
  ```bash
  git checkout -- .
  ```

---

### Step 3: Fetch Latest Changes from GitHub

Fetch the latest changes from the remote repository:

```bash
git fetch origin
```

**What this does:**
- Downloads information about new commits from GitHub
- Does NOT modify your local files yet
- Safe to run multiple times

**Expected output:**
- If there are updates: Shows information about new commits
- If you're up to date: No output or "Already up to date"

---

### Step 4: Check What Updates Are Available

Compare your current version with the remote version:

```bash
git log HEAD..origin/main --oneline
```

**What this shows:**
- List of new commits that are available
- If the list is empty, you're already up to date

**Alternative command to see summary:**
```bash
git status
```

This will show: "Your branch is behind 'origin/main' by X commits" if updates are available.

---

### Step 5: Pull the Latest Version

Pull and merge the latest changes into your local repository:

```bash
git pull origin main
```

**What this does:**
- Downloads the latest files from GitHub
- Merges them with your local files
- Updates your repository to the latest version

**If you're on a different branch (e.g., `master`):**
```bash
git pull origin master
```

**Expected output:**
- If successful: Shows files changed and commits merged
- If conflicts occur: You'll see conflict markers (see Troubleshooting below)

---

### Step 6: Verify the Update

Check that the update was successful:

```bash
git status
```

**Expected output:**
- "Your branch is up to date with 'origin/main'"
- No modified files (unless you had local changes)

You can also check the latest commit:
```bash
git log -1 --oneline
```

This shows the most recent commit hash and message.

---

### Step 7: Update Python Dependencies (Recommended)

If the update includes changes to `requirements.txt`, update your Python packages:

**If using a virtual environment (recommended):**

1. Activate the virtual environment:
   ```bash
   source venv/bin/activate
   ```

2. Upgrade pip (optional but recommended):
   ```bash
   pip install --upgrade pip
   ```

3. Install/update dependencies:
   ```bash
   pip install -r requirements.txt --upgrade
   ```

4. Deactivate the virtual environment when done:
   ```bash
   deactivate
   ```

**If NOT using a virtual environment:**

1. Update dependencies (installs system-wide):
   ```bash
   pip3 install -r requirements.txt --upgrade
   ```

   **Note:** On some systems, you may need `pip` instead of `pip3`, or `python -m pip`.

---

### Step 8: Test the Updated Application

Run the application to verify everything works:

```bash
# If using venv, activate it first
source venv/bin/activate

# Run the application
python3 main.py
```

**Check for:**
- Application launches successfully
- All features work as expected
- No error messages in the console

---

## Quick Reference: One-Line Update

If you're confident and want to update quickly:

```bash
cd /path/to/readanything && git pull origin main && source venv/bin/activate && pip install -r requirements.txt --upgrade && deactivate
```

**Warning:** This doesn't check for uncommitted changes or verify updates. Use with caution.

---

## Troubleshooting

### Problem: "fatal: not a git repository"

**Solution:** You're not in a git repository. Make sure you cloned the repository using `git clone`, not downloaded a ZIP file.

To fix: Clone the repository properly:
```bash
cd /path/to/parent/directory
git clone https://github.com/ZeroDayZen/readanything.git
cd readanything
```

---

### Problem: "Your branch has diverged" or merge conflicts

**Solution:** Your local changes conflict with remote changes.

**Option 1: Keep your local changes (rebase):**
```bash
git pull --rebase origin main
```

**Option 2: Discard local changes and use remote version:**
```bash
git fetch origin
git reset --hard origin/main
```

**Warning:** This will permanently delete your local changes!

**Option 3: Stash changes, pull, then reapply:**
```bash
git stash
git pull origin main
git stash pop
```

---

### Problem: "Permission denied" when pulling

**Solution:** Check file permissions or use sudo (not recommended for git operations).

Better solution: Fix ownership:
```bash
sudo chown -R $USER:$USER .
git pull origin main
```

---

### Problem: "fatal: refusing to merge unrelated histories"

**Solution:** Force merge (use with caution):
```bash
git pull origin main --allow-unrelated-histories
```

---

### Problem: Dependencies fail to update

**Solutions:**

1. **Upgrade pip first:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt --upgrade
   ```

2. **Install dependencies individually:**
   ```bash
   pip install --upgrade PyQt6 pyttsx3 pynput Pillow
   ```

3. **Check for error messages** in the output and install missing system dependencies.

---

### Problem: Application doesn't work after update

**Solutions:**

1. **Reinstall dependencies:**
   ```bash
   source venv/bin/activate
   pip install -r requirements.txt --upgrade --force-reinstall
   ```

2. **Check the CHANGELOG.md** for breaking changes:
   ```bash
   cat CHANGELOG.md
   ```

3. **Check for error messages** when running the application

4. **Revert to previous version** (if needed):
   ```bash
   git log --oneline  # Find the previous commit hash
   git checkout <previous-commit-hash>
   ```

---

## Best Practices

1. **Always commit or stash local changes** before updating
2. **Read the CHANGELOG.md** to see what changed
3. **Update dependencies** after pulling new code
4. **Test the application** after updating
5. **Keep backups** of important customizations
6. **Use virtual environments** to avoid dependency conflicts

---

## Alternative: Use the GUI Updater

If you prefer a graphical interface, use the built-in updater:

```bash
python3 update.py
```

This provides the same functionality with a user-friendly GUI.

---

## Need Help?

- Check the main README.md for general information
- Check INSTALL_KALI.md for installation-specific issues
- Review CHANGELOG.md to see what changed in each version
- Open an issue on GitHub: https://github.com/ZeroDayZen/readanything/issues

---

**Last Updated:** This guide is for ReadAnything version 1.0-beta and later.

