#!/bin/bash
# Setup git configuration for the project

echo "Setting up Git configuration..."

# Get organization email from user
read -p "Enter your organization email: " ORG_EMAIL
read -p "Enter your name (for git commits): " USER_NAME

# Configure git
git config user.email "$ORG_EMAIL"
git config user.name "$USER_NAME"

echo "Git configured with:"
echo "  Email: $(git config user.email)"
echo "  Name: $(git config user.name)"

