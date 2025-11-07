# Shared Data Directory

This directory contains data files shared between workers and the backend.

## Files

- **livelive.txt**: Email pool for account creation
  - Format: `email:password` (one per line)
  - Add your hotmail/outlook accounts here

- **kicks.json**: Generated Kick.com accounts
  - Automatically populated by workers
  - Contains account credentials and metadata

## Usage

1. Add emails to livelive.txt:
   ```
   your_email@hotmail.com:your_password
   another@outlook.com:another_password
   ```

2. Run account creation (emails will be consumed)

3. Generated accounts will be saved to kicks.json

## Security

**IMPORTANT**: Never commit livelive.txt or kicks.json to git!
These files contain sensitive credentials.
